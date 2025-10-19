# Technical Implementation Approach

## Phase 1: Prove Manual + Cursor (Weeks 1-2)
**Focus:** Validate data flow with simplest path
1. Create BigQuery schema for all 6 tables
2. Set up Google Sheets → BigQuery sync (claude.ai usage)
3. Implement Cursor API integration (usage + expenses)
4. Build first Metabase dashboard (Cursor productivity)

**Success Gate:** End-to-end data flow for Cursor working

## Phase 2: Claude Integration (Weeks 3-4)
**Focus:** Add Claude ecosystem data sources
1. Implement Claude Admin API client (claude_code endpoint)
2. Build cost report parser with platform filtering
3. Create API key mapping workflow
4. Add remaining dashboards (Executive, Cost Allocation)

**Success Gate:** All 3 platforms flowing to BigQuery with correct attribution

## Phase 3: Dashboard & UX (Weeks 5-6)
**Focus:** Complete Metabase suite and polish
1. Build all 4 core dashboards
2. Configure export capabilities
3. Implement user access controls
4. Create user training documentation

**Success Gate:** Finance team using dashboards independently

## Phase 4: Automation & Hardening (Weeks 7-8)
**Focus:** Production readiness
1. Deploy Cloud Scheduler for daily runs
2. Implement monitoring and alerting
3. Add data quality validation
4. Create operational runbook
5. Perform 30-day reliability testing

**Success Gate:** System achieves >99% uptime for 30 days

## Contingency Plans

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
