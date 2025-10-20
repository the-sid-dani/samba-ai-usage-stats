#!/usr/bin/env python3
"""
Programmatic Metabase dashboard creator.

- Logs in via /api/session (reads creds from .env or env)
- Resolves BigQuery database id by name (or uses MB_DB_ID)
- Reads *.sql from a directory, creates a card per file
- Creates a dashboard and lays out cards in a 3-column grid (24 cols total)
- Writes dashboards.json with created ids + URL

Env vars (.env or process):
  MB_HOST  (e.g., http://127.0.0.1:3000)
  MB_USER  (Metabase admin email)
  MB_PASS  (Metabase admin password)
  MB_DB_ID (optional numeric database id)
  MB_DB_NAME (optional, e.g., "AI Usage Analytics (BigQuery)")
  MB_COLLECTION_ID (optional numeric collection id)

Usage examples:
  python scripts/metabase/create_dashboards.py \
    --sql-dir sql/dashboard/ai_cost \
    --dashboard-name "AI Cost Dashboard - Q4 2025" \
    --date start_date=2025-10-01 --date end_date=2025-12-31 \
    --number quarter_budget_usd=73000 --number daily_budget_usd=793.48 \
    --number alert_threshold_usd=500 --number user_budget_threshold_usd=500 \
    --number inactive_window_days=14 --number total_seats=250 \
    --out dashboards.json
"""
import argparse, json, os, sys, time, pathlib
from typing import List, Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv


