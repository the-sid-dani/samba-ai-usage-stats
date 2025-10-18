# Epic 4: Metabase Dashboard Suite
Archon Project ID: cb4ceffa-9f56-4e05-9040-897c0a970a22

**Goal:** Deploy self-hosted Metabase on GCP Compute Engine and build all three dashboards (AI Cost Dashboard, AI Engineering Productivity Dashboard, Claude Desktop Usage Dashboard) with complete SQL queries, visualizations, and export capabilities. This epic delivers the primary business value by making all collected data accessible and actionable for finance, engineering, and product stakeholders.

## Story 4.1: Provision Metabase Infrastructure on GCP

Deployment Standard: All infra changes (gcloud/Terraform/VM bootstrap) must be executed using the project deployer service account `deployer-sa@ai-workflows-459123.iam.gserviceaccount.com` (see `docs/operations/service-accounts.md`).
Archon Task ID: 6dd10454-c411-4fd3-84fb-3946deb952f3

As a DevOps engineer,
I want to deploy Metabase on GCP Compute Engine with PostgreSQL metadata storage,
so that we have a stable BI platform for dashboard hosting.

**Acceptance Criteria:**
1. GCP Compute Engine e2-medium VM (2 vCPUs, 4GB RAM) provisioned in us-central1 with Ubuntu 20.04 and Docker installed
2. Docker Compose configuration created with Metabase container (latest) and PostgreSQL 13 container for metadata storage
3. Metabase accessible on port 3000 with firewall rule allowing access from company IP ranges and blocking all other traffic
4. PostgreSQL data persisted to Docker volume with automated daily backup to Cloud Storage bucket
5. Initial Metabase admin account created and admin credentials stored in Secret Manager
6. VM configured with static external IP and automated startup script to launch Docker Compose on reboot

#### Implementation Updates

- Delivered a reproducible Metabase + PostgreSQL stack under `infrastructure/metabase/`.
  - `docker-compose.yml` provisions `metabase/metabase:v0.49.14` alongside PostgreSQL 13 with health checks, persistent volumes for database/plugins/logs, JVM tuning (`JAVA_TOOL_OPTIONS`), and hardened defaults (`MB_PASSWORD_COMPLEXITY=strong`, `MB_CREATE_SAMPLE_DATA=false`).
  - `metabase.env.example` documents the runtime contract (site URL, admin bootstrap user, encryption key, backup bucket) so secrets can be sourced from Secret Manager without leaving credentials on disk.
- Automated VM bootstrap via `startup.sh` to satisfy install, security, and resiliency requirements.
  - Installs Docker, the compose plugin, and (if missing) the gcloud CLI; assigns the invoking sudo user to the docker group and logs to `/var/log/metabase-bootstrap.log`.
  - Fetches secret names from instance metadata (with sane defaults) and pulls the latest Secret Manager versions to materialize `/opt/metabase/metabase.env`, ensuring admin credentials and encryption keys never persist outside memory.
  - Registers a systemd service that runs `docker compose up -d` on boot and a timer-backed `metabase-backup.service` that executes nightly `pg_dump` uploads via `backup-metabase.sh` to `gs://$MB_BACKUP_BUCKET`, keeping 30 days of local snapshots.
- Captured operator guidance that maps directly to the acceptance criteria.
  - `infrastructure/metabase/README.md` documents reserving the static IP, restricting firewall ingress to approved CIDRs, copying assets, and validating compose health.
  - `docs/operations/metabase-gce-provisioning.md` links each acceptance criterion to the provisioning assets, outlines metadata overrides (e.g., `metabase-site-url`), and details verification commands (`systemctl status`, `docker compose ps`, backup log checks).
- Outstanding follow-ups before declaring production readiness:
  1. Run the bootstrap on the target VM and record verification evidence (screenshots, command output) for QA.
  2. Configure HTTPS termination (Cloud Load Balancer + managed certificate) and wire SMTP settings once DNS points to the static IP.

## Story 4.2: Connect Metabase to BigQuery

