# Metabase GCE Provisioning Runbook

This runbook summarizes the infrastructure artifacts and operational steps for Story 4.1 (Metabase infrastructure). Compose and bootstrap assets live in `infrastructure/metabase/`.

## Assets

| Artifact | Purpose | Location |
| --- | --- | --- |
| `docker-compose.yml` | Deploys Metabase + PostgreSQL with health checks and persistent volumes | `infrastructure/metabase/docker-compose.yml` |
| `metabase.env.example` | Documents required environment variables populated from Secret Manager | `infrastructure/metabase/metabase.env.example` |
| `startup.sh` | Installs Docker, syncs assets to `/opt/metabase`, fetches secrets (admin + BigQuery), enables systemd units | `infrastructure/metabase/startup.sh` |
| `backup-metabase.sh` | Nightly `pg_dump` job uploaded to Cloud Storage via systemd timer | `infrastructure/metabase/backup-metabase.sh` |
| Provisioning guide | Firewall, static IP, VM + bootstrap steps | `infrastructure/metabase/README.md` |

## Acceptance Criteria Mapping

- **AC1 e2-medium VM / Docker:** `startup.sh` installs Docker on Ubuntu 20.04 and is executed post `gcloud compute instances create` (instructions in README).
- **AC2 Docker Compose:** `docker-compose.yml` defines Metabase 0.49.14 + PostgreSQL 13 with dependency health checks.
- **AC3 Port 3000 firewall:** README documents `metabase-allow-3000` firewall rule restricted to company CIDRs.
- **AC4 Persistent PostgreSQL + backup:** Volume `metabase-db-data` ensures local persistence; `backup-metabase.sh` + timer pushes daily backups to `gs://$MB_BACKUP_BUCKET`.
- **AC5 Admin credentials in Secret Manager:** `startup.sh` pulls email/password/encryption secrets via `gcloud secrets versions access`.
- **AC6 Static IP + startup automation:** README covers reserving `metabase-static-ip`; systemd unit `metabase.service` restarts the stack automatically on reboot.

## Operational Steps (Summary)

Impersonate the deployer service account for all commands:

```
gcloud <command> --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com
```

Canonical identities and resources: see `docs/operations/service-accounts.md` and `docs/operations/environment-catalog.yaml`. 

1. Reserve static IP and create firewall rule `metabase-allow-3000`.
2. Create `metabase-db-password`, `metabase-admin-email`, `metabase-admin-password`, `metabase-encryption-key` secrets.
3. Create backup bucket (e.g., `gs://samba-metabase-backups`) and grant VM service account write access.
4. Provision VM (`e2-medium`, Ubuntu 20.04) with the static IP and scopes `cloud-platform`.
5. Add metadata attributes:
   - `metabase-backup-bucket=<bucket-name>`
   - `metabase-bq-project-secret`, `metabase-bq-dataset-secret`, `metabase-bq-service-account-secret`, `metabase-bq-credentials-secret` (if using JSON key)
   - Optional overrides: `metabase-site-url`, `metabase-site-name`, `metabase-*-secret`
   - Shortcut: run `scripts/metabase/setup_bigquery_connection.sh` locally (with deployer-sa impersonation) to automate SA creation, secret population, and metadata wiring.
6. Copy `infrastructure/metabase/` to the VM and execute `sudo ./startup.sh`.
7. Validate services:
   - `systemctl status metabase.service`
   - `systemctl status metabase-backup.timer`
   - `docker compose --project-name metabase -f /opt/metabase/docker-compose.yml ps`
8. Point DNS to the reserved static IP, configure HTTPS termination, and complete the Metabase first-run wizard.
9. Execute the validation checklist in `docs/operations/metabase-bigquery-validation.md` and attach artifacts to Story 4.2.

## Backup & Restore

- Backups land at `gs://$MB_BACKUP_BUCKET/metabase/<timestamp>.sql`.
- To restore:
  1. Download target dump locally or onto the VM.
  2. Stop stack: `sudo systemctl stop metabase.service`.
  3. Restore: `cat metabase-<timestamp>.sql | docker compose --project-name metabase -f /opt/metabase/docker-compose.yml exec -T metabase-db psql -U metabase_app metabase`.
  4. Start stack: `sudo systemctl start metabase.service`.

## Observability

- Health endpoint: `GET http://<static-ip>:3000/api/health`
- Logs:
  - Metabase app: `docker compose --project-name metabase -f /opt/metabase/docker-compose.yml logs -f metabase`
  - Systemd: `journalctl -u metabase.service`
  - Backups: `journalctl -u metabase-backup.service`
- Monitoring recommendation: add uptime check (port 3000) and Cloud Monitoring log-based alert on backup failures.
- Verify BigQuery connectivity post-boot:
  - Confirm `/opt/metabase/metabase.env` contains `MB_BIGQUERY_*` variables populated from Secret Manager/metadata.
  - If a JSON key is used, ensure `/opt/metabase/metabase-bigquery-key.json` exists with `0600` permissions.
  - Within Metabase Admin → Databases, run connection test and capture screenshot for Story 4.2 audit trail.
