# Project Brief: AI Usage Analytics Dashboard

**Project ID:** 03e62de8-5be5-4f58-a835-725ed7f7cab8
**Created:** September 26, 2025
**Author:** Business Analyst Mary

## Executive Summary

Unified analytics dashboard tracking AI usage and costs across Claude.ai, Claude Code, Claude API, and Cursor platforms. System will provide finance team with clear visibility into usage patterns, cost allocation, and ROI metrics through automated data pipeline feeding BigQuery warehouse and Looker dashboards.

**Key Value Proposition:** Single source of truth for $7k+ monthly AI spend across 4 platforms, enabling finance team to optimize costs and track ROI.

## Problem Statement

### Current State
- Organization uses 4 different AI platforms (Claude.ai, Claude Code, Claude API, Cursor) with no unified visibility
- 30-40 API keys across ~15 team members with manual cost tracking
- Finance team (Jaya) requires quarterly reporting for budget planning

### Pain Points
- Finance team lacks consolidated view of AI spending across platforms
- No visibility into user adoption patterns or ROI metrics
- Manual effort required to track and allocate costs
- Difficulty identifying optimization opportunities
- No clear understanding of seat vs usage-based costs

### Business Impact
- **Financial:** $7k+ monthly AI spend without proper cost allocation
- **Operational:** Manual reporting effort for quarterly reviews
- **Strategic:** Unable to optimize AI tool usage or identify ROI

## Proposed Solution

### Core Concept
Automated data pipeline pulling usage metrics from vendor APIs into unified BigQuery warehouse with Looker dashboards providing finance-focused KPIs.

### Technical Approach
```
Python API Scripts → Cloud Run (daily) → BigQuery → Google Sheets (identity) → Looker Dashboards
```

### Key Differentiators
- **Unified View:** Single dashboard for all AI platform usage
- **Automated Refresh:** Daily data updates via Cloud Run jobs
- **Smart Attribution:** API key mapping through Google Sheets integration
- **Finance-First:** KPIs designed for cost optimization and ROI tracking

## Target Users

### Primary User Segment: Finance Team
- **Profile:** Finance managers and administrators (Jaya)
- **Current Workflow:** Manual cost tracking and quarterly budget reviews
- **Needs:** Consolidated spending visibility, cost allocation by user/team
- **Goals:** Optimize AI spending, accurate budget forecasting

### Secondary User Segment: Engineering Leadership
- **Profile:** Engineering managers and team leads
- **Current Workflow:** Ad-hoc usage monitoring through individual platforms
- **Needs:** Team productivity metrics and adoption insights
- **Goals:** Maximize AI tool ROI and optimize team workflows

## Goals & Success Metrics

### Business Objectives
- **Cost Visibility:** 100% AI spending tracked and allocated within 2 weeks
- **Operational Efficiency:** Reduce manual reporting effort by 80%
- **Optimization:** Identify 15-20% cost savings opportunities within 1 quarter

### User Success Metrics
- Finance team can generate monthly reports in <5 minutes
- Clear visibility into seat vs usage-based costs across all platforms
- User adoption and productivity trends clearly tracked

### Key Performance Indicators (KPIs)
- **Usage KPIs:** Active users (DAU/WAU), Total interactions, Lines of code added/accepted, Acceptance rate %
- **Cost KPIs:** Total monthly spend by platform, Cost per user, Seat vs API usage breakdown, Month-over-month trends
- **ROI KPIs:** Cost per line of code accepted, Usage efficiency by team/user

## Technical Implementation

### Data Sources & API Integration

**Anthropic Claude API:**
- Endpoint: `/v1/organizations/usage_report/messages`
- Key Fields: `api_key_id`, `workspace_id`, `model`, `uncached_input_tokens`, `output_tokens`
- Identity Mapping: API key ID → email via Google Sheets lookup

**Anthropic Claude Code:**
- Endpoint: `/v1/organizations/usage_report/claude_code`
- Key Fields: `email`, `sessions`, `loc_added`, `loc_removed`, `acceptance_rate`
- Identity Mapping: Direct email attribution

**Anthropic Claude.ai:**
- Source: Console usage metrics with email attribution
- Key Fields: `email`, `message_count`, `conversation_sessions`, `input_tokens`, `output_tokens`, `daily_active_usage`
- Identity Mapping: Direct email attribution

**Cursor:**
- Endpoint: `/teams/daily-usage-data`
- Key Fields: `email`, `totalLinesAdded`, `acceptedLinesAdded`, `subscriptionIncludedReqs`, `usageBasedReqs`
- Identity Mapping: Direct email attribution

### Architecture

**Data Pipeline:**
1. **Ingestion:** Python scripts with requests library for API calls
2. **Scheduling:** Google Cloud Scheduler → Cloud Run jobs (daily 6am PT)
3. **Storage:** BigQuery dataset with raw + curated tables
4. **Identity Resolution:** Google Sheets → BigQuery import for API key mapping
5. **Visualization:** Looker Studio connected to BigQuery views

