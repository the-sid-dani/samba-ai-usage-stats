# Source Tree Structure

**Project:** AI Usage Analytics Dashboard
**Last Updated:** October 19, 2025
**Architecture Version:** 2.1

---

## Complete Directory Structure

```plaintext
samba-ai-usage-stats/
├── .github/                              # GitHub configuration
│   └── workflows/                        # CI/CD pipelines (future)
│       ├── ci.yaml
│       └── deploy.yaml
│
├── docs/                                 # Project documentation
│   ├── api-reference/                    # API documentation
│   │   ├── claude-admin-api.md
│   │   ├── cursor-api-specs.md
│   │   ├── DATA_SUMMARY.md
│   │   ├── metabase-architecture.md
│   │   ├── PLATFORM_SEGMENTATION_STRATEGY.md
│   │   └── VERIFIED_API_DATA.md
│   ├── architecture/                     # Architecture shards
│   │   ├── coding-standards.md
│   │   ├── components.md
│   │   ├── core-workflows.md
│   │   ├── data-models.md
│   │   ├── database-schema.md
│   │   ├── deployment-architecture.md
│   │   ├── development-workflow.md
│   │   ├── error-handling-strategy.md
│   │   ├── external-api-integrations.md
│   │   ├── high-level-architecture.md
│   │   ├── index.md
│   │   ├── introduction.md
│   │   ├── monitoring-and-observability.md
│   │   ├── next-steps.md
│   │   ├── security-and-performance.md
│   │   ├── source-tree.md               # This file
│   │   ├── tech-stack.md
│   │   ├── testing-strategy.md
│   │   └── unified-project-structure.md
│   ├── operations/                       # Operational documentation
│   │   ├── api-key-management.md
│   │   ├── backup-recovery.md
│   │   ├── environment-catalog.yaml
│   │   ├── incident_response.md
│   │   ├── metabase-bigquery-validation.md
│   │   ├── metabase-gce-provisioning.md
│   │   ├── runbook.md
│   │   ├── service-accounts.md
│   │   ├── troubleshooting.md
│   │   └── user-guide.md
│   ├── prd/                              # Product requirements shards
│   │   ├── CLAUDE_API_FINDINGS.md
│   │   ├── data-architecture.md
│   │   ├── epic-list.md
│   │   ├── goals-and-background-context.md
│   │   ├── index.md
│   │   ├── next-steps.md
│   │   ├── requirements.md
│   │   ├── technical-assumptions.md
│   │   ├── technical-implementation-approach.md
│   │   └── user-interface-design-goals.md
│   ├── runbooks/                         # Operational runbooks
│   │   ├── metabase-dashboard-automation-quickstart.md
│   │   ├── metabase-dashboard-automation.md
│   │   ├── metabase-vm-from-scratch.md
│   │   └── metabase-vm-sql-transfer.md
│   ├── stories/                          # User stories
│   │   ├── 2.1.fix-cursor-api-client.md
│   │   ├── 2.2.fix-anthropic-api-client.md
│   │   ├── 2.3.create-pipeline-orchestrator.md
│   │   ├── 2.7.backfill-cursor-spending-historical-data.md
│   │   ├── 4.*.md                        # Production stories
│   │   ├── 5.*.md                        # Infrastructure stories
│   │   ├── 6.*.md                        # Metabase stories
│   │   ├── CURSOR_INGESTION_SPEC.md
│   │   └── CURSOR_REDESIGN.md
│   ├── architecture.md                   # Main architecture document
│   ├── BIGQUERY_SCHEMA_WITH_REAL_DATA.md
│   ├── brief.md
│   ├── CLAUDE_FINAL_VALIDATED_DESIGN.md
│   ├── CLAUDE_INGESTION_IMPLEMENTATION_SUMMARY.md
│   ├── CURSOR_COST_ARCHITECTURE.md
│   ├── CURSOR_UNIFIED_DESIGN.md
│   ├── deployment-guide.md
│   ├── google-sheets-setup.md
│   ├── metabase-transition-brief.md
│   └── prd.md
│
├── infrastructure/                       # Infrastructure as Code
│   ├── cloud_run/                        # Cloud Run deployment
│   │   ├── deploy-claude-ingestion.sh
│   │   ├── deploy-cursor-ingestion.sh
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── service.yaml
│   │   ├── setup-iam.sh
│   │   └── setup-scheduler.sh
│   ├── metabase/                         # Metabase VM deployment
│   │   ├── backup-metabase.sh
│   │   ├── docker-compose.yml
│   │   ├── metabase.env.example
│   │   ├── README.md
│   │   └── startup.sh
│   ├── terraform/                        # Terraform IaC
│   │   └── main.tf
│   └── README.md
│
├── production-data/                      # Production data samples
│   ├── claude_code_team_2025_10_01_to_2025_10_31.csv
│   ├── claude_code_team_2025_10_01_to_2025_11_01.csv
│   └── claude-logs.csv
│
├── PRPs/                                 # Planning documents
│   ├── cc-prp-initials/                  # Initial plans
│   │   ├── initial-claude-ingestion-rebuild.md
│   │   └── initial-metabase-chart-automation.md
│   └── cc-prp-plans/                     # Detailed PRPs
│       ├── prp-claude-ingestion-rebuild.md
│       └── prp-metabase-chart-automation.md
│
├── scripts/                              # Utility scripts
│   ├── api_investigation/                # API exploration scripts
│   │   ├── responses/                    # API response samples
│   │   ├── save_complete_responses.py
│   │   ├── test_claude_admin_api.py
│   │   ├── test_cost_report_grouped.py
│   │   ├── test_cursor_admin_api.py
│   │   ├── test_detailed_claude_api.py
│   │   └── test_group_by_array.py
│   ├── ingestion/                        # Data ingestion scripts
│   │   ├── backfill_claude_data.py
│   │   ├── cursor_client.py
│   │   ├── ingest_claude_app_usage_logs.py
│   │   ├── ingest_claude_data.py
│   │   ├── ingest_cursor_daily.py
│   │   ├── retry_failed_claude_dates.py
│   │   └── retry_failed_dates.py
│   ├── metabase/                         # Metabase automation
│   │   ├── create_dashboards.py          # Dashboard creation (to be enhanced)
│   │   ├── create_single_card.py
│   │   ├── run_dashboard_creation.sh
│   │   └── setup_bigquery_connection.sh
│   └── validation/                       # Data validation
│       ├── CLAUDE_COST_DUPLICATION_FINDINGS.md
│       ├── CLAUDE_ROOT_CAUSE_ANALYSIS.md
│       ├── data_validation_queries_CORRECTED.sql
│       ├── data_validation_queries.sql
│       ├── run_data_validation.py
│       └── run_validation.py
│
├── sql/                                  # SQL definitions
│   ├── bigquery/                         # BigQuery schema
│   │   └── tables/                       # Table creation scripts
│   ├── dashboard/                        # Dashboard queries
│   │   ├── ai_cost/                      # AI cost dashboard queries (14 files)
│   │   │   ├── 01_kpi_total_cost.sql
│   │   │   ├── 02_kpi_daily_average.sql
│   │   │   ├── 03_kpi_cost_per_user.sql
│   │   │   ├── 04_kpi_budget_variance.sql
│   │   │   ├── 05_daily_spend_trend.sql
│   │   │   ├── 06_tool_breakdown.sql
│   │   │   ├── 07_top15_spenders.sql
│   │   │   ├── 08_user_distribution_histogram.sql
│   │   │   ├── 09_cost_by_model.sql
│   │   │   ├── 10_cost_by_token_type.sql
│   │   │   ├── 11_team_attribution_table.sql
│   │   │   ├── 12_alert_budget.sql
│   │   │   ├── 13_alert_efficiency.sql
│   │   │   └── 14_alert_utilization.sql
│   │   └── claude_app_usage_metrics.sql
│   └── schemas/                          # Schema definitions
│       ├── create_claude_code_productivity.sql
│       ├── create_claude_costs.sql
│       └── create_claude_usage_keys.sql
│
├── src/                                  # Application source code
│   └── ingestion/                        # Ingestion service
│       ├── cursor_client.py
│       ├── Dockerfile
│       ├── ingest_cursor_daily.py
│       ├── requirements-cursor.txt
│       └── test_cursor_spend_delta.py
│
├── templates/                            # Configuration templates
│   └── api_key_mapping_template.csv
│
├── tests/                                # Test suite
│   └── test_claude_ingestion/           # Claude ingestion tests
│
├── venv/                                 # Python virtual environment
│
├── .env                                  # Environment variables (not committed)
├── .gitignore                            # Git ignore rules
├── AGENTS.md                             # Agent definitions
├── CLAUDE_INGESTION_README.md            # Claude ingestion documentation
├── CLAUDE.md                             # Project instructions
├── cloudbuild.yaml                       # Cloud Build configuration
├── Dockerfile                            # Main Dockerfile
├── Dockerfile.claude-ingestion           # Claude ingestion Dockerfile
├── Dockerfile.cursor-ingestion           # Cursor ingestion Dockerfile
├── FINAL_VALIDATION_CHECKLIST.md        # Validation checklist
├── HANDOFF_SUMMARY.md                    # Handoff documentation
├── IMPLEMENTATION_COMPLETE.md            # Implementation summary
├── package.json                          # Node.js metadata (minimal)
├── README.md                             # Project README
├── requirements.txt                      # Python dependencies
├── requirements-claude-ingestion.txt     # Claude-specific dependencies
├── SERVICE_ACCOUNTS_REFERENCE.md         # Service account documentation
├── TASK_REVIEW_PRIORITY_ANALYSIS.md      # Task analysis
├── UNBLOCK_CURSOR_DEPLOYMENT.md          # Cursor deployment notes
└── UNIFIED_TABLE_DESIGN.md               # Table design documentation
```

