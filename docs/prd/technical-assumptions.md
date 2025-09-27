# Technical Assumptions

## Repository Structure: Monorepo
Single repository containing all components: Python ingestion scripts, BigQuery schema definitions, Looker dashboard configurations, and documentation. This approach simplifies dependency management and deployment coordination for the relatively small codebase.

## Service Architecture
**Serverless Microservices within Monorepo:** Cloud Run containerized jobs for each data source (Anthropic Claude API, Cursor API) with shared BigQuery client and utilities. This provides scalability and fault isolation while maintaining operational simplicity for daily batch processing.

## Testing Requirements
**Unit + Integration Testing:**
- Unit tests for API clients with mocking (pytest framework)
- Integration tests with BigQuery sandbox for data pipeline validation
- Data quality validation checks with schema drift detection
- Load testing simulating 30-day historical backfill scenarios

## Additional Technical Assumptions and Requests

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
