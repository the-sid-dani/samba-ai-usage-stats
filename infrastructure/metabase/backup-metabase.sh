#!/usr/bin/env bash
set -euo pipefail

# Simple local backup; uploads to GCS if gcloud/gsutil are available and MB_BACKUP_BUCKET is set.

: "${MB_DB_USER:=metabase_app}"
: "${MB_DB_NAME:=metabase}"
: "${MB_BACKUP_DIR:=/opt/metabase/backups}"

mkdir -p "$MB_BACKUP_DIR"
ts=$(date -u +"%Y%m%dT%H%M%SZ")
outfile="$MB_BACKUP_DIR/metabase_${ts}.sql"

# Use docker compose exec to dump Postgres
if command -v docker >/dev/null 2>&1; then
  docker compose -f /opt/metabase/docker-compose.yml exec -T metabase-db pg_dump -U "$MB_DB_USER" "$MB_DB_NAME" > "$outfile"
else
  echo "[backup] Docker not found; cannot perform backup" >&2
  exit 1
fi

echo "[backup] Local dump written: $outfile"

# Optional: upload to GCS if bucket configured
if [[ -n "${MB_BACKUP_BUCKET:-}" ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    gcloud storage cp "$outfile" "gs://${MB_BACKUP_BUCKET}/metabase/" || echo "[backup] Upload failed (gcloud)" >&2
  elif command -v gsutil >/dev/null 2>&1; then
    gsutil cp "$outfile" "gs://${MB_BACKUP_BUCKET}/metabase/" || echo "[backup] Upload failed (gsutil)" >&2
  else
    echo "[backup] gcloud/gsutil not installed; skipping upload" >&2
  fi
fi