Identity & Permissions: Configure the Metabase connection to impersonate `metabase-bq-reader@ai-workflows-459123.iam.gserviceaccount.com`. Provision and IAM bindings must be applied under `deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`. Reference `docs/operations/service-accounts.md` and `docs/operations/environment-catalog.yaml` for canonical values.
Archon Task ID: f4cfd823-0ec7-4ab8-9f61-d04557b72b30

As a data analyst,
I want Metabase connected to our BigQuery dataset,
so that I can query all 8 tables for dashboard creation.

**Acceptance Criteria:**
1. GCP service account created with BigQuery Data Viewer role for `ai_usage_analytics` dataset
2. Metabase BigQuery connection uses secrets loaded at runtime from Secret Manager (no persistent key files) [MVP]; [Post-MVP] adopt Workload Identity Federation
3. Metabase connection test successful showing all 8 tables (claude_ai_usage_stats, claude_code_usage_stats, cursor_usage_stats, claude_usage_report, claude_cost_report, cursor_spending, dim_api_keys, dim_workspaces)
4. Test query executed successfully from Metabase query editor returning sample data from each table
5. All 3 pre-aggregated views accessible (vw_claude_ai_daily_summary, vw_engineering_productivity, vw_combined_daily_costs)
6. Query performance validated (simple aggregations complete in < 2 seconds)
7. No service account keys are stored on disk on the Metabase VM; secrets handled via environment or metadata-only mechanisms [MVP]

#### Implementation Plan & Notes

- Service account + IAM:
  - Create `metabase-bq-reader@${PROJECT_ID}.iam.gserviceaccount.com` with `roles/bigquery.dataViewer` on dataset `ai_usage_analytics` and `roles/secretmanager.secretAccessor` limited to new secrets that hold Metabase connection values.
  - Store its email + optional impersonation notes in `/docs/operations/coordination-plan.md` once provisioned.
  - Run all provisioning/role-assignments via `deployer-sa@ai-workflows-459123.iam.gserviceaccount.com` impersonation (`gcloud ... --impersonate-service-account=deployer-sa@...`); see `docs/operations/service-accounts.md`.
  - Cross-check the machine-readable catalog (`docs/operations/environment-catalog.yaml`) for canonical service-account names, dataset IDs, and secret names before executing.
- Secret Manager wiring (mirrors `startup.sh` contract):
  - Introduce secrets `metabase-bigquery-project`, `metabase-bigquery-dataset`, and `metabase-bigquery-key` (JSON key optional; MVP uses OAuth via service account impersonation).
  - Update `startup.sh` to read optional metadata overrides `metabase-bq-project`, `metabase-bq-dataset`, `metabase-bq-credentials-secret`; render values into `/opt/metabase/metabase.env` as `MB_BIGQUERY_PROJECT_ID`, `MB_BIGQUERY_DATASET`, `MB_BIGQUERY_SERVICE_ACCOUNT`.
  - Document secret naming and rotation expectations in `docs/operations/runbook.md` (Section 9 credential management).
- Automation helper: `scripts/metabase/setup_bigquery_connection.sh` encapsulates the SA creation, dataset IAM binding, secret population, and metadata updates using deployer-sa impersonation.
- Metabase configuration workflow:
  1. SSH → run `docker exec -it metabase /bin/bash` → `export MB_DB_*` etc as needed, then apply environment variables via `metabase.env`.
  2. Within Metabase Admin → Databases → **Add database** → BigQuery → select `Service Account JSON` (if using key) or configure via OAuth impersonation (preferred). For MVP, supply connection using env variables set by `startup.sh`.
  3. Use `Allow large results` disabled; set `processing_location=US` to match dataset region.
  4. Disable **Automatic Question Sync** until dashboards verified to avoid noisy load (optional).
- Validation checklist (capture evidence for QA):
  - Screenshot of Database connection test showing row counts for all eight tables.
  - Saved SQL snippet per table & view stored in `sql/validation/metabase-connection.sql`.
  - Record execution timings for representative aggregations (`avg`/`sum`) ensuring <2s at Q4 data volume; store in story Debug Log.
