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
    --param date_range \
    --number quarter_budget_usd=73000 --number daily_budget_usd=793.48 \
    --number alert_threshold_usd=500 --number inactive_window_days=14 --number total_seats=250 \
    --out dashboards.json
"""
import argparse, json, os, sys, time, pathlib
from typing import List, Dict, Any, Optional
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
    dbs = r.json()
    if name:
        for d in dbs:
            if d.get("engine") == "bigquery" and name.lower() in str(d.get("name", "")).lower():
                return int(d["id"])
    for d in dbs:
        if d.get("engine") == "bigquery":
            return int(d["id"])
    raise SystemExit("No BigQuery database found in Metabase")


def read_sql_files(sql_dir: str) -> List[Dict[str, str]]:
    files = sorted(pathlib.Path(sql_dir).glob("*.sql"))
    if not files:
        raise SystemExit(f"No .sql files found in {sql_dir}")
    out = []
    for f in files:
        out.append({"name": f.stem.replace("_", " ").title(), "file": str(f), "sql": f.read_text()})
    return out


def create_card(sess: requests.Session, host: str, db_id: int, title: str, sql: str) -> int:
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
    r = sess.post(f"{host.rstrip('/')}/api/card", json=payload)
    r.raise_for_status()
    return r.json()["id"]


def create_dashboard(
    sess: requests.Session, host: str, name: str, collection_id: Optional[int], parameters: List[Dict[str, Any]]
) -> int:
    payload: Dict[str, Any] = {"name": name, "parameters": parameters}
    if collection_id is not None:
        payload["collection_id"] = collection_id
    r = sess.post(f"{host.rstrip('/')}/api/dashboard", json=payload)
    r.raise_for_status()
    return r.json()["id"]


def add_card_to_dashboard(
    sess: requests.Session, host: str, dash_id: int, card_id: int, row: int, col: int, sx: int = 8, sy: int = 6
) -> None:
    payload = {"cardId": card_id, "row": row, "col": col, "sizeX": sx, "sizeY": sy}
    r = sess.post(f"{host.rstrip('/')}/api/dashboard/{dash_id}/cards", json=payload)
    r.raise_for_status()


def parse_number_kv(pairs: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in pairs:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        try:
            vnum = float(v)
        except ValueError:
            vnum = v
        out.append({"name": k, "slug": k, "type": "number", "default": vnum})
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
    for p in args.param:
        if "date" in p:
            params.append({"name": p, "slug": p, "type": "date/all-options"})
        else:
            params.append({"name": p, "slug": p, "type": "text"})
    params.extend(parse_number_kv(args.number))

    dash_id = create_dashboard(sess, host, args.dashboard_name, args.collection_id, params)

    # Create cards and lay them out 3 per row (24-col grid -> 8 units each)
    created = []
    col = 0
    row = 0
    for f in sql_files:
        card_id = create_card(sess, host, db_id, f["name"], f["sql"])
        add_card_to_dashboard(sess, host, dash_id, card_id, row=row, col=col, sx=8, sy=6)
        created.append({"card_id": card_id, "name": f["name"], "file": f["file"]})
        col += 8
        if col >= 24:
            col = 0
            row += 6

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
