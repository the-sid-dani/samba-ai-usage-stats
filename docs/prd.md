# AI Usage Analytics Dashboard Product Requirements Document (PRD)

**Project ID:** samba-ai-usage-stats
**Document Version:** 2.0
**Created:** October 17, 2025
**Author:** John (PM)
**Status:** Draft
**Previous Version:** v1.0 (archived - deprecated Looker/4-platform approach)

---

## Goals and Background Context

### Goals

- **Unified Cost Visibility:** Provide 100% spending visibility across Claude ecosystem (claude.ai, Claude Code, Claude API) and Cursor platform through consolidated BigQuery data warehouse and Metabase dashboards
- **Platform-Specific Analytics:** Enable distinct analysis of chat-based AI usage (claude.ai) vs developer productivity tools (Claude Code, Cursor) with separate usage and cost tracking
- **Cost Optimization:** Identify 15-20% cost savings opportunities within 1 quarter through data-driven insights into usage patterns and platform efficiency
- **Operational Efficiency:** Reduce manual reporting effort by 80% through automated data ingestion from APIs and manual upload workflows
- **ROI Tracking:** Measure AI tool productivity gains with metrics including acceptance rates, lines of code, and cost-per-productivity calculations

### Background Context

Our organization uses multiple AI platforms across different use cases:
- **Claude.ai:** Chat-based knowledge work and research (~$2-3k/month)
- **Claude Code:** IDE-integrated coding assistance (~$2-3k/month)
- **Claude API:** Programmatic API usage for automation (~$1-2k/month)
- **Cursor:** AI-powered IDE for development (~$2-3k/month)

**Total Monthly Spend:** $7-10k across ~15 team members

**Current Pain Points:**
- No unified view of AI spending across platforms
- Manual effort required for cost allocation and reporting
- Inability to compare platform efficiency (cost per productivity)
- No automation for daily data collection and analysis
- Finance team (Jaya) lacks visibility for budget planning

This PRD defines a simplified 3-platform analytics system (removing Gemini from scope) that:
1. Automates data collection from APIs where available
2. Provides manual upload workflow for claude.ai (no programmatic API)
3. Stores all data in BigQuery with 6 focused tables
4. Delivers insights through self-hosted Metabase dashboards

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| September 26, 2025 | 1.0 | Initial PRD with 4 platforms + Looker | John (PM) |
| October 17, 2025 | 2.0 | Simplified to 3 platforms, 6 tables, Metabase focus, manual claude.ai upload | John (PM) |

---

## Requirements

### Functional Requirements

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

### Non-Functional Requirements

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

## Data Architecture

### BigQuery Tables (6 Tables)

#### 1. `claude_usage_stats`
**Purpose:** Claude.ai chat/web interface usage
**Data Source:** Manual upload to Google Sheets → BigQuery sync
**Key Fields:**
- `user_email` - User attribution
- `activity_date` - Date of usage
- `conversation_count` - Number of conversations
- `message_count` - Number of messages sent
- `project_count` - Number of projects created
- `file_upload_count` - Files uploaded to conversations
- `upload_timestamp` - When data was uploaded (for freshness tracking)

**Update Frequency:** Manual (weekly or monthly)

#### 2. `claude_code_usage_stats`
**Purpose:** Claude Code IDE productivity metrics
**Data Source:** Claude Admin API `/claude_code` endpoint
**Key Fields:**
- `user_email` - Direct email attribution
- `activity_date` - Date of usage
- `num_sessions` - IDE sessions
- `commits_by_claude_code` - Git commits with AI
- `pull_requests_by_claude_code` - PRs created with AI
- `lines_added` - Lines added with AI assistance
- `lines_removed` - Lines removed with AI assistance
- `edit_tool_accepted` - File edits accepted
- `edit_tool_rejected` - File edits rejected
- `model` - AI model used
- `estimated_cost_usd` - Usage-based cost
- `input_tokens`, `output_tokens`, `cache_tokens` - Token usage

**Update Frequency:** Daily automated