- Post-MVP (tracked separately):
  - Explore Workload Identity Federation to remove the remaining JSON key dependency; requires configuring `gcloud auth login` from VM using `gcloud beta iam workload-identity-pools`.
  - Add automated connection health check (Metabase API `/api/database/:id/schema`) monitored via Cloud Monitoring.

## Story 4.3: Build AI Cost Dashboard
Archon Task ID: b0e1e287-f6b9-4a7f-a31c-4672a90a4968

As a finance team member,
I want the AI Cost Dashboard with all 8 visualizations and SQL queries,
so that I can track total spending, user costs, and budget variance.

**Acceptance Criteria:**
1. Dashboard created in Metabase with name "AI Cost Dashboard - Q4 2025" following exact layout from `/docs/dashboard-design-spec.md`
2. Top banner 4 KPI cards created: Q4 Total, Daily Average, Cost/User, vs Budget with QoQ comparison calculations
3. Daily spend trend line chart with budget reference line sourced from configuration (e.g., daily budget) showing all three cost sources (Claude, Claude Code, Cursor)
4. Tool breakdown pie chart showing Claude Desktop, Claude Code, and Cursor cost distribution
5. Top 15 spenders horizontal bar chart with configurable alert threshold reference line
6. User distribution histogram, cost by model stacked bar, cost by token type stacked bar all implemented per spec
7. Team attribution table with drill-down to user details
8. Three alert cards (Budget Alerts, Efficiency Alerts, Utilization Alerts) with conditional color coding (red/yellow/green)
9. Global date range filter functional (default Q4 2025)
10. Export to PDF and XLSX tested and working

#### Implementation Plan & Notes

- Primary references: `/docs/dashboard-design-spec.md`, `sql/views/vw_combined_daily_costs.sql`, and base tables `claude_cost_report`, `cursor_spending`, `claude_usage_report`.
- Prerequisites:
  - Ensure cost/usage pipelines (Epics 2 & 3) have populated prior 90 days of data.
  - Verify configuration parameters (daily budget thresholds) stored in project config or Metabase dashboard parameters.
- Build workflow:
  1. Create dashboard skeleton following spec layout: KPI row, trend section, breakdowns, alert cards.
  2. Use Metabase saved questions for reusable metrics (budget variance, top spenders). Store questions inside `Finance` collection.
  3. Configure alert cards via custom SQL expressions (red/yellow/green thresholds) and document threshold values in dashboard description.
  4. Validate exports (PDF/XLSX) and attach artifacts under `docs/operations/artifacts/`.
- Performance:
  - Rely on view `vw_combined_daily_costs` to avoid heavy aggregation at dashboard runtime.
  - Record query execution times (<2s) as part of Story 4.7 validation.
- Evidence for completion: screenshot of final dashboard, exported files, links to question IDs.

## Story 4.4: Build AI Engineering Productivity Dashboard
Archon Task ID: 5b240674-53de-4add-bb9b-0a7017d1155b

As an engineering manager,
I want the Engineering Productivity Dashboard with developer metrics,
so that I can track team productivity, acceptance rates, and tool effectiveness.

**Acceptance Criteria:**
1. Dashboard created in Metabase following exact layout from `/docs/engineering-dashboard-spec.md` with name "AI Engineering Productivity Dashboard - Q4 2025"
2. Top banner 4 KPI cards: Active Devs, LOC Accepted, Acceptance %, Commits with QoQ comparisons
3. Dual-axis line chart showing total LOC suggested, accepted LOC (left axis), and acceptance rate percentage (right axis)
4. Acceptance rate gauge with target zones (red <35%, yellow 35-45%, green >45%)
5. Developer distribution histogram and IDE comparison box plot implemented
6. Feature usage stacked bar showing Edit Tools, Tabs, Cmd+K, Chat, Composer, Agent usage by week
7. Suggestion quality trend line, tab completion rate bar chart, and model mix card implemented
8. Developer ranking table (sortable) with all developers, LOC metrics, acceptance rates, sessions, and primary IDE
9. Activity heatmap showing developer activity by week and day of week
10. Drill-down from developer name in table to daily detail modal working

