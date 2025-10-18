# Metabase on GCE – Provisioning Guide

This directory contains the Docker Compose stack and bootstrap scripts required to run Metabase on a Google Compute Engine VM with a PostgreSQL metadata store.

## Contents

- `docker-compose.yml` – Metabase + PostgreSQL stack (port 3000, persistent volumes)
- `metabase.env.example` – Template env file populated from Secret Manager during bootstrap
- `startup.sh` – Idempotent bootstrap script that installs dependencies, fetches secrets, and wires Docker Compose + systemd
- `backup-metabase.sh` – Daily `pg_dump` helper invoked by a systemd timer to push backups to Cloud Storage

## Prerequisites

0. Deployment identity (required)

All provisioning and configuration must run under the project deployer service account to ensure the right permissions and audit trail.

- Deployer SA: `deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`
- Impersonation examples:
  - `gcloud ... --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`
  - `gcloud auth application-default login --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com` (for Terraform)
- See `docs/operations/service-accounts.md` for full role requirements.

1. **GCP project metadata**
   - Region: `us-central1`
   - VM name: `metabase-vm`
   - Service account with the following roles:
     - `roles/secretmanager.secretAccessor`
     - `roles/storage.objectAdmin` (restricted to backup bucket)
     - `roles/logging.logWriter`
2. **Static IP for the VM**
   ```bash
   gcloud compute addresses create metabase-static-ip \
     --region=us-central1
   ```
3. **Cloud Storage bucket for backups**
   ```bash
   gsutil mb -l us-central1 gs://samba-metabase-backups
   ```
4. **Secret Manager entries (store admin + database credentials)**
   ```bash
   echo "strong-db-password" | gcloud secrets create metabase-db-password --data-file=-
   echo "admin@example.com"  | gcloud secrets create metabase-admin-email --data-file=-
   echo "strong-admin-pass"  | gcloud secrets create metabase-admin-password --data-file=-
   openssl rand -base64 32   | gcloud secrets create metabase-encryption-key --data-file=-
   ```
5. **Metabase ↔ BigQuery connectivity (Story 4.2)**
   - Create/read-only service account that Metabase will impersonate:
     ```bash
     gcloud iam service-accounts create metabase-bq-reader \
       --display-name="Metabase BigQuery Reader"
     gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
       --member="serviceAccount:metabase-bq-reader@${PROJECT_ID}.iam.gserviceaccount.com" \
       --role="roles/bigquery.dataViewer"
     ```
   - Optional: if using a JSON key (MVP fallback), generate and store it:
     ```bash
     gcloud iam service-accounts keys create /tmp/metabase-bq-key.json \
       --iam-account=metabase-bq-reader@${PROJECT_ID}.iam.gserviceaccount.com
     gcloud secrets create metabase-bigquery-key --data-file=/tmp/metabase-bq-key.json
     rm /tmp/metabase-bq-key.json
     ```
   - Store project/dataset overrides (if different from defaults) in Secret Manager:
     ```bash
     printf "%s" "${PROJECT_ID}"      | gcloud secrets create metabase-bigquery-project --data-file=-
     printf "ai_usage_analytics"      | gcloud secrets create metabase-bigquery-dataset  --data-file=-
     printf "%s" "metabase-bq-reader@${PROJECT_ID}.iam.gserviceaccount.com" \
       | gcloud secrets create metabase-bigquery-service-account --data-file=-
     ```

## Firewall – Restrict Port 3000

Allow Metabase UI access only from approved ranges (replace CIDRs as needed):

```bash
gcloud compute firewall-rules create metabase-allow-3000 \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:3000 \
  --source-ranges=203.0.113.10/32,198.51.100.24/32
```

## Provisioning Steps

Run all commands with impersonation, e.g. `--impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`. The VM service account should be `metabase-vm@ai-workflows-459123.iam.gserviceaccount.com` with roles listed in `docs/operations/service-accounts.md`.

