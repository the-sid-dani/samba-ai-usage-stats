#!/usr/bin/env bash
set -euo pipefail

# Programmatic Metabase Dashboard Creator
# ---------------------------------------
# Automates cloning/updating the repo on the VM, staging SQL assets, and
# running create_dashboards.py. Run as root (or with sudo) on the Metabase VM.
#
# You may override any variable via environment variables before invoking
# (e.g. `REPO_URL=... ./run_dashboard_creation.sh`).

log() {
  echo "[run-dashboard-creation] $*"
}

REPO_URL=${REPO_URL:-"https://github.com/the-sid-dani/samba-ai-usage-stats.git"}
REPO_DIR=${REPO_DIR:-"/usr/local/src/samba-ai-usage-stats"}
REPO_REF=${REPO_REF:-"metabase-bq-setup"}
SQL_ASSETS_SRC=${SQL_ASSETS_SRC:-"sql/dashboard/ai_cost"}
DASHBOARD_SCRIPT_SRC=${DASHBOARD_SCRIPT_SRC:-"scripts/metabase/create_dashboards.py"}
TOOLS_DIR=${TOOLS_DIR:-"/opt/metabase/tools"}
ASSETS_DEST_DIR=${ASSETS_DEST_DIR:-"/tmp/metabase-assets"}
DASHBOARD_NAME=${DASHBOARD_NAME:-"AI Cost Dashboard - Q4 2025"}
DASHBOARD_OUT=${DASHBOARD_OUT:-"$TOOLS_DIR/dashboards.json"}

log "Starting Metabase dashboard automation"

log "Ensuring git/python dependencies are installed"
apt-get update -y >/dev/null
apt-get install -y git python3 python3-pip >/dev/null
python3 -m pip install --upgrade pip requests python-dotenv >/dev/null

# Ensure repo is on desired ref
log "Cloning or updating repository at $REPO_DIR (ref: $REPO_REF)"
if [[ -d "$REPO_DIR/.git" ]]; then
  git -C "$REPO_DIR" fetch origin "$REPO_REF"
  git -C "$REPO_DIR" checkout "$REPO_REF"
  git -C "$REPO_DIR" pull --ff-only origin "$REPO_REF"
else
  rm -rf "$REPO_DIR"
  git clone --branch "$REPO_REF" --single-branch "$REPO_URL" "$REPO_DIR"
fi

log "Staging SQL assets under $ASSETS_DEST_DIR"
mkdir -p "$ASSETS_DEST_DIR/sql/dashboard"
rm -rf "$ASSETS_DEST_DIR/sql/dashboard/$(basename "$SQL_ASSETS_SRC")"
cp -R "$REPO_DIR/$SQL_ASSETS_SRC" "$ASSETS_DEST_DIR/sql/dashboard/"

log "Installing dashboard script to $TOOLS_DIR"
install -d -m 0755 "$TOOLS_DIR"
install -m 0755 "$REPO_DIR/$DASHBOARD_SCRIPT_SRC" "$TOOLS_DIR/create_dashboards.py"

if [[ ! -f "$TOOLS_DIR/.env" ]]; then
  log "Creating initial $TOOLS_DIR/.env (update credentials before re-running)"
  tee "$TOOLS_DIR/.env" >/dev/null <<'ENV'
MB_HOST=http://127.0.0.1:3000
MB_USER=your-admin@example.com
MB_PASS=replace_me

# Either set MB_DB_ID or MB_DB_NAME (the script resolves by name if present)
# MB_DB_ID=123
MB_DB_NAME=AI Usage Analytics (BigQuery)

# Optional: place dashboard under a collection (numeric id)
# MB_COLLECTION_ID=1
ENV
  log "Edit $TOOLS_DIR/.env with real credentials, then rerun the script."
  exit 0
fi

set -o allexport
# shellcheck source=/dev/null
source "$TOOLS_DIR/.env"
set +o allexport

if [[ "${MB_PASS:-replace_me}" == "replace_me" || "${MB_USER:-your-admin@example.com}" == "your-admin@example.com" ]]; then
  log "MB_USER/MB_PASS still placeholders. Update $TOOLS_DIR/.env and rerun."
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

log "Dashboard creation complete; output manifest: $DASHBOARD_OUT"
cat "$DASHBOARD_OUT"
