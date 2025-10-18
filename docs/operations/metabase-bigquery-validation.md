# Metabase ↔ BigQuery Validation Steps

Use this checklist after running `scripts/metabase/setup_bigquery_connection.sh` and re-running `/opt/metabase/startup.sh` on the VM.

## Preflight
- Confirm deployer-sa impersonation works: `gcloud auth print-access-token --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`
- Verify VM has `MB_BIGQUERY_*` in `/opt/metabase/metabase.env`

## Metabase Admin
1. Admin → Databases → Add database → BigQuery
2. Prefer environment/impersonation (MB_BIGQUERY_*); if JSON fallback used, select Service Account JSON
3. Set `processing_location=US`

## Connection Test & Evidence
- Take a screenshot of the successful connection test
- Run all queries in `sql/validation/metabase-connection.sql`
- Record timing results (< 2s for simple aggregations) and paste into `docs/validation/metabase_connection_YYYY-MM-DD.md`

## Expected Tables & Views
- Tables: claude_ai_usage_stats, claude_code_usage_stats, cursor_usage_stats, claude_usage_report, claude_cost_report, cursor_spending, dim_api_keys, dim_workspaces
- Views: vw_claude_ai_daily_summary, vw_engineering_productivity, vw_combined_daily_costs

## Troubleshooting
- Permission denied listing tables → ensure `metabase-bq-reader@…` has dataset-level `roles/bigquery.dataViewer` and project `roles/bigquery.metadataViewer`
- Impersonation failure → ensure your user has `roles/iam.serviceAccountTokenCreator` on deployer-sa
- Env not loaded → rerun `/opt/metabase/startup.sh` and check `/opt/metabase/metabase.env`