---

## Key Directories Explained

### `/docs` - Documentation Hub
**Purpose:** All project documentation organized by type

**Sub-directories:**
- `api-reference/` - API documentation and specifications
- `architecture/` - Architecture document shards (this directory)
- `operations/` - Operational procedures and runbooks
- `prd/` - Product requirements shards
- `runbooks/` - Step-by-step operational procedures
- `stories/` - User stories and implementation specs

**Root-level docs:**
- `architecture.md` - Main architecture document (source)
- `prd.md` - Main PRD document (source)
- `BIGQUERY_SCHEMA_WITH_REAL_DATA.md` - Schema with real data samples
- `CLAUDE_FINAL_VALIDATED_DESIGN.md` - Validated Claude design
- `CURSOR_UNIFIED_DESIGN.md` - Cursor data design

### `/infrastructure` - Infrastructure as Code
**Purpose:** All deployment and infrastructure configuration

**Sub-directories:**
- `cloud_run/` - Cloud Run service and job definitions
- `metabase/` - Metabase VM deployment (Docker Compose)
- `terraform/` - Terraform IaC for GCP resources

**Key Files:**
- `cloud_run/deploy-*.sh` - Deployment automation scripts
- `metabase/docker-compose.yml` - Metabase + PostgreSQL stack
- `terraform/main.tf` - Infrastructure provisioning

