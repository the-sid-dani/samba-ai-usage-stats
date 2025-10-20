# Metabase Dashboard Automation (BigQuery)

This runbook lets you create Metabase dashboards programmatically from a directory of `*.sql` files using the repo script `scripts/metabase/create_dashboards.py`.

Works with a local Metabase on the VM (`http://127.0.0.1:3000`). Credentials are read from a VM-local `.env` and never committed.

**Need a one-liner?** Use the automation helper at `scripts/metabase/run_dashboard_creation.sh`. From the VM:

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
sudo /opt/metabase/tools/run_dashboard_creation.sh
```

The first run creates `/opt/metabase/tools/.env` with placeholders and exits. Edit it with real credentials, rerun, and you’re done.

If you prefer to do it manually, follow the steps below.

## Prerequisites
- Metabase running on the VM and accessible at `http://127.0.0.1:3000`
- Outbound internet access to grab Python packages (one-time)
- Root shell on the VM (commands below assume `root@metabase-vm:~#`)

### Step 0 — Make sure Python tooling exists (one time)

```bash
apt-get update -y
apt-get install -y python3 python3-pip
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade requests python-dotenv
```

### Step 1 — Copy SQL assets to the VM
Use the repo’s ready-made queries under `sql/dashboard/ai_cost`.

```bash
# run from your laptop → VM (adjust user/host)
rsync -av "sql/dashboard/ai_cost/" metabase-vm:/tmp/metabase-assets/sql/dashboard/ai_cost/
```

If you can’t rsync, you can also upload files manually and place them under `/tmp/metabase-assets/sql/dashboard/ai_cost/`.

### Step 2 — Place the tool on the VM
Option A — copy the file from this repo:

```bash
# from your laptop → VM (adjust host)
scp scripts/metabase/create_dashboards.py metabase-vm:/tmp/
ssh metabase-vm "sudo install -d -m 0755 /opt/metabase/tools && sudo mv /tmp/create_dashboards.py /opt/metabase/tools/create_dashboards.py && sudo chmod +x /opt/metabase/tools/create_dashboards.py"
```

Option B — paste directly on the VM (no repo copy):

```bash
install -d -m 0755 /opt/metabase/tools
# Then paste the latest script contents from scripts/metabase/create_dashboards.py into /opt/metabase/tools/create_dashboards.py
chmod +x /opt/metabase/tools/create_dashboards.py
```

### Step 3 — Create a local .env on the VM
This file stays on the VM; do not commit secrets.

```bash
tee /opt/metabase/tools/.env > /dev/null <<'ENV'
MB_HOST=http://127.0.0.1:3000
MB_USER=your-admin@example.com
MB_PASS=replace_me

# Either set MB_DB_ID or MB_DB_NAME (the script resolves by name if present)
# MB_DB_ID=123
MB_DB_NAME=AI Usage Analytics (BigQuery)

# Optional: place dashboard under a collection (numeric id)
# MB_COLLECTION_ID=1
ENV
```

### Step 4 — Run the dashboard creator
Example: create an "AI Cost" dashboard with date filter and number params, writing an output manifest.

```bash
env MB_ENV_FILE=/opt/metabase/tools/.env \
  python3 /opt/metabase/tools/create_dashboards.py \
  --sql-dir /tmp/metabase-assets/sql/dashboard/ai_cost \
  --dashboard-name "AI Cost Dashboard - Q4 2025" \
  --param date_range \
  --number quarter_budget_usd=73000 \
  --number daily_budget_usd=793.48 \
  --number alert_threshold_usd=500 \
  --number inactive_window_days=14 \
  --number total_seats=250 \
  --out /opt/metabase/tools/dashboards.json
```

Expected output:

Created dashboard: http://127.0.0.1:3000/dashboard/<id>
Wrote: /opt/metabase/tools/dashboards.json

Inspect results:

```bash
cat /opt/metabase/tools/dashboards.json
```

## Notes
- Script also accepts `--collection-id`; it now defaults from `MB_COLLECTION_ID` if present.
- You can re-run with different `--dashboard-name` to create additional dashboards.
- Queries are added as cards in a 3×8 layout across a 24‑column grid.

## Troubleshooting
- 401 Unauthorized: verify `MB_USER`/`MB_PASS` in `.env`.
- Connection issues: confirm Metabase is reachable at `MB_HOST`.
- "No BigQuery database found": set `MB_DB_NAME` (or `MB_DB_ID`) to match the Metabase database.
- Python import error: install `requests` and `python-dotenv` on the VM.