#### 3. `cursor_usage_stats`
**Purpose:** Cursor IDE productivity and interaction metrics
**Data Source:** Cursor Admin API `/teams/daily-usage-data`
**Key Fields:**
- `user_email` - Direct email attribution
- `activity_date` - Date of usage
- `is_active` - User activity flag
- `total_lines_added` - Lines suggested by AI
- `accepted_lines_added` - Lines accepted by developer
- `total_applies` - AI suggestions applied
- `total_accepts` - AI suggestions accepted
- `total_rejects` - AI suggestions rejected
- `composer_requests` - Long-form code generation
- `chat_requests` - Q&A interactions
- `agent_requests` - Autonomous code changes
- `cmdk_usages` - Inline edit requests
- `subscription_included_reqs` - Within subscription (≤500)
- `usage_based_reqs` - Overage requests
- `most_used_model` - Primary AI model
- `client_version` - Cursor version

**Update Frequency:** Daily automated

#### 4. `claude_expenses`
**Purpose:** All Claude platform costs (claude.ai + Claude Code + API combined)
**Data Source:** Claude Admin API Cost Report
**Key Fields:**
- `expense_date` - Date of cost
- `platform` - "claude.ai" | "claude_code" | "claude_api"
- `workspace_id` - Workspace attribution
- `model` - AI model driving cost
- `cost_usd` - Cost in USD
- `cost_type` - "tokens" | "subscription" | "other"
- `token_type` - "input" | "output" | "cache_read" (if applicable)
- `service_tier` - Service level

**Update Frequency:** Daily automated

**Platform Segmentation Logic:**
- Use `workspace_id` or API endpoint patterns to distinguish claude.ai vs Claude Code vs API usage
- Aggregate by platform for dashboard filtering

#### 5. `cursor_expenses`
**Purpose:** Cursor subscription and overage costs
**Data Source:** Cursor Admin API `/teams/daily-usage-data` (cost fields)
**Key Fields:**
- `expense_date` - Date of cost
- `user_email` - User attribution
- `cost_type` - "subscription" | "usage_based" | "api_key"
- `subscription_included_reqs` - Requests within plan
- `usage_based_reqs` - Overage requests
- `estimated_cost_usd` - Total cost
- `subscription_plan` - Plan type

**Update Frequency:** Daily automated

**Cost Calculation:**
```
total_cost = (subscription_base / days_in_month) + (usage_based_reqs × overage_rate)
```

#### 6. `api_usage_expenses`
**Purpose:** Claude API programmatic usage costs ONLY (not Cursor API)
**Data Source:** Claude Admin API Cost Report (filtered)
**Key Fields:**
- `expense_date` - Date of cost
- `api_key_id` - API key attribution
- `model` - AI model used
- `cost_usd` - Cost in USD
- `input_tokens` - Input token count
- `output_tokens` - Output token count
- `cache_tokens` - Cache token usage
- `endpoint` - API endpoint used (messages, batch, etc.)
- `service_tier` - Service level

**Update Frequency:** Daily automated

**Filtering Logic:**
- Include ONLY programmatic API usage (Messages API, Batch API, Tools API)
- Exclude Claude Code and claude.ai costs (those go in `claude_expenses`)
- Use API key patterns or workspace IDs to filter

### Data Flow Architecture

```
┌─────────────────────┐
│  Data Sources       │
├─────────────────────┤
│ 1. Google Sheets    │──► Manual Upload ──────► claude_usage_stats
│ 2. Claude Admin API │──► /claude_code ────────► claude_code_usage_stats
│    (3 endpoints)    │──► Cost Report ─────────► claude_expenses
│                     │──► Cost Report (filter)─► api_usage_expenses
│ 3. Cursor Admin API │──► /daily-usage-data ───► cursor_usage_stats
│                     │──► /daily-usage-data ───► cursor_expenses
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  BigQuery Tables    │
│  (6 tables)         │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Metabase           │
│  (4 dashboards)     │
└─────────────────────┘
```

### API Key Mapping Strategy

**Challenge:** Claude API Cost Report returns `api_key_id`, not email
**Solution:** Maintain mapping table in Google Sheets:
- `api_key_id` → `user_email`
- `api_key_id` → `team_name`
- Manual maintenance by admin