def env_or(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        sys.exit(f"Missing required env: {name}")
    return v


def login(host: str, user: str, pwd: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{host.rstrip('/')}/api/session", json={"username": user, "password": pwd})
    r.raise_for_status()
    return s


def resolve_db_id(sess: requests.Session, host: str, name: Optional[str], dbid: Optional[str]) -> int:
    if dbid:
        return int(dbid)
    r = sess.get(f"{host.rstrip('/')}/api/database")
    r.raise_for_status()
    payload = r.json()
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            dbs = payload["data"]
        else:
            dbs = []
            for value in payload.values():
                if isinstance(value, list):
                    dbs.extend(value)
    else:
        dbs = payload
    if not isinstance(dbs, list):
        raise SystemExit("Unexpected Metabase /api/database payload; cannot resolve database id")
    if name:
        for d in dbs:
            if d.get("engine") == "bigquery" and name.lower() in str(d.get("name", "")).lower():
                return int(d["id"])
    for d in dbs:
        if d.get("engine") == "bigquery":
            return int(d["id"])
    raise SystemExit("No BigQuery database found in Metabase")


def resolve_field_id(sess: requests.Session, host: str, db_id: int, table_name: str, col_name: str) -> Optional[int]:
    """Resolve BigQuery field ID from database metadata"""
    r = sess.get(f"{host.rstrip('/')}/api/database/{db_id}/metadata")
    r.raise_for_status()
    metadata = r.json()

    # Find the table
    for table in metadata.get("tables", []):
        if table_name.lower() in table.get("name", "").lower():
            # Find the field
            for field in table.get("fields", []):
                if field.get("name") == col_name:
                    return field["id"]

    print(f"Warning: Could not resolve field ID for {table_name}.{col_name}")
    return None


def read_sql_files(sql_dir: str) -> List[Dict[str, str]]:
    files = sorted(pathlib.Path(sql_dir).glob("*.sql"))
    if not files:
        raise SystemExit(f"No .sql files found in {sql_dir}")
    out = []
    for f in files:
        out.append({"name": f.stem.replace("_", " ").title(), "file": str(f), "sql": f.read_text()})
    return out


def _build_template_tags(sql: str, param_index: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    tags: Dict[str, Dict[str, Any]] = {}
    used: List[str] = []
    for slug, meta in param_index.items():
        if f"{{{{{slug}" in sql:
            used.append(slug)
            tag_config = {
                "id": meta["id"],
                "name": slug,
                "display-name": meta["name"],
                "type": meta.get("type", "text"),
                "widget-type": meta.get("_widget", meta.get("type", "text")),
                "default": meta.get("default"),
                "required": False,  # Make all parameters optional
            }
            # Add dimension field mapping for Field Filter types
            if meta.get("type") == "dimension":
                tag_config["dimension"] = meta.get("dimension", ["field", meta.get("field_id")])
            tags[slug] = tag_config
    return tags, used


def create_card(
    sess: requests.Session,
    host: str,
    db_id: int,
    title: str,
    sql: str,
    param_index: Dict[str, Dict[str, Any]],
) -> Tuple[int, List[str]]:
    template_tags, used_slugs = _build_template_tags(sql, param_index)
    payload = {
        "name": title,
        "dataset_query": {
            "type": "native",
            "native": {"query": sql, "template-tags": {}},
            "database": db_id,
        },
        "display": "table",
        "visualization_settings": {},
        "description": title,
    }
    payload["dataset_query"]["native"]["template-tags"] = template_tags
    r = sess.post(f"{host.rstrip('/')}/api/card", json=payload)
    r.raise_for_status()
    return r.json()["id"], used_slugs


def create_dashboard(
    sess: requests.Session, host: str, name: str, collection_id: Optional[int], parameters: List[Dict[str, Any]]
) -> int:
    payload: Dict[str, Any] = {"name": name, "parameters": parameters}
    if collection_id is not None:
        payload["collection_id"] = collection_id
    r = sess.post(f"{host.rstrip('/')}/api/dashboard", json=payload)
    if r.status_code >= 400:
        raise SystemExit(
            "Metabase create_dashboard failed "
            f"{r.status_code}: {r.text}"
        )
    return r.json()["id"]


def update_dashboard_layout(
    sess: requests.Session,
    host: str,
    dash_id: int,
    name: str,
    parameters: List[Dict[str, Any]],
    dashcards: List[Dict[str, Any]],
    collection_id: Optional[int],
) -> None:
    payload: Dict[str, Any] = {
        "name": name,
        "parameters": parameters,
        "dashcards": dashcards,
    }
    if collection_id is not None:
        payload["collection_id"] = collection_id
    r = sess.put(f"{host.rstrip('/')}/api/dashboard/{dash_id}", json=payload)
    r.raise_for_status()


def parse_number_kv(pairs: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in pairs:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        slug = k.strip()
        try:
            vnum = float(v)
        except ValueError:
            vnum = v
        out.append({
            "id": f"mb_param_{slug}",
            "name": k,
            "slug": slug,
            "type": "number",
            "default": vnum,
            "_widget": "number",
        })
    return out


def parse_date_kv(pairs: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in pairs:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        slug = k.strip()
        out.append({
            "id": f"mb_param_{slug}",
            "name": k,
            "slug": slug,
            "type": "date",
            "default": v.strip(),
            "_widget": "date/single",
        })
    return out


def main():
    load_dotenv(dotenv_path=os.getenv("MB_ENV_FILE", "./.env"), override=False)

    parser = argparse.ArgumentParser(description="Create Metabase dashboard from SQL files.")
    parser.add_argument("--sql-dir", required=True, help="Directory with *.sql files")
    parser.add_argument("--dashboard-name", required=True, help="Dashboard title")
    # Allow overriding collection via env var for convenience
    _env_collection = os.getenv("MB_COLLECTION_ID")
    parser.add_argument(
        "--collection-id",
        type=int,
        default=(int(_env_collection) if _env_collection and _env_collection.isdigit() else None),
    )
    parser.add_argument("--db-id", default=os.getenv("MB_DB_ID"))
    parser.add_argument("--db-name", default=os.getenv("MB_DB_NAME"))
    parser.add_argument("--param", action="append", default=[], help="Add a dashboard parameter by slug (e.g., date_range)")
    parser.add_argument("--date", action="append", default=[], help="Date params as name=value (e.g., start_date=2025-10-01)")
    parser.add_argument("--number", action="append", default=[], help="number params as name=value (repeatable)")
    parser.add_argument("--out", default="dashboards.json")
    args = parser.parse_args()

    host = env_or("MB_HOST", "http://127.0.0.1:3000")
    user = env_or("MB_USER")
    pwd = env_or("MB_PASS")

    sess = login(host, user, pwd)
    db_id = resolve_db_id(sess, host, args.db_name, args.db_id)

    sql_files = read_sql_files(args.sql_dir)

    # Build dashboard parameters
    params: List[Dict[str, Any]] = []

    # Add date parameters (simple date type, not Field Filters)
    params.extend(parse_date_kv(args.date))

    # Add number parameters
    params.extend(parse_number_kv(args.number))

    # Add regular params
    for p in args.param:
        slug = p.strip()
        if "date" in p:
            params.append({
                "id": f"mb_param_{slug}",
                "name": p,
                "slug": slug,
                "type": "date/all-options",
                "default": None,
                "_widget": "date/all-options",
            })
        else:
            params.append({
                "id": f"mb_param_{slug}",
                "name": p,
                "slug": slug,
                "type": "text",
                "default": None,
                "_widget": "text",
            })

    param_index = {p["slug"]: p for p in params}

    dash_id = create_dashboard(sess, host, args.dashboard_name, args.collection_id, params)

    # Create cards and lay them out 3 per row (24-col grid -> 8 units each)
    created = []
    dashcards_payload: List[Dict[str, Any]] = []
    col = 0
    row = 0
    for f in sql_files:
        card_id, used_slugs = create_card(sess, host, db_id, f["name"], f["sql"], param_index)
        created.append({"card_id": card_id, "name": f["name"], "file": f["file"]})
        dashcards_payload.append(
            {
                "id": -(len(dashcards_payload) + 1),
                "card_id": card_id,
                "row": row,
                "col": col,
                "size_x": 8,
                "size_y": 6,
                "series": [],
                "visualization_settings": {},
                "parameter_mappings": [
                    {
                        "parameter_id": param_index[slug]["id"],
                        "card_id": card_id,
                        "target": ["variable", ["template-tag", slug]],
                    }
                    for slug in used_slugs
                ],
                "dashboard_tab_id": None,
            }
        )
        col += 8
        if col >= 24:
            col = 0
            row += 6

    update_dashboard_layout(
        sess,
        host,
        dash_id,
        args.dashboard_name,
        params,
        dashcards_payload,
        args.collection_id,
    )
    result = {
        "dashboard_id": dash_id,
        "dashboard_url": f"{host.rstrip('/')}/dashboard/{dash_id}",
        "database_id": db_id,
        "cards": created,
        "created_at": int(time.time()),
    }
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"Created dashboard: {result['dashboard_url']}")
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
