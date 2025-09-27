# Requirements

## Functional Requirements

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

## Non-Functional Requirements

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
