# Goals and Background Context

## Goals

- **Unified Cost Visibility:** Provide 100% spending visibility across Claude ecosystem (claude.ai, Claude Code, Claude API) and Cursor platform through consolidated BigQuery data warehouse and Metabase dashboards
- **Platform-Specific Analytics:** Enable distinct analysis of chat-based AI usage (claude.ai) vs developer productivity tools (Claude Code, Cursor) with separate usage and cost tracking
- **Cost Optimization:** Identify 15-20% cost savings opportunities within 1 quarter through data-driven insights into usage patterns and platform efficiency
- **Operational Efficiency:** Reduce manual reporting effort by 80% through automated data ingestion from APIs and manual upload workflows
- **ROI Tracking:** Measure AI tool productivity gains with metrics including acceptance rates, lines of code, and cost-per-productivity calculations

## Background Context

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

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| September 26, 2025 | 1.0 | Initial PRD with 4 platforms + Looker | John (PM) |
| October 17, 2025 | 2.0 | Simplified to 3 platforms, 6 tables, Metabase focus, manual claude.ai upload | John (PM) |

---