### `/scripts` - Utility Scripts
**Purpose:** Operational scripts for data pipeline and dashboard management

**Sub-directories:**
- `api_investigation/` - API exploration and testing scripts
- `ingestion/` - Data ingestion scripts (Claude, Cursor)
- `metabase/` - Dashboard automation scripts
- `validation/` - Data quality validation scripts

**Critical Scripts:**
- `ingestion/ingest_claude_data.py` - Claude API ingestion
- `ingestion/ingest_cursor_daily.py` - Cursor API ingestion
- `metabase/create_dashboards.py` - Dashboard automation (to be enhanced)
- `validation/run_validation.py` - Data quality checks

### `/sql` - SQL Definitions
**Purpose:** All BigQuery SQL (schemas, views, dashboard queries)

**Sub-directories:**
- `bigquery/tables/` - Table creation DDL
- `dashboard/ai_cost/` - Dashboard query library (14 files)
- `schemas/` - Schema definition scripts

**Dashboard Queries:**
- `01-04_kpi_*.sql` - KPI cards (scalar charts)
- `05_daily_spend_trend.sql` - Trend analysis (line chart)
- `06_tool_breakdown.sql` - Provider breakdown (pie chart)
- `07_top15_spenders.sql` - User rankings (bar chart)
- `08-10_*.sql` - Additional analytics
- `11-14_alert_*.sql` - Alert tables

### `/src` - Application Source
**Purpose:** Python application code for Cloud Run services

**Structure:**
- `ingestion/` - Cursor ingestion service (containerized)
  - `Dockerfile` - Container definition
  - `ingest_cursor_daily.py` - Main ingestion logic
  - `cursor_client.py` - API client
  - `requirements-cursor.txt` - Dependencies

**Future Structure (Planned):**
```
src/
├── ingestion/          # API client modules
├── processing/         # Data transformation
├── storage/            # BigQuery operations
├── shared/             # Common utilities
└── orchestration/      # Pipeline coordination
```

### `/PRPs` - Planning Documents
**Purpose:** Initial plans and detailed PRPs for features

**Sub-directories:**
- `cc-prp-initials/` - Initial planning documents
- `cc-prp-plans/` - Detailed implementation PRPs

**Current Plans:**
- `initial-claude-ingestion-rebuild.md` - Claude pipeline redesign
- `prp-claude-ingestion-rebuild.md` - Claude pipeline implementation
- `initial-metabase-chart-automation.md` - Dashboard automation planning
- `prp-metabase-chart-automation.md` - Dashboard automation implementation

