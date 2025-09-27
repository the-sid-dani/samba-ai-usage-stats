# AI Usage Analytics Dashboard Product Requirements Document (PRD)

**Project ID:** 03e62de8-5be5-4f58-a835-725ed7f7cab8
**Document Version:** 1.0
**Created:** September 26, 2025
**Author:** John (PM)
**Status:** Draft

---

## Goals and Background Context

### Goals
- **Financial Visibility:** Unified dashboard providing 100% AI spending visibility across Claude.ai, Claude Code, Claude API, and Cursor platforms
- **Cost Optimization:** Enable identification of 15-20% cost savings opportunities within 1 quarter through data-driven insights
- **Operational Efficiency:** Reduce manual reporting effort by 80% through automated daily data ingestion and dashboard generation
- **ROI Tracking:** Provide clear metrics on AI tool usage efficiency and productivity gains across team members
- **Budget Planning:** Support quarterly budget forecasting with accurate historical usage and cost trends

### Background Context

Our organization currently spends $7k+ monthly across 4 different AI platforms (Claude.ai, Claude Code, Claude API, and Cursor) with 30-40 API keys distributed among ~15 team members. The finance team (Jaya) lacks consolidated visibility into this spending, resulting in manual effort for quarterly reviews and missed optimization opportunities.

This PRD addresses the critical need for a unified analytics dashboard that automates data collection from vendor APIs, stores information in a BigQuery data warehouse, and presents finance-focused KPIs through Looker dashboards. The solution will provide single source of truth for AI usage patterns, cost allocation by user/team, and ROI metrics essential for strategic decision-making.

### Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| September 26, 2025 | 1.0 | Initial PRD creation from Project Brief | John (PM) |
| September 27, 2025 | 1.1 | Added Epic 5 deployment execution requirements and stories | John (PM) |
| September 27, 2025 | 1.2 | Updated for Metabase transition replacing Looker Studio | John (PM) |

---

## Requirements

### Functional Requirements

**FR1:** The system shall automatically ingest daily usage data from Anthropic Claude API (covering Claude API, Claude Code, and Claude.ai usage) and Cursor Admin API via their respective admin endpoints

**FR2:** The system shall store raw usage data in BigQuery with partitioned tables supporting 2+ years of historical retention

**FR3:** The system shall map API keys to user emails through Google Sheets integration for accurate cost allocation

**FR4:** The system shall generate normalized usage and cost fact tables in BigQuery for reporting and analytics

**FR5:** The system shall provide Metabase dashboards displaying monthly cost breakdowns by platform, user, and usage type through self-hosted deployment on GCP Compute Engine

**FR6:** The system shall calculate and display key productivity metrics including lines of code added/accepted, acceptance rates, and session counts

**FR7:** The system shall implement automated data validation checks to ensure accuracy against vendor invoices

**FR8:** The system shall provide email alerts when monthly costs increase by >20% compared to previous month

**FR9:** The system shall be deployable to Google Cloud Platform using Infrastructure as Code (Terraform) with automated provisioning of all required resources including BigQuery dataset, Cloud Run service, Secret Manager secrets, and IAM roles

**FR10:** The system shall provide automated BigQuery table and view deployment scripts that create all fact tables, dimension tables, and analytics views in the target environment

**FR11:** The system shall run autonomously in production with Cloud Scheduler triggering daily data ingestion at 6 AM PT without manual intervention

**FR12:** The system shall provide production health monitoring through Cloud Run health checks and comprehensive logging for operational visibility

**FR13:** The system shall deploy Metabase dashboards on self-hosted GCP Compute Engine VM using Docker containerization with PostgreSQL metadata storage

**FR14:** The system shall provide all 6 dashboard types through Metabase interface: Finance Executive Dashboard, Cost Allocation Workbench, Engineering Productivity Analytics, Platform ROI Analysis, System Administration Panel, and Compliance & Security View

**FR15:** The system shall maintain existing BigQuery data source connectivity through Metabase BigQuery driver with service account authentication

**FR16:** The system shall provide programmatic dashboard management through Metabase REST API enabling dashboard-as-code deployment and configuration

**FR17:** The system shall support all existing export capabilities (CSV, XLSX, JSON, PNG) through Metabase native export functionality

### Non-Functional Requirements

**NFR1:** The system shall maintain 99.5% uptime for daily data ingestion jobs with automatic retry mechanisms

**NFR2:** The system shall complete daily data processing within 2 hours of scheduled execution at 6 AM PT

**NFR3:** All API keys and credentials shall be stored securely in Google Secret Manager with audit logging enabled

**NFR4:** The system shall implement exponential backoff for API rate limit handling with maximum 3 retry attempts

