# Requirements

## Functional Requirements

**FR1: Claude.ai Usage Data Collection**
The system shall provide a Google Sheets template for manual upload of claude.ai chat usage logs with automated BigQuery sync to `claude_usage_stats` table.

**FR2: Claude Code Usage Data Collection**
The system shall automatically fetch Claude Code IDE usage metrics from Claude Admin API `/claude_code` endpoint and store in `claude_code_usage_stats` table with daily refresh.

**FR3: Cursor Usage Data Collection**
The system shall automatically fetch Cursor IDE productivity metrics from Cursor Admin API `/teams/daily-usage-data` endpoint and store in `cursor_usage_stats` table with daily refresh.

**FR4: Claude Cost Data Collection**
The system shall fetch combined Claude expenses (claude.ai + Claude Code + API) from Claude Admin API Cost Report endpoint and store in `claude_expenses` table with platform field for segmentation.

**FR5: Cursor Cost Data Collection**
The system shall fetch Cursor subscription and overage costs from Cursor Admin API and store in `cursor_expenses` table with cost type breakdown (subscription vs usage-based).

**FR6: API Usage Cost Tracking**
The system shall filter Claude API programmatic usage costs from Claude Admin API Cost Report and store in `api_usage_expenses` table separate from platform costs.

**FR7: BigQuery Data Warehouse**
The system shall maintain 6 BigQuery tables with partitioning, 2+ years retention, and proper schema design supporting analytics queries.

**FR8: Metabase Dashboard Suite**
The system shall provide 4 core dashboards through self-hosted Metabase: Executive Summary, Cost Allocation, Productivity Analytics, and Platform ROI Analysis.

**FR9: Automated Data Pipeline**
The system shall run daily automated data ingestion at 6 AM PT for API-based sources (Claude Code, Cursor, expenses) with retry logic and error handling.

**FR10: Data Quality Validation**
The system shall implement validation checks ensuring data completeness, schema compliance, and cost reconciliation against vendor invoices.

**FR11: Export Capabilities**
The system shall support dashboard data export in CSV, XLSX, JSON, and PNG formats through Metabase native functionality.

**FR12: Alert System**
The system shall send email alerts when monthly costs increase >20% or when data ingestion failures occur.

## Non-Functional Requirements

**NFR1: Reliability**
The system shall maintain 99.5% uptime for automated data ingestion with exponential backoff retry mechanisms.

**NFR2: Performance**
Dashboard queries shall complete within 5 seconds using BigQuery optimizations and Metabase caching.

**NFR3: Security**
All API keys shall be stored in Google Secret Manager with audit logging enabled and quarterly rotation procedures.

**NFR4: Scalability**
The system shall support 100+ users and 50+ API keys without architectural changes.

**NFR5: Data Privacy**
All data shall remain within Google Cloud Platform US region with encryption at rest and in transit.

**NFR6: Deployment**
Metabase shall deploy on GCP Compute Engine e2-medium VM (~$25/month) with automated backup and recovery.

**NFR7: Maintainability**
All infrastructure shall be defined as code (Terraform) with comprehensive documentation for operational handoff.

---