**Table:** `dim_api_key_mapping` (BigQuery)
- Synced from Google Sheets
- Used for JOIN with `api_usage_expenses` and `claude_expenses`

---

## User Interface Design Goals

### Dashboard Strategy

**Platform:** Self-hosted Metabase on GCP Compute Engine
**Architecture:** See `/docs/api-reference/metabase-architecture.md`
**Cost:** ~$25/month VM + $0 licensing

### Core Dashboards (4 Required)

#### 1. Executive Summary Dashboard
**Target Users:** Finance Team, C-Suite
**Data Sources:** All expense tables aggregated
**Key Metrics:**
- Total monthly AI spend across all platforms
- Month-over-month growth rate
- Platform cost distribution (pie chart)
- Top 5 users by spend
- Budget vs actual variance

**Visualizations:**
- KPI cards (total spend, growth %)
- Line chart (monthly trends)
- Pie chart (platform distribution)
- Bar chart (user ranking)

#### 2. Cost Allocation Workbench
**Target Users:** Finance Team, Department Heads
**Data Sources:** All expense tables + user mapping
**Key Metrics:**
- User-level cost breakdown
- Team/department aggregations
- Platform-by-user spend matrix
- Cost per productivity ratios

**Visualizations:**
- Detailed cost tables (sortable, filterable)
- Heatmap (user × platform spending)
- Export-friendly format for budget reviews

#### 3. Productivity Analytics Dashboard
**Target Users:** Engineering Managers, Team Leads
**Data Sources:** `claude_code_usage_stats`, `cursor_usage_stats`
**Key Metrics:**
- Lines of code accepted (acceptance rate)
- Commits and PRs generated with AI
- Developer efficiency rankings
- Tool effectiveness comparison (Claude Code vs Cursor)

**Visualizations:**
- Acceptance rate trends (line chart)
- Productivity heatmap (team performance)
- Tool comparison (side-by-side metrics)

#### 4. Platform ROI Analysis
**Target Users:** Technical Architects, Finance
**Data Sources:** All tables (usage + expenses)
**Key Metrics:**
- Cost per line of code
- Cost per accepted suggestion
- Platform efficiency scores
- ROI by user and platform

**Visualizations:**
- Scatter plots (cost vs productivity)
- ROI trend lines
- Efficiency comparison charts
- Platform recommendation insights

### Accessibility & Usability

- **WCAG AA Compliance:** Full keyboard navigation, screen reader support
- **Color Scheme:** Color-blind friendly (blue/orange, not red/green)
- **Responsive Design:** Desktop-optimized with tablet support
- **Export Options:** CSV, XLSX, JSON, PNG for all dashboards

---

## Technical Assumptions

### Infrastructure

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

### Data Sources & APIs

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

### Metabase Architecture

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

### Data Quality & Validation

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

### Security & Compliance

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

## Epic List

### Epic 1: Foundation & Data Infrastructure
**Goal:** Establish BigQuery data warehouse and manual upload workflows
**Deliverables:**
- Create 6 BigQuery tables with proper schema
- Set up Google Sheets → BigQuery sync for claude.ai usage
- Create API key mapping table and management process
- Implement basic data validation checks

**Success Criteria:** Can manually upload claude.ai data and query in BigQuery

### Epic 2: Cursor Integration
**Goal:** Automate Cursor data collection for usage and costs
**Deliverables:**
- Implement Cursor API client using documented specs
- Build ETL pipeline: Cursor API → BigQuery (usage + expenses)
- Add error handling and retry logic
- Validate data accuracy against Cursor dashboard

**Success Criteria:** Daily automated Cursor data flowing to BigQuery with 99% accuracy

### Epic 3: Claude Platform Integration
**Goal:** Automate Claude ecosystem data collection (Code + expenses + API)
**Deliverables:**
- Implement Claude Admin API client for `/claude_code` endpoint
- Build cost report parser for claude_expenses (all platforms)
- Filter API usage costs into api_usage_expenses
- Implement platform segmentation logic

