# Service Accounts and Environment Catalog (Source of Truth)

This document is the canonical reference for deployment and runtime identities, their roles, and key resource locations. All agents must follow this when deploying or configuring systems.

## Project and Regions
- Project ID: `ai-workflows-459123`
- Primary region: `us-central1`
- Primary zone: `us-central1-a`
- Primary dataset: `ai_usage_analytics`
- Backup bucket: `gs://samba-metabase-backups`

## Service Accounts

### 1) Deployer (CI/CD & Operators)
- Email: `deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`
- Purpose: Run all Terraform, gcloud, and CI/CD deployment actions across Cursor pipelines and Metabase infra.
- Required roles (project level unless noted):
  - `roles/run.admin`
  - `roles/iam.serviceAccountUser` (on runtime SAs it needs to actAs: `ai-usage-pipeline@…`, `metabase-vm@…`)
  - `roles/cloudscheduler.admin`
  - `roles/artifactregistry.writer`
  - `roles/compute.admin` (to create/manage the Metabase VM)
  - `roles/secretmanager.admin` (create/manage secrets) or narrow to `secretAccessor` if secrets exist already
  - BigQuery: dataset‑level `roles/bigquery.dataOwner` on `ai_usage_analytics` if Terraform manages schema; otherwise `roles/bigquery.jobUser`
- Usage examples (impersonation):
  - `gcloud ... --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`
  - `terraform apply` with ADC: `gcloud auth application-default login --impersonate-service-account=deployer-sa@...`

### 2) Pipeline Runtime (Cloud Run jobs)
- Email: `ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com`
- Purpose: Execute Cursor ingestion/validation jobs.
- Roles:
  - `roles/bigquery.jobUser`
  - Dataset‑level `roles/bigquery.dataEditor` on `ai_usage_analytics`
  - `roles/secretmanager.secretAccessor` on `anthropic-admin-api-key`, `cursor-api-key`

### 3) Scheduler Invoker (Cloud Scheduler)
- Email: `scheduler@ai-workflows-459123.iam.gserviceaccount.com` (or the configured scheduler SA)
- Roles:
  - `roles/run.jobsExecutor`
  - `roles/iam.serviceAccountTokenCreator`

### 4) Metabase VM
- Email: `metabase-vm@ai-workflows-459123.iam.gserviceaccount.com`
- Purpose: Host Metabase and nightly backup jobs on GCE.
- Roles:
  - `roles/secretmanager.secretAccessor`
  - `roles/storage.objectAdmin` (scope to `samba-metabase-backups`)
  - `roles/logging.logWriter`

### 5) Metabase BigQuery Reader
- Email: `metabase-bq-reader@ai-workflows-459123.iam.gserviceaccount.com`
- Purpose: Metabase DB connection identity to query BigQuery.
- Roles:
  - Dataset‑level `roles/bigquery.dataViewer` on `ai_usage_analytics`
  - Optional: `roles/secretmanager.secretAccessor` for connection secrets

## Secret Manager (names)
- `anthropic-admin-api-key`
- `cursor-api-key`
- `metabase-db-password`
- `metabase-admin-email`
- `metabase-admin-password`
- `metabase-encryption-key`
- `metabase-bigquery-project` → value: `ai-workflows-459123`
- `metabase-bigquery-dataset` → value: `ai_usage_analytics`
- `metabase-bigquery-service-account` → value: `metabase-bq-reader@ai-workflows-459123.iam.gserviceaccount.com`
- Optional fallback: `metabase-bigquery-key` (JSON key)

## Impersonation Patterns
- gcloud (user workstation): `gcloud auth login`; then run any command with `--impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`.
- ADC for Terraform: `gcloud auth application-default login --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`.

## Where to Put This in Workflows
- All deployment guides and stories must assume deployments occur under `deployer-sa`.
- Metabase provisioning and BigQuery connection steps should use the identities above; avoid ad‑hoc SAs or plain JSON keys.