### `/tests` - Test Suite
**Purpose:** Automated testing (unit, integration, validation)

**Structure:**
- `test_claude_ingestion/` - Claude pipeline tests
- Future: `metabase/` - Metabase automation tests
- Future: `integration/` - End-to-end tests

---

## File Naming Conventions

### Python Scripts
- **Pattern:** `{action}_{entity}_{modifier}.py`
- **Examples:**
  - `ingest_claude_data.py` - Ingest Claude data
  - `create_dashboards.py` - Create dashboards
  - `run_validation.py` - Run validation

### SQL Files
- **Pattern:** `{sequence}_{purpose}_{details}.sql`
- **Examples:**
  - `01_kpi_total_cost.sql` - Numbered for ordering
  - `05_daily_spend_trend.sql` - Clear purpose
  - `create_claude_costs.sql` - Schema creation

### Documentation
- **Pattern:** `{topic}-{subtopic}.md` (kebab-case)
- **Examples:**
  - `metabase-dashboard-automation.md`
  - `high-level-architecture.md`
  - `tech-stack.md`

### Configuration Files
- **Pattern:** `{service}.{environment}.{ext}`
- **Examples:**
  - `metabase.env.example` - Example config
  - `docker-compose.yml` - Service definition
  - `cloudbuild.yaml` - Build configuration

---

## Critical File Locations

### Configuration Files (Environment-Specific)
```
/.env                          # Main environment variables (not committed)
/infrastructure/metabase/.env  # Metabase configuration (not committed)
/.env.example                  # Template for environment setup
```

### Entry Points
```
/src/ingestion/ingest_cursor_daily.py    # Cursor daily ingestion
/scripts/ingestion/ingest_claude_data.py # Claude daily ingestion
/scripts/metabase/create_dashboards.py   # Dashboard automation
```

### Schema Definitions
```
/sql/schemas/create_claude_costs.sql             # Claude cost table
/sql/schemas/create_claude_code_productivity.sql # Claude Code productivity
/sql/schemas/create_claude_usage_keys.sql        # Claude usage by key
/sql/bigquery/tables/                            # All table DDL
```

### Deployment Configurations
```
/Dockerfile                                # Main container
/Dockerfile.claude-ingestion              # Claude ingestion container
/Dockerfile.cursor-ingestion              # Cursor ingestion container
/infrastructure/cloud_run/service.yaml    # Cloud Run service config
/infrastructure/metabase/docker-compose.yml # Metabase stack
```

---

## Git Ignore Patterns

**Not Committed:**
- `.env` - Environment variables with secrets
- `.env.*` - Any environment-specific configs
- `__pycache__/` - Python bytecode cache
- `*.pyc` - Compiled Python files
- `venv/` - Virtual environment
- `node_modules/` - Node dependencies
- `.DS_Store` - macOS metadata
- `*.log` - Log files
- `dashboards.json` - Generated dashboard manifests
- `/opt/` - VM-specific directories

**Committed:**
- `.env.example` - Template for environment setup
- `*.env.example` - Example configurations
- `requirements*.txt` - Python dependencies
- All source code, docs, SQL, infrastructure configs

---

## New Files from Metabase Automation Feature

**When Metabase Chart Automation is Implemented:**

```
scripts/metabase/
├── create_dashboards.py          # ✏️ ENHANCED (existing)
├── create_single_card.py          # (existing, unchanged)
├── chart_templates.py             # ✨ NEW - Chart visualization templates
├── filter_templates.py            # ✨ NEW - Filter configuration templates
├── config_loader.py               # ✨ NEW - Configuration loader/validator
├── validate_config.py             # ✨ NEW - Config validation script
├── chart_config.json              # ✨ NEW - Chart type mappings
└── filter_config.json             # ✨ NEW - Filter presets

examples/chart_configs/            # ✨ NEW DIRECTORY
├── example_line_chart.json
├── example_pie_chart.json
├── example_multi_chart.json
└── example_with_filters.json

docs/
├── claude-dashboard-guide.md      # ✨ NEW - Claude usage guide
└── runbooks/
    └── metabase-dashboard-automation.md  # ✏️ UPDATED

tests/metabase/                    # ✨ NEW DIRECTORY
├── test_chart_templates.py
├── test_filter_templates.py
├── test_config_loader.py
└── test_create_dashboards.py
```

---

## Dependency Files

### Python Dependencies

