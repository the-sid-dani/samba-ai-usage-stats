# Epic List

## Epic 1: Foundation & Data Infrastructure
**Goal:** Establish BigQuery data warehouse and manual upload workflows
**Deliverables:**
- Create 6 BigQuery tables with proper schema
- Set up Google Sheets → BigQuery sync for claude.ai usage
- Create API key mapping table and management process
- Implement basic data validation checks

**Success Criteria:** Can manually upload claude.ai data and query in BigQuery

## Epic 2: Cursor Integration
**Goal:** Automate Cursor data collection for usage and costs
**Deliverables:**
- Implement Cursor API client using documented specs
- Build ETL pipeline: Cursor API → BigQuery (usage + expenses)
- Add error handling and retry logic
- Validate data accuracy against Cursor dashboard

**Success Criteria:** Daily automated Cursor data flowing to BigQuery with 99% accuracy

## Epic 3: Claude Platform Integration
**Goal:** Automate Claude ecosystem data collection (Code + expenses + API)
**Deliverables:**
- Implement Claude Admin API client for `/claude_code` endpoint
- Build cost report parser for claude_expenses (all platforms)
- Filter API usage costs into api_usage_expenses
- Implement platform segmentation logic

**Success Criteria:** All Claude data sources automated with correct platform attribution

## Epic 4: Metabase Dashboard Suite
**Goal:** Deploy self-hosted Metabase with 4 core dashboards
**Deliverables:**
- Provision GCP VM and deploy Metabase via Docker
- Connect to BigQuery with service account
- Build 4 dashboards: Executive, Cost Allocation, Productivity, ROI
- Configure export capabilities and user access

**Success Criteria:** Finance team can independently access dashboards and export data

## Epic 5: Production Hardening
**Goal:** Ensure system reliability and operational readiness
**Deliverables:**
- Implement Cloud Scheduler for daily automation
- Add comprehensive monitoring and alerting
- Create runbook for common operations
- Implement automated backup for Metabase VM
- Document user guides and admin procedures

**Success Criteria:** System runs autonomously for 30 days with >99% uptime

---