**NFR5:** Data processing shall scale to support 100+ users and 50+ API keys without architecture changes

**NFR6:** All data transformations shall be logged with structured JSON format for debugging and monitoring

**NFR7:** BigQuery dataset shall use US region with Google-managed encryption for data at rest

**NFR8:** The system shall provide health check endpoints for monitoring job success/failure status

**NFR9:** The deployment process shall complete infrastructure provisioning within 15 minutes using Terraform automation with proper state management and rollback capabilities

**NFR10:** The CI/CD pipeline shall automatically deploy code changes to production within 10 minutes of successful testing with zero-downtime deployment strategy

**NFR11:** The BigQuery table and view deployment shall handle schema migrations gracefully without data loss and support rollback to previous schema versions

**NFR12:** All deployment processes shall include comprehensive validation steps ensuring >99% deployment success rate with automatic rollback on failure

**NFR13:** The production environment shall be fully reproducible from Infrastructure as Code with no manual configuration steps required

**NFR14:** The Metabase VM shall maintain 99.5% uptime with automated backup and monitoring on GCP Compute Engine e2-medium instance (~$25/month)

**NFR15:** Dashboard queries shall complete within 5 seconds leveraging existing BigQuery view optimizations and VM resource allocation

**NFR16:** Metabase deployment shall be fully automated using Docker Compose with one-command setup and configuration

**NFR17:** The VM infrastructure shall be reproducible using Infrastructure as Code with automated PostgreSQL setup and Metabase configuration

---

## User Interface Design Goals

### Overall UX Vision
Clean, finance-focused dashboard emphasizing cost visibility and trend analysis. Primary users are finance professionals who need quick access to spending summaries, cost allocation by user/team, and month-over-month comparisons. Interface should minimize cognitive load while providing drill-down capabilities for detailed analysis.

### Key Interaction Paradigms
- **Role-based Navigation:** Different menu structures for Finance vs Engineering vs Admin users
- **Contextual Help:** Embedded tooltips and metric definitions for non-technical finance users
- **Progressive Disclosure:** Summary cards that expand to detailed breakdowns on click
- **Cross-Dashboard Linking:** Ability to jump from cost anomaly to productivity details for root cause analysis

### Core Screens and Views
1. **Finance Executive Dashboard** - High-level spend summary with budget variance alerts
2. **Cost Allocation Workbench** - Detailed user/team/project cost breakdowns with export tools
3. **Engineering Productivity Analytics** - Developer efficiency metrics and team comparisons
4. **Platform ROI Analysis** - Cost-per-productivity calculations across all AI tools
5. **System Administration Panel** - Data quality monitoring and manual controls (admin-only)
6. **Compliance & Security View** - Access auditing and API key management (security-only)

### Accessibility: WCAG AA
- **Keyboard Navigation:** Full dashboard navigation without mouse for accessibility compliance
- **Screen Reader Support:** Proper ARIA labels for all charts and data tables
- **Color Blind Friendly:** Blue/orange color scheme instead of red/green for status indicators
- **High Contrast Mode:** Optional high contrast theme for visually impaired users

### Branding
Corporate-standard Metabase styling with clear, professional aesthetic focused on data readability rather than visual flourishes, utilizing Metabase theming capabilities for consistent branding.

### Target Device and Platforms: Web Responsive
Primary usage on desktop/laptop for detailed analysis, with responsive design supporting tablet access for executive summary views.

---

## Technical Assumptions

### Repository Structure: Monorepo
Single repository containing all components: Python ingestion scripts, BigQuery schema definitions, Looker dashboard configurations, and documentation. This approach simplifies dependency management and deployment coordination for the relatively small codebase.

### Service Architecture
**Serverless Microservices within Monorepo:** Cloud Run containerized jobs for each data source (Anthropic Claude API, Cursor API) with shared BigQuery client and utilities. This provides scalability and fault isolation while maintaining operational simplicity for daily batch processing.

### Testing Requirements
**Unit + Integration Testing:**
- Unit tests for API clients with mocking (pytest framework)
- Integration tests with BigQuery sandbox for data pipeline validation
- Data quality validation checks with schema drift detection
- Load testing simulating 30-day historical backfill scenarios

### Additional Technical Assumptions and Requests

**Infrastructure & Deployment:**
- **Google Cloud Platform:** Existing project ai-workflows-459123 with BigQuery, Cloud Run, Secret Manager
- **Python 3.11:** Runtime environment with google-cloud libraries and requests
- **Container Strategy:** Multi-stage Docker builds optimized for Cloud Run cold starts
- **Scheduling:** Google Cloud Scheduler triggering daily jobs at 6 AM PT