**Main Dependencies (`requirements.txt`):**
- `requests` - HTTP client for API calls
- `google-cloud-bigquery` - BigQuery client
- `google-cloud-secret-manager` - Secret management
- `google-cloud-logging` - Structured logging
- `python-dotenv` - Environment variable loading
- `pandas` - Data manipulation
- `pytest` - Testing framework

**Claude Ingestion (`requirements-claude-ingestion.txt`):**
- `requests`
- `google-cloud-bigquery`
- `google-cloud-secret-manager`
- `python-dotenv`

**Cursor Ingestion (`src/ingestion/requirements-cursor.txt`):**
- `requests`
- `google-cloud-bigquery`
- `python-dotenv`

**Future Metabase Automation Dependencies:**
- `jsonschema>=4.20.0` - JSON configuration validation
- `pydantic>=2.5.0` - Data validation

### Node.js (Minimal)
**package.json:**
- Minimal Node.js metadata
- No actual Node.js application (Python-based project)

---

## Environment-Specific Structures

### Development Environment
```
Local Machine
├── Clone repository
├── Create venv
├── Install dependencies
├── Configure .env with dev credentials
├── Run scripts locally
└── Connect to dev BigQuery dataset
```

### Production Environment (GCP)
```
GCP Project: ai-workflows-459123
├── Cloud Run Jobs
│   ├── claude-ingestion (containerized)
│   └── cursor-ingestion (containerized)
├── Cloud Scheduler
│   └── Daily 6 AM PT trigger
├── BigQuery Dataset: ai_usage_analytics
│   ├── Raw tables (partitioned by date)
│   ├── Curated tables (clustered by key fields)
│   └── Aggregated views (finance KPIs)
├── Compute Engine VM (Metabase)
│   ├── Docker containers (Metabase + PostgreSQL)
│   ├── nginx reverse proxy
│   └── Automated backups
├── Secret Manager
│   ├── anthropic-admin-api-key
│   ├── cursor-api-key
│   └── metabase-admin-password
└── Cloud Logging
    └── Structured JSON logs
```

---

## Build Artifacts (Not in Git)

**Generated During Development:**
- `__pycache__/` - Python bytecode cache
- `*.pyc` - Compiled Python files
- `.pytest_cache/` - Test cache
- `dashboards.json` - Generated dashboard manifests
- `*.log` - Log files

**Generated During Deployment:**
- Docker images in Google Container Registry:
  - `gcr.io/ai-workflows-459123/ai-usage-ingestion`
  - `gcr.io/ai-workflows-459123/cursor-daily-ingest`
- Cloud Run revisions
- BigQuery table partitions
- Metabase database backups

---

## Future Directory Additions

**Planned (from PRPs):**

```
scripts/metabase/
├── chart_templates.py      # Chart visualization settings
├── filter_templates.py     # Filter widget configurations
├── config_loader.py        # Configuration management
└── validate_config.py      # Validation utilities

examples/
└── chart_configs/          # Example dashboard configurations

tests/metabase/             # Metabase automation tests

docs/
└── claude-dashboard-guide.md  # Claude interaction guide
```

---

## Project Growth Pattern

**Historical Growth:**
1. **Phase 1 (Sept 2025):** Initial PRD and architecture
2. **Phase 2 (Oct 2025):** Claude & Cursor ingestion implementation
3. **Phase 3 (Oct 2025):** Metabase integration and dashboard automation planning
4. **Phase 4 (Nov 2025 - Planned):** Chart automation implementation

**Directory Evolution:**
- Started: `/docs`, `/sql`, `/scripts`
- Added: `/infrastructure`, `/PRPs`, `/src`
- Next: `/examples`, `/tests/metabase`

**File Count Growth:**
- Initial: ~20 files
- Current: ~175 files
- Projected: ~200+ files after Metabase automation

---

## Maintenance Notes

### Regular Updates Required

**Weekly:**
- Review and update SQL dashboard queries
- Update chart_config.json for new charts
- Review API client error logs

**Monthly:**
- Update architecture documentation
- Review and archive old planning documents
- Update dependency versions

**Per Feature:**
- Update source-tree.md with new directories/files
- Update PRPs directory with planning docs
- Add tests for new functionality
- Update relevant runbooks

### Documentation Sync

**When Adding Files:**
1. Update this source-tree.md
2. Update docs/architecture/unified-project-structure.md if structure changes
3. Update relevant runbook if operational script added
4. Add entry to README.md if user-facing

**When Removing Files:**
1. Archive in docs/archive/ if contains useful history
2. Update all references in documentation
3. Update source-tree.md
4. Clean up related test files

---

**Generated by Winston (Architect) on October 19, 2025**