**Success Criteria:** All Claude data sources automated with correct platform attribution

### Epic 4: Metabase Dashboard Suite
**Goal:** Deploy self-hosted Metabase with 4 core dashboards
**Deliverables:**
- Provision GCP VM and deploy Metabase via Docker
- Connect to BigQuery with service account
- Build 4 dashboards: Executive, Cost Allocation, Productivity, ROI
- Configure export capabilities and user access

**Success Criteria:** Finance team can independently access dashboards and export data

### Epic 5: Production Hardening
**Goal:** Ensure system reliability and operational readiness
**Deliverables:**
- Implement Cloud Scheduler for daily automation
- Add comprehensive monitoring and alerting
- Create runbook for common operations
- Implement automated backup for Metabase VM
- Document user guides and admin procedures

**Success Criteria:** System runs autonomously for 30 days with >99% uptime

---

## Technical Implementation Approach

### Phase 1: Prove Manual + Cursor (Weeks 1-2)
**Focus:** Validate data flow with simplest path
1. Create BigQuery schema for all 6 tables
2. Set up Google Sheets → BigQuery sync (claude.ai usage)
3. Implement Cursor API integration (usage + expenses)
4. Build first Metabase dashboard (Cursor productivity)

**Success Gate:** End-to-end data flow for Cursor working

### Phase 2: Claude Integration (Weeks 3-4)
**Focus:** Add Claude ecosystem data sources
1. Implement Claude Admin API client (claude_code endpoint)
2. Build cost report parser with platform filtering
3. Create API key mapping workflow
4. Add remaining dashboards (Executive, Cost Allocation)

**Success Gate:** All 3 platforms flowing to BigQuery with correct attribution

### Phase 3: Dashboard & UX (Weeks 5-6)
**Focus:** Complete Metabase suite and polish
1. Build all 4 core dashboards
2. Configure export capabilities
3. Implement user access controls
4. Create user training documentation

**Success Gate:** Finance team using dashboards independently

### Phase 4: Automation & Hardening (Weeks 7-8)
**Focus:** Production readiness
1. Deploy Cloud Scheduler for daily runs
2. Implement monitoring and alerting
3. Add data quality validation
4. Create operational runbook
5. Perform 30-day reliability testing

**Success Gate:** System achieves >99% uptime for 30 days

### Contingency Plans

**API Integration Issues:**
- Fallback: Manual CSV upload for affected platform
- Timeline impact: +1 week per platform
- Mitigation: Parallel development of manual upload templates

**Data Quality Problems:**
- Fallback: Manual reconciliation process
- Timeline impact: +2 weeks for automated validation
- Mitigation: Start with manual validation, automate incrementally

**Performance Issues:**
- Fallback: Pre-aggregated summary tables
- Timeline impact: +1 week for optimization
- Mitigation: Design schema with performance in mind from start

**User Adoption Challenges:**
- Fallback: Increased training and documentation
- Timeline impact: +1-2 weeks for change management
- Mitigation: Involve finance team early in dashboard design

---

## Next Steps

### Architect Handoff
Use this PRD to create technical architecture documentation covering:
- BigQuery schema design with partitioning strategy
- ETL pipeline architecture for each data source
- Metabase deployment specification
- API integration patterns and error handling

Reference preserved documentation:
- `/docs/api-reference/cursor-api-specs.md`
- `/docs/api-reference/metabase-architecture.md`

### Developer Handoff
Break down epics into user stories focusing on:
- Table creation and schema implementation
- API client development with testing
- Dashboard creation with Metabase API
- Automation and monitoring setup

### Success Metrics

**30-Day Milestones:**
- All 6 BigQuery tables populated with accurate data
- 4 Metabase dashboards operational
- Daily automation running reliably
- Finance team using system for monthly reporting

**90-Day Goals:**
- 15% cost savings identified through analytics
- 80% reduction in manual reporting effort
- >99% system uptime achieved
- Positive user feedback from finance and engineering teams

---

*Generated using BMAD-METHOD™ framework by John (PM)*