1. **Create the VM**
   ```bash
   gcloud compute instances create metabase-vm \
     --zone=us-central1-a \
     --machine-type=e2-medium \
     --image-family=ubuntu-2004-lts \
     --image-project=ubuntu-os-cloud \
     --boot-disk-size=50GB \
     --address=metabase-static-ip \
     --tags=metabase \
     --service-account=metabase-vm@${PROJECT_ID}.iam.gserviceaccount.com \
     --scopes=https://www.googleapis.com/auth/cloud-platform
   ```
2. **Attach backup bucket metadata (enables automated pg_dump)**
   ```bash
   gcloud compute instances add-metadata metabase-vm \
     --zone=us-central1-a \
     --metadata=metabase-backup-bucket=samba-metabase-backups,metabase-site-url=https://metabase.example.com,metabase-bq-project-secret=metabase-bigquery-project,metabase-bq-dataset-secret=metabase-bigquery-dataset,metabase-bq-service-account-secret=metabase-bigquery-service-account,metabase-bq-credentials-secret=metabase-bigquery-key
   ```
   - Override secret names if required: add `metabase-db-password-secret`, `metabase-admin-email-secret`, etc.
3. **Copy provisioning assets to the VM**
   ```bash
   gcloud compute scp \
     infrastructure/metabase/* \
     metabase-vm:/tmp/metabase-assets \
     --zone=us-central1-a --recurse
   ```
   - Optional helper: run `scripts/metabase/setup_bigquery_connection.sh` locally (with impersonation) to create the reader SA, populate secrets, and set metadata before SSHing.
4. **SSH into the VM and run the bootstrap script**
   ```bash
   gcloud compute ssh metabase-vm --zone=us-central1-a
   sudo mkdir -p /opt/metabase
   cd /tmp/metabase-assets
   sudo chmod +x startup.sh backup-metabase.sh
   sudo ./startup.sh
   ```
   - The script installs Docker, configures the compose stack, writes `/opt/metabase/metabase.env` with values from Secret Manager, and enables systemd units for the application and nightly backups.

5. **Verify services**
   ```bash
   sudo systemctl status metabase.service
   sudo systemctl status metabase-backup.timer
   docker compose --project-name metabase -f /opt/metabase/docker-compose.yml ps
   ```

## Persistent Storage & Backups

- PostgreSQL data resides on the `metabase-db-data` Docker volume (host path: `/var/lib/docker/volumes/metabase-db-data/_data`).
- Nightly backups run via `metabase-backup.timer` at 03:00 UTC:
  - Dumps are produced with `pg_dump` and uploaded to `gs://$MB_BACKUP_BUCKET/metabase/`.
  - Local copies are retained under `/opt/metabase/backups` for 30 days.
- Validate backups:
  ```bash
  gsutil ls gs://samba-metabase-backups/metabase/
  sudo journalctl -u metabase-backup.service --since "1 day ago"
  ```

## Post-Deployment Checklist

- Record the Metabase BigQuery connection identity as `metabase-bq-reader@ai-workflows-459123.iam.gserviceaccount.com`. Store canonical values in `docs/operations/environment-catalog.yaml`.

- Update DNS to point to the static IP, then enable HTTPS (recommend Google-managed certificate via HTTPS Load Balancer).
- Configure SMTP settings in Metabase (Admin → Settings → Email) for alerts.
- Configure the BigQuery database connection in Metabase Admin → Databases, referencing the environment variables populated by `startup.sh`; capture connection test evidence for Story 4.2.
- Disable sample data (`MB_CREATE_SAMPLE_DATA=false` is set) and invite authorized users.
- Rotate admin and database secrets quarterly; update Secret Manager versions and rerun `sudo ./startup.sh` to pull fresh values.
- Update firewall rule source ranges as teams change.
- Follow the validation checklist in `docs/operations/metabase-bigquery-validation.md` to record QA artifacts (<2s query timings, connection screenshots).
