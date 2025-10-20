# Metabase VM Setup — Commands to Run on `root@metabase-vm`

This sequence assumes you are already SSH’d into the VM as `root@metabase-vm:~#`.

**Shortcut:** if you just want a one-shot automation, run the helper script we ship:

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

The first run creates `/opt/metabase/tools/.env` with placeholders and exits. Edit the file, rerun the script, and it will handle the rest. If you prefer the manual steps, continue below.

---

## Manual Step-By-Step
Run each block in order if you want to replicate the workflow without the helper script.

---

## 1. Install prerequisites (Git, Python, pip packages)
```bash
apt-get update -y && \
apt-get install -y git python3 python3-pip && \
python3 -m pip install --upgrade pip && \
python3 -m pip install --upgrade requests python-dotenv
```

## 2. Clone the repository locally on the VM
```bash
rm -rf /opt/metabase/assets-repo && \
git clone https://github.com/the-sid-dani/samba-ai-usage-stats.git /opt/metabase/assets-repo
```

## 3. Copy SQL assets into the working directory
```bash
install -d -m 0755 /tmp/metabase-assets/sql/dashboard/ai_cost && \
rsync -av /opt/metabase/assets-repo/sql/dashboard/ai_cost/ /tmp/metabase-assets/sql/dashboard/ai_cost/
```

## 4. Install the dashboard creator script
```bash
install -d -m 0755 /opt/metabase/tools && \
cp /opt/metabase/assets-repo/scripts/metabase/create_dashboards.py /opt/metabase/tools/create_dashboards.py && \
chmod +x /opt/metabase/tools/create_dashboards.py
```

## 5. Create the local Metabase `.env`
```bash
tee /opt/metabase/tools/.env > /dev/null <<'ENV'
MB_HOST=http://127.0.0.1:3000
MB_USER=your-admin@example.com
MB_PASS=replace_me

# Either set MB_DB_ID or MB_DB_NAME (the script resolves by name if present)
# MB_DB_ID=123
MB_DB_NAME=AI Usage Analytics (BigQuery)

# Optional: collection id
# MB_COLLECTION_ID=1
ENV
```

## 6. Run the dashboard creator (adjust params as needed)
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

## 7. Inspect the results
```bash
cat /opt/metabase/tools/dashboards.json
```

You can repeat Step 6 with different `--sql-dir` folders or dashboard names whenever you need to create a new dashboard. Remove `/opt/metabase/assets-repo` afterwards if you don’t want to keep a local clone on the VM.
