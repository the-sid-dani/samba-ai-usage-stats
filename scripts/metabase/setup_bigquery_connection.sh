#!/usr/bin/env bash
set -euo pipefail

# Setup Metabase → BigQuery connection prerequisites under deployer-sa impersonation.
# - Creates/ensures the metabase-bq-reader SA
# - Grants IAM
# - Ensures/creates required secrets
# - Optionally sets VM metadata keys used by infrastructure/metabase/startup.sh
#
# Usage:
#   export CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com
#   gcloud auth print-access-token --impersonate-service-account="$CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT" >/dev/null
#   bash scripts/metabase/setup_bigquery_connection.sh [--project ai-workflows-459123] [--dataset ai_usage_analytics] [--set-metadata]
#
# Idempotent and safe to re-run.

PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
DATASET_ID="ai_usage_analytics"
SET_METADATA=false
ZONE="us-central1-a"
VM_NAME="metabase-vm"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2;;
    --dataset) DATASET_ID="$2"; shift 2;;
    --set-metadata) SET_METADATA=true; shift;;
    --zone) ZONE="$2"; shift 2;;
    --vm) VM_NAME="$2"; shift 2;;
    *) echo "Unknown flag: $1"; exit 2;;
  esac
done

bold() { printf "\033[1m%s\033[0m\n" "$*"; }

preflight() {
  bold "Preflight checks"
  if [[ -z "${PROJECT_ID:-}" ]]; then
    echo "Project not set. Use --project or 'gcloud config set project <id>'." >&2
    exit 1
  fi
  gcloud services enable iamcredentials.googleapis.com >/dev/null 2>&1 || true

  # Verify impersonation works
  local imp_sa="${CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT:-}"
  if [[ -z "$imp_sa" ]]; then
    echo "CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT not set. Export it to deployer-sa before running." >&2
    exit 1
  fi
  if ! gcloud auth print-access-token --impersonate-service-account="$imp_sa" >/dev/null; then
    cat >&2 <<EOF
Impersonation failed for $imp_sa.
Ensure the CALLER (your user) has roles/iam.serviceAccountTokenCreator on:
  $imp_sa
Then retry. See docs/operations/service-accounts.md.
EOF
    exit 1
  fi
  echo "Impersonation OK for $imp_sa"
}

ensure_sa() {
  local sa_id="metabase-bq-reader"
  local sa_email="$sa_id@${PROJECT_ID}.iam.gserviceaccount.com"
  if gcloud iam service-accounts describe "$sa_email" --project "$PROJECT_ID" >/dev/null 2>&1; then
    echo "SA exists: $sa_email"
  else
    gcloud iam service-accounts create "$sa_id" \
      --display-name="Metabase BigQuery Reader" \
      --project "$PROJECT_ID"
  fi
  echo "$sa_email"
}

grant_roles() {
  local sa_email="$1"
  bold "Granting IAM to $sa_email"
  # Project-scoped roles for metadata listing and jobs
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:$sa_email" \
    --role "roles/bigquery.metadataViewer" >/dev/null
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:$sa_email" \
    --role "roles/bigquery.jobUser" >/dev/null

  # Dataset-level dataViewer (preferred). Try GA/alpha paths; if both fail, print manual hint.
  if gcloud alpha bigquery datasets add-iam-policy-binding "$PROJECT_ID:$DATASET_ID" \
      --member="serviceAccount:$sa_email" \
      --role="roles/bigquery.dataViewer" >/dev/null 2>&1; then
    echo "Added dataset IAM via gcloud alpha bigquery."
  else
    echo "Could not add dataset-level IAM with gcloud alpha. Attempting bq fallback..."
    if command -v bq >/dev/null 2>&1; then
      # Safe append using bq (best-effort). This may overwrite if misused, so we avoid set_access.
      echo "Please ensure dataset-level dataViewer exists for $sa_email on $PROJECT_ID:$DATASET_ID." >&2
      echo "Example (manual): bq update --dataset --access=role:READER,userByEmail:$sa_email $PROJECT_ID:$DATASET_ID" >&2
    else
      echo "Install 'bq' to set dataset IAM or add it manually in console." >&2
    fi
  fi
}

ensure_secrets() {
  bold "Ensuring Secret Manager entries"
  local ensure_secret
  ensure_secret() {
    local name="$1"; local value="$2"
    if gcloud secrets describe "$name" --project "$PROJECT_ID" >/dev/null 2>&1; then
      echo "Secret exists: $name (adding new version)"
      printf "%s" "$value" | gcloud secrets versions add "$name" --project "$PROJECT_ID" --data-file=- >/dev/null
    else
      printf "%s" "$value" | gcloud secrets create "$name" --project "$PROJECT_ID" --replication-policy=automatic --data-file=- >/dev/null
    fi
  }

  ensure_secret metabase-bigquery-project "$PROJECT_ID"
  ensure_secret metabase-bigquery-dataset "$DATASET_ID"
  ensure_secret metabase-bigquery-service-account "metabase-bq-reader@${PROJECT_ID}.iam.gserviceaccount.com"
}

maybe_set_vm_metadata() {
  if [[ "$SET_METADATA" == true ]]; then
    bold "Setting VM metadata for $VM_NAME"
    gcloud compute instances add-metadata "$VM_NAME" \
      --zone "$ZONE" \
      --metadata=metabase-bq-project-secret=metabase-bigquery-project,metabase-bq-dataset-secret=metabase-bigquery-dataset,metabase-bq-service-account-secret=metabase-bigquery-service-account || true
  else
    echo "Skipping VM metadata updates (pass --set-metadata to enable)."
  fi
}

post_summary() {
  cat <<EOF

Done. Next steps:
  1) SSH to the VM and run:   sudo /opt/metabase/startup.sh
  2) In Metabase Admin → Databases, add the BigQuery connection (env/impersonation preferred).
  3) Run sql/validation/metabase-connection.sql; capture connection test + timings (<2s agg).

Canonical references:
  - docs/operations/service-accounts.md
  - docs/operations/environment-catalog.yaml
EOF
}

main() {
  preflight
  local sa_email
  sa_email=$(ensure_sa)
  grant_roles "$sa_email"
  ensure_secrets
  maybe_set_vm_metadata
  post_summary
}

main "$@"