#### Implementation Plan & Notes

- References: `/docs/engineering-dashboard-spec.md`, `sql/views/vw_engineering_productivity.sql`, `sql/tables/cursor_usage_stats.sql`, `sql/tables/claude_code_usage_stats.sql`.
- Preparation:
  - Confirm `vw_engineering_productivity` exposes acceptance %, suggestion quality, IDE usage; update view if fields missing.
  - Ensure Cursor and Claude Code ingestion jobs populate the required metrics (Story 2.x / 3.x).
- Dashboard build steps:
  1. Construct KPI cards for Active Devs, LOC Accepted, Acceptance %, Commits using view aggregates.
  2. Dual-axis trend: create SQL question returning LOC totals and acceptance rate; configure chart with left/right axes.
  3. Implement drill-down by linking ranking table rows to detailed modal questions filtered by developer (Metabase click behavior).
  4. Generate activity heatmap via pre-aggregated query (consider staging table for performance).
- Validation:
  - Cross-check metrics against manual BigQuery queries; store SQL in `sql/validation/engineering-dashboard.sql` when created.
  - Capture screenshots of KPI row, dual-axis chart, and drill-down modal.
- Evidence: saved question IDs, dashboard export (PDF), documented load timings (<3s).

## Story 4.5: Build Claude Desktop Usage Dashboard
Archon Task ID: 40a81310-36ec-4129-b05e-14417395d7ec

As a product manager,
I want the Claude Desktop Usage Dashboard showing adoption and engagement metrics,
so that I can track claude.ai usage patterns and feature adoption.

**Acceptance Criteria:**
1. Dashboard created in Metabase following `/docs/claude-desktop-dashboard-spec.md` with name "Claude Desktop Usage Dashboard - Q4 2025"
2. Top banner 4 KPI cards: Active Users, Conversations, Files Used, Projects with QoQ comparisons
3. Daily active users line chart with 7-day moving average showing adoption trend
4. Platform distribution donut chart (Desktop App, Web, iOS, Android) with percentages
5. Conversations per user histogram and average conversations trend bar chart
6. Event type distribution stacked bar and file upload trend line chart implemented
7. Project usage visualizations: projects per user bar, project stats card, top 10 projects bar chart
8. User activity table (top 30 users) showing weekly convos, files, projects, platform, last active date
9. Hourly usage heatmap (day of week × hour UTC) showing peak usage patterns
10. Alert cards for inactive users and power users with counts and actions

#### Implementation Plan & Notes

- References: `/docs/claude-desktop-dashboard-spec.md`, `sql/views/vw_claude_ai_daily_summary.sql`, raw table `claude_ai_usage_stats`.
- Pre-work:
  - Validate Claude ingestion (Story 3.x) populates platform, project, and file usage fields; coordinate with data team if transformations required.
  - Confirm moving-average calculations available in view or compute within SQL questions.
- Build workflow:
  1. KPI row using aggregated view; include QoQ trendnotes in descriptions.
  2. DAU line chart (with 7-day moving average) and platform distribution donut built via SQL questions stored under Product collection.
  3. Conversations per user histogram plus alert cards (Power vs Inactive) using CASE logic.
  4. Hourly heatmap: if necessary create staging table for performance (`sql/views/vw_claude_hourly_heatmap.sql`).
- Validation:
  - Exports (PDF/XLSX) captured and saved.
  - Table of top users cross-checked against BigQuery query for audit.
  - Document alert thresholds (inactive >7 days, power users >95th percentile) in dashboard description.
- Evidence: dashboard screenshots, question IDs, validation SQL stored for QA.

## Story 4.6: Configure Dashboard Collections and Access
Archon Task ID: ed66390b-5d91-4315-9f15-6d477a79291c

