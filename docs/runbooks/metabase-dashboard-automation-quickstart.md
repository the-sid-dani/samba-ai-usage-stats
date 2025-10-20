# Metabase Dashboard Automation — Quickstart

Use this guide when you are SSH’d into the VM as `root@metabase-vm:~#`. It installs the automation helper, collects SQL assets from the correct branch, and runs the dashboard creator. Follow the steps in order.

---

## 1. Install or refresh the helper script
Run this every time you want the latest helper (safe to re-run).

```bash
install -d -m 0755 /opt/metabase/tools
cat <<'EOF' >/opt/metabase/tools/run_dashboard_creation.sh
#!/usr/bin/env bash
set -euo pipefail

log() { echo "[run-dashboard-creation] $*"; }

REPO_URL=${REPO_URL:-"https://github.com/the-sid-dani/samba-ai-usage-stats.git"}
REPO_DIR=${REPO_DIR:-"/usr/local/src/samba-ai-usage-stats"}
REPO_REF=${REPO_REF:-"metabase-bq-setup"}
SQL_ASSETS_SRC=${SQL_ASSETS_SRC:-"sql/dashboard/ai_cost"}
DASHBOARD_SCRIPT_SRC=${DASHBOARD_SCRIPT_SRC:-"scripts/metabase/create_dashboards.py"}
TOOLS_DIR=${TOOLS_DIR:-"/opt/metabase/tools"}
ASSETS_DEST_DIR=${ASSETS_DEST_DIR:-"/tmp/metabase-assets"}
DASHBOARD_NAME=${DASHBOARD_NAME:-"AI Cost Dashboard - Q4 2025"}
DASHBOARD_OUT=${DASHBOARD_OUT:-"$TOOLS_DIR/dashboards.json"}

log "Ensuring git/python dependencies"
apt-get update -y >/dev/null
apt-get install -y git python3 python3-pip >/dev/null
python3 -m pip install --upgrade pip requests python-dotenv >/dev/null

log "Syncing repo (ref: $REPO_REF)"
if [[ -d "$REPO_DIR/.git" ]]; then
  git -C "$REPO_DIR" fetch origin "$REPO_REF"
  git -C "$REPO_DIR" checkout "$REPO_REF"
  git -C "$REPO_DIR" pull --ff-only origin "$REPO_REF"
else
  rm -rf "$REPO_DIR"
  git clone --branch "$REPO_REF" --single-branch "$REPO_URL" "$REPO_DIR"
fi

log "Copying SQL assets"
mkdir -p "$ASSETS_DEST_DIR/sql/dashboard"
rm -rf "$ASSETS_DEST_DIR/sql/dashboard/$(basename "$SQL_ASSETS_SRC")"
cp -R "$REPO_DIR/$SQL_ASSETS_SRC" "$ASSETS_DEST_DIR/sql/dashboard/"

log "Installing create_dashboards.py"
install -d -m 0755 "$TOOLS_DIR"
install -m 0755 "$REPO_DIR/$DASHBOARD_SCRIPT_SRC" "$TOOLS_DIR/create_dashboards.py"

if [[ ! -f "$TOOLS_DIR/.env" ]]; then
  log "Creating $TOOLS_DIR/.env placeholders"
  cat <<'ENV' >"$TOOLS_DIR/.env"
MB_HOST=http://127.0.0.1:3000
MB_USER=your-admin@example.com
MB_PASS=replace_me
# MB_DB_ID=123
MB_DB_NAME=AI Usage Analytics (BigQuery)
# MB_COLLECTION_ID=1
ENV
  log "Update credentials in $TOOLS_DIR/.env and rerun."
  exit 0
fi

set -o allexport
source "$TOOLS_DIR/.env"
set +o allexport

if [[ "${MB_USER}" == "your-admin@example.com" || "${MB_PASS}" == "replace_me" ]]; then
  log "Credentials still placeholders; edit $TOOLS_DIR/.env and rerun."
  exit 1
fi

log "Running dashboard creator"
env MB_ENV_FILE="$TOOLS_DIR/.env" \
  python3 "$TOOLS_DIR/create_dashboards.py" \
  --sql-dir "$ASSETS_DEST_DIR/sql/dashboard/$(basename "$SQL_ASSETS_SRC")" \
  --dashboard-name "$DASHBOARD_NAME" \
  --param date_range \
  --number quarter_budget_usd=73000 \
  --number daily_budget_usd=793.48 \
  --number alert_threshold_usd=500 \
  --number inactive_window_days=14 \
  --number total_seats=250 \
  --out "$DASHBOARD_OUT"

log "Dashboard manifest at $DASHBOARD_OUT"
cat "$DASHBOARD_OUT"
EOF
chmod +x /opt/metabase/tools/run_dashboard_creation.sh
```

> Note: cloning runs as root; pip warns about system installs — acceptable on this utility VM, but switch to a venv if you prefer isolation.

---

## 2. Run the helper for the first time
```bash
sudo /opt/metabase/tools/run_dashboard_creation.sh
```
- On the first run, the script exits after creating `/opt/metabase/tools/.env` with placeholders.
- Edit the file with real Metabase credentials and (optionally) database/collection info:
  ```bash
  nano /opt/metabase/tools/.env
  ```
  Set at minimum `MB_USER` and `MB_PASS`. Use `MB_DB_NAME` or `MB_DB_ID` to target the correct BigQuery connection.

---

## 3. Run again to create the dashboard
```bash
sudo /opt/metabase/tools/run_dashboard_creation.sh
```
- This time the script logs in, copies SQL files, creates cards, assembles the dashboard, and writes the manifest to `/opt/metabase/tools/dashboards.json`.
- After it finishes, open the printed URL in a browser (e.g., `http://127.0.0.1:3000/dashboard/<id>`).

---

## 4. Refreshing later
Whenever SQL queries or parameters change, rerun step 3. The helper will:
1. `git fetch` the `metabase-bq-setup` branch.
2. Replace the staged SQL directory under `/tmp/metabase-assets/sql/dashboard/ai_cost/`.
3. Re-install the latest `create_dashboards.py`.
4. Re-create the dashboard and emit an updated manifest.

Optional overrides per run:
```bash
REPO_REF=metabase-bq-setup DASHBOARD_NAME="AI Cost Dashboard - FY26" \
  sudo /opt/metabase/tools/run_dashboard_creation.sh
```
(The script reads variables such as `REPO_URL`, `REPO_DIR`, `SQL_ASSETS_SRC`, `DASHBOARD_NAME`, `DASHBOARD_OUT` from the environment before running.)

---

## 5. Troubleshooting
- **Missing SQL directory** – ensure the target branch actually contains `sql/dashboard/ai_cost/`. Change `SQL_ASSETS_SRC` if using another folder.
- **Metabase login failures** – verify `MB_USER`/`MB_PASS` in `.env`, and that the VM can reach `MB_HOST`.
- **Wrong database** – supply `MB_DB_NAME` or `MB_DB_ID` in `.env`.
- **Dependencies** – rerun step 1 to reinstall the script; it also refreshes Python packages.

Keep this file in the repo so future runs stay reproducible.