**Data Architecture:**
- **BigQuery Dataset:** US region with partitioned tables for cost optimization
- **Data Retention:** 2+ years for historical trend analysis and compliance
- **Identity Resolution:** Google Sheets as manual mapping source for API key attribution
- **Data Quality:** Automated validation against vendor invoice reconciliation

**Security & Compliance:**
- **Secret Management:** Google Secret Manager for API keys with quarterly rotation
- **Access Controls:** IAM with principle of least privilege for service accounts
- **Audit Logging:** Structured JSON logging to Cloud Logging for all operations
- **Data Encryption:** Google-managed keys at rest, TLS 1.2+ in transit

**Monitoring & Operations:**
- **Health Checks:** /health endpoints for Cloud Run services
- **Error Handling:** Exponential backoff with circuit breaker patterns
- **Alerting:** Cost anomaly detection and data staleness monitoring
- **Performance:** 2-hour SLA for daily processing completion

---

## Epic List

**Epic 1: Foundation & Cursor Integration**
Establish project infrastructure, BigQuery data warehouse, and complete Cursor platform integration delivering first usable dashboard for engineering productivity metrics.

**Epic 2: Anthropic Multi-Platform Integration**
Add Anthropic Claude API integration covering Claude API, Claude Code, and Claude.ai usage data with unified user attribution and cost allocation capabilities.

**Epic 3: Advanced Analytics & Finance Dashboard**
Implement comprehensive cost analysis, budget tracking, and finance-specific reporting with automated alerting for cost anomalies and variance detection.

**Epic 4: Production Hardening & Monitoring**
Deploy production-grade monitoring, data quality validation, security hardening, and operational documentation for long-term system reliability.

**Epic 5: Infrastructure Provisioning & Deployment**
Execute infrastructure provisioning, deploy all services to production, and validate end-to-end system integration with real data sources for business-ready operation.

**Epic 6: Metabase Dashboard Platform**
Replace planned Looker Studio with free self-hosted Metabase on GCP Compute Engine, providing all 6 dashboard types with API-driven management capabilities while maintaining existing BigQuery data pipeline integrity.

### Epic Rationale
- **Epic 1** provides immediate value to engineering team while proving technical architecture
- **Epic 2** adds the primary cost data sources needed by finance team
- **Epic 3** delivers the core business value for cost optimization and budget planning
- **Epic 4** ensures enterprise-grade reliability and maintainability
- **Epic 5** bridges development to production, ensuring actual business value delivery
- **Epic 6** provides cost-effective dashboard solution with superior API capabilities and zero licensing costs

Each epic delivers deployable functionality that provides tangible value to users, with logical dependencies flowing from infrastructure to data sources to analytics to operations.

---

## Technical Implementation Approach

### Phase 1: Prove Architecture
- Start with Cursor integration only
- Validate entire pipeline: API → BigQuery → Looker
- Implement comprehensive error handling early
- **Success Criteria:** End-to-end data flow working reliably

### Phase 2: Add Complexity
- Integrate Anthropic APIs with extensive testing
- Implement Google Sheets mapping with validation
- Add basic monitoring and alerting
- **Success Criteria:** Multi-platform cost attribution working

### Phase 3: Polish & Harden
- Build advanced Metabase dashboards
- Implement automated data quality checks
- Add production monitoring and recovery
- **Success Criteria:** Finance team can use system independently

### Phase 4: Infrastructure Execution
- Execute Terraform infrastructure provisioning
- Deploy BigQuery tables and views to production
- Configure Secret Manager with API keys
- Set up IAM roles and service accounts
- **Success Criteria:** GCP infrastructure fully provisioned and accessible

### Phase 5: Production Deployment & Integration
- Build and deploy Docker container to Cloud Run
- Configure Cloud Scheduler for daily automation
- Execute end-to-end integration testing with real APIs
- Validate data pipeline with production data
- **Success Criteria:** System running autonomously in production with real data

### Contingency Plans
- **API Integration Issues:** Fall back to manual data upload initially
- **Performance Problems:** Implement caching and query optimization
- **Data Quality Issues:** Add manual validation checkpoints
- **User Adoption Problems:** Provide training and support documentation

---

## Next Steps

### UX Expert Prompt
Review this PRD and create comprehensive UI/UX specifications for the multi-stakeholder dashboard system, focusing on role-based user experiences and finance team workflow optimization.

### Architect Prompt
Use this PRD to create detailed technical architecture documentation covering the serverless data pipeline, BigQuery schema design, and Cloud Run deployment specifications for the AI usage analytics system.

---

*Generated using BMAD-METHOD™ framework by John (PM)*