**Data Model:**
- **Raw Tables:** `raw_anthropic_usage`, `raw_anthropic_cost`, `raw_claude_code`, `raw_cursor_usage`
- **Curated Tables:** `dim_users`, `dim_api_keys`, `fct_usage_daily`, `fct_cost_daily`
- **Aggregated Views:** `agg_monthly_finance`, `agg_user_summary`

## MVP Scope

### Core Features (Must Have)
- **Daily Automated Ingestion:** All 4 platforms with error handling and retries
- **BigQuery Data Warehouse:** Normalized schema with raw + curated layers
- **Google Sheets Integration:** API key → email mapping with manual maintenance
- **Basic Looker Dashboard:** Usage + cost KPIs with monthly/quarterly views
- **Cost Anomaly Alerts:** Email notifications for unusual spending patterns

### Out of Scope for MVP
- Real-time dashboards (daily refresh sufficient)
- Advanced ML analytics or predictive modeling
- Automated API key provisioning workflows
- Integration with additional platforms beyond the 4 specified

### MVP Success Criteria
Finance team can access unified monthly usage/cost report within 2 weeks of deployment, with 95% data accuracy compared to vendor invoices.

## Implementation Phases

### Phase 1: Proof of Concept (1 week)
- Single platform integration (Cursor - easiest email attribution)
- Basic BigQuery schema and Cloud Run deployment
- Validates entire pipeline architecture

### Phase 2: Full Platform Integration (1 week)
- Add remaining 3 platforms (Claude API, Claude Code, Claude.ai)
- Implement Google Sheets connector for API key mapping
- Complete data normalization and user attribution

### Phase 3: Dashboard Development (3-5 days)
- Build Looker Studio dashboards with finance-focused KPIs
- Create monthly/quarterly report templates
- Implement cost anomaly alerting

### Phase 4: Production Deployment (2-3 days)
- Production environment setup with monitoring
- Documentation and handoff to finance team
- Performance optimization and security hardening

## Technical Considerations

### Platform Requirements
- **Target Environment:** Google Cloud Platform (ai-workflows-459123 project)
- **Compute:** Cloud Run for serverless Python execution
- **Storage:** BigQuery for data warehouse and Google Sheets for identity mapping
- **Monitoring:** Cloud Monitoring for job success/failure tracking

### Technology Stack
- **Backend:** Python 3.9+ with requests, google-cloud-bigquery libraries
- **Infrastructure:** Cloud Run, Cloud Scheduler, Secret Manager
- **Data:** BigQuery dataset with partitioned tables
- **Visualization:** Looker Studio with BigQuery connector

### Security & Compliance
- **API Keys:** Stored in Google Secret Manager with IAM controls
- **Data Access:** BigQuery IAM with principle of least privilege
- **Audit Trail:** All API calls and data transformations logged
- **Data Retention:** 2+ years for historical trend analysis

## Constraints & Assumptions

### Constraints
- **Budget:** Existing Google Cloud credits and platform subscriptions
- **Timeline:** 2-3 weeks for MVP delivery to finance team
- **Resources:** 1 developer + analyst support for implementation
- **Technical:** Must use existing Google Cloud project and BigQuery

### Key Assumptions
- Admin API access remains stable for all 4 platforms
- Google Sheets manual maintenance acceptable for 30-40 API keys
- Daily data refresh sufficient (no real-time requirements)
- Finance team comfortable with Looker Studio interface
- Current API rate limits sufficient for daily batch processing

## Risks & Mitigation

### Key Risks
- **API Rate Limits:** Implement exponential backoff and caching strategies
- **API Changes:** Version pinning and monitoring for endpoint modifications
- **Data Quality Issues:** Validation checks and reconciliation with vendor invoices
- **Access Management:** Secure API key storage and rotation procedures

### Open Questions
- What is the preferred cost allocation method for shared/automation API keys?
- Should historical data be backfilled, and if so, how far back?
- What specific cost anomaly thresholds should trigger alerts?
- Are there any compliance requirements for data retention?

### Areas Needing Further Research
- Historical data availability and backfill requirements
- Looker Studio licensing and advanced feature needs
- Integration with existing finance/accounting systems
- Automated API key lifecycle management for future scaling

## Next Steps

### Immediate Actions
1. **Environment Setup:** Configure Google Cloud project permissions and BigQuery dataset
2. **API Access Verification:** Test admin API keys for all 4 platforms
3. **Google Sheets Creation:** Set up API key mapping spreadsheet with current 30-40 keys
4. **Development Start:** Begin with Cursor API integration as proof of concept

### PM Handoff
This Project Brief provides the full context for the AI Usage Analytics Dashboard. The project is ready for technical implementation with clear requirements, architecture, and success criteria defined. Development can begin immediately with Phase 1 (Cursor integration proof of concept).

---

*Generated by Business Analyst Mary using BMAD-METHOD™ framework*