# Tech Stack

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| Backend Language | Python | 3.11+ | Data pipeline scripting | Excellent BigQuery/GCP integration, simple for data tasks |
| Data Processing | pandas | 2.0+ | Data transformation | Standard for data manipulation |
| Database | BigQuery | Latest | Data warehouse | Serverless, no maintenance, built for analytics |
| Authentication | Google Cloud IAM | Latest | Service account auth | Native GCP integration |
| Backend Testing | pytest | 7.4+ | Unit tests | Simple testing framework |
| Build Tool | Docker | 24+ | Containerization | Required for Cloud Run |
| CI/CD | GitHub Actions | Latest | Automated deployment | Simple, free deployment pipeline |
| Monitoring | Google Cloud Logging | Latest | Basic logging | Built-in monitoring, no extra tools needed |
| Secret Management | Google Secret Manager | Latest | API key storage | Secure, simple credential storage |
| Scheduling | Google Cloud Scheduler | Latest | Daily job automation | Managed cron service |
| Data Visualization | Metabase | Latest | Self-hosted dashboards | Full control, advanced features, connects to BigQuery |
| VM Infrastructure | GCP Compute Engine | e2-medium | Metabase hosting | Reliable, managed VM for self-hosted solution |
| VM Database | PostgreSQL | 15+ | Metabase metadata | Required for Metabase configuration storage |
| API Key Mapping | Google Sheets API | v4 | Manual identity resolution | Simple spreadsheet for 30-40 keys |
| Dashboard Automation | Metabase REST API | Latest | Programmatic chart/filter creation | API-first for dashboard-as-code approach |
| Configuration Management | JSON + Python | jsonschema 4.20+ | Chart/filter configuration | Systematic chart type mapping and validation |
| Chart Templates | chart_templates.py | N/A | Visualization settings reference | Defines viz_settings for 13 chart types |
| Filter Templates | filter_templates.py | N/A | Field filter configurations | Defines 9 filter widget types |

---