As a Metabase admin,
I want dashboards organized in collections with appropriate access controls,
so that users see relevant dashboards for their role.

**Acceptance Criteria:**
1. Metabase collections created: "Finance" (Cost dashboard), "Engineering" (Productivity dashboard), "Product" (Claude Desktop dashboard)
2. User groups created in Metabase: Finance Team, Engineering Managers, Product Team, Executives
3. Permissions configured: Finance group can access Finance collection, Engineering group can access Engineering collection, Executives can access all
4. Dashboard links shared with stakeholder groups via email or Slack
5. Test access with different user accounts confirms proper permissions (users only see their authorized dashboards)
6. Dashboard homepage configured showing role-appropriate default view
7. SSO (Google/OIDC/SAML) enabled for Metabase; local user signups disabled; MFA enforced via IdP [MVP]
8. [Post-MVP] Quarterly access review documented; group-to-collection permissions verified and approved

#### Implementation Plan & Notes

- Identity references: `docs/operations/service-accounts.md`, `docs/operations/environment-catalog.yaml`, internal IdP configuration guides.
- Steps:
  1. Create Metabase groups (`Finance`, `Engineering Managers`, `Product`, `Executives`) and map to collections.
  2. Collections created after dashboards exist; configure permissions (view vs curate) per group.
  3. Enable SSO (Google/OIDC/SAML) via Metabase Admin → Authentication; coordinate with security for client IDs/secrets.
  4. Disable local signups and enforce MFA at IdP level; document procedure in runbook.
  5. Configure homepage per role and create `docs/operations/access-review-template.md` for quarterly audits.
  6. Invite representative users and confirm least-privilege access.
- Evidence:
  - Screenshot of permissions matrix.
  - Link to SSO configuration record (secure storage).
  - Completed access review checklist stored under `/docs/operations/artifacts/`.

## Story 4.7: Test Dashboard Performance and Export
Archon Task ID: ae6fcd33-6b2b-4060-ba3c-d1230cbbc394

As a dashboard user,
I want dashboards to load quickly and support all export formats,
so that I can efficiently analyze data and share reports.

**Acceptance Criteria:**
1. All three dashboards meet performance SLO: p95 load time < 5 seconds with full data (Q4 date range) [MVP]
2. Individual charts refresh meet p95 < 3 seconds when filters change [MVP]
3. [Post-MVP] Track p50 and alert on SLO violations
3. PDF export generates single-page dashboard layout for all three dashboards
4. CSV export from tables downloads complete data with proper column headers
5. XLSX export preserves formatting and includes all visualizations
6. PNG screenshot export captures full dashboard at 1920×1080 resolution
7. Scheduled email reports configured to send Cost Dashboard PDF to finance team first Monday of each month

#### Implementation Plan & Notes

- Performance validation:
  - Use browser dev tools or Metabase audit logs to capture dashboard load times (record p95 for initial load and filter changes).
  - Execute validation script outlined in `docs/operations/metabase-bigquery-validation.md` plus dashboard-specific checks.
  - Document timings in `docs/operations/artifacts/metabase-dashboard-performance-<date>.md`.
- Export verification:
  - Produce PDF, XLSX, PNG, and CSV for each dashboard; store under `/docs/operations/artifacts/`.
  - Validate formatting (legends, tables, conditional colors) and note any manual fixes required.
- Scheduled reports:
  - Configure Metabase subscription (Finance collection) sending Cost Dashboard PDF monthly; capture screenshot of schedule settings.
  - Confirm email delivery via finance distribution list (log in completion notes).
- Post-MVP tracking:
  - Outline plan to monitor p50 and SLO breaches (Metabase API + Cloud Monitoring).
  - Define re-test cadence (monthly or post-release) and surface results in Story 4.7 QA record.
- Evidence:
  - Performance log, export files, subscription screenshot.
  - Entry in Story 4.7 Dev Agent Record summarizing metrics and artifacts.

---
