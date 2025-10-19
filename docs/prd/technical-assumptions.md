# Technical Assumptions

## Infrastructure

**Google Cloud Platform:**
- **Project:** `ai-workflows-459123` (existing)
- **BigQuery Dataset:** `ai_usage_analytics` (US region)
- **Compute Engine:** e2-medium VM for Metabase (~$25/month)
- **Secret Manager:** API key storage with quarterly rotation
- **Cloud Scheduler:** Daily trigger at 6 AM PT

**Python Runtime:**
- **Version:** Python 3.11+
- **Key Libraries:** `google-cloud-bigquery`, `requests`, `pandas`
- **Container:** Docker with multi-stage builds

## Data Sources & APIs

**1. Claude Admin API** (documented in `/docs/api-reference/`)
- **Endpoint 1:** `/v1/organizations/usage_report/claude_code` → claude_code_usage_stats
- **Endpoint 2:** `/v1/organizations/cost_report` → claude_expenses, api_usage_expenses
- **Authentication:** Admin API key (x-api-key header)
- **Rate Limits:** Standard Anthropic limits with backoff

**2. Cursor Admin API** (documented in `/docs/api-reference/cursor-api-specs.md`)
- **Endpoint:** `/teams/daily-usage-data` → cursor_usage_stats, cursor_expenses
- **Authentication:** Basic auth (API key as username)
- **Rate Limits:** 90-day max date range per request

**3. Google Sheets**
- **Purpose:** Manual upload for claude.ai usage, API key mapping
- **Sync Method:** BigQuery Sheets connector or manual CSV import
- **Update Frequency:** Weekly/monthly manual updates

## Metabase Architecture

**Reference:** `/docs/api-reference/metabase-architecture.md`

**Deployment:**
- GCP Compute Engine e2-medium VM
- Docker Compose (Metabase + PostgreSQL)
- BigQuery connection via service account
- Automated backup to Cloud Storage

**API Capabilities:**
- Dashboard creation via REST API
- Programmatic widget/card management
- Scheduled reports and email delivery
- Export in multiple formats

## Data Quality & Validation

**Validation Checks:**
- Schema compliance (required fields present)
- Data freshness (last updated < 48 hours)
- Cost reconciliation (API totals match invoices ±5%)
- Duplicate detection (deduplication on date + user)

**Error Handling:**
- Exponential backoff for API retries (3 attempts)
- Circuit breaker pattern for repeated failures
- Structured logging to Cloud Logging
- Email alerts for data staleness >48 hours

## Security & Compliance

**API Key Management:**
- Store in Google Secret Manager (never in code)
- Rotate quarterly with documented procedure
- Least privilege IAM for service accounts
- Audit logging enabled for all access

**Data Encryption:**
- At rest: Google-managed keys
- In transit: TLS 1.2+
- Network: VPC with firewall rules for Metabase VM

---
