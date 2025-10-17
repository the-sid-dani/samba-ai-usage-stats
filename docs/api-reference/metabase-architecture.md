# Metabase Dashboard Architecture

## Overview

Metabase is a free, open-source business intelligence platform that enables programmatic dashboard creation and management through a comprehensive REST API. We're using it as a cost-effective alternative to Looker Studio for AI usage analytics dashboards.

## Why Metabase?

**Key Advantages:**
- **$0 Licensing Cost** - Free self-hosted version (vs potential Looker licensing)
- **Full REST API** - "Dashboards-as-code" approach enables automation
- **Complete Export Capabilities** - CSV, XLSX, JSON, PNG
- **Faster Deployment** - Days instead of weeks for dashboard creation
- **Programmatic Control** - API-first architecture for full automation

**Trade-offs:**
- Manual user management (no RBAC in free version)
- VM maintenance responsibility
- Community support vs enterprise support
- Custom alerting implementation needed

## Deployment Architecture

### Infrastructure

**Platform:** GCP Compute Engine
**Instance Type:** e2-medium (2 vCPUs, 4GB RAM)
**Operating System:** Ubuntu 20.04 LTS
**Storage:** 20GB persistent SSD
**Cost:** ~$25/month
**Location:** us-central1 (same region as BigQuery)

### Component Stack

```
GCP Compute Engine VM
├── Docker Compose
│   ├── Metabase Container (port 3000)
│   │   └── Metabase Application
│   └── PostgreSQL Container (port 5432)
│       └── Metadata Storage
├── Service Account
│   └── BigQuery Read Access
└── Monitoring & Backup Scripts
```

### Docker Configuration

**docker-compose.yml structure:**
```yaml
version: '3'
services:
  postgres:
    image: postgres:13
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=metabase
      - POSTGRES_USER=metabase
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"
    environment:
      - MB_DB_TYPE=postgres
      - MB_DB_HOST=postgres
      - MB_DB_PORT=5432
      - MB_DB_DBNAME=metabase
    depends_on:
      - postgres

volumes:
  postgres-data:
```

## Metabase API Capabilities

### Authentication

**Endpoint:** `POST /api/session`
**Method:** Session token or API key

```json
// Request
{
  "username": "admin@example.com",
  "password": "secure-password"
}

// Response
{
  "id": "session-token-here"
}
```

### Dashboard Management

**Create Dashboard:**
```
POST /api/dashboard

Request:
{
  "name": "Finance Executive Dashboard",
  "description": "Monthly cost summaries and growth trends",
  "collection_id": 1,
  "parameters": [
    {
      "name": "Date Range",
      "type": "date/range",
      "default": "past30days"
    }
  ]
}

Response:
{
  "id": 123,
  "name": "Finance Executive Dashboard",
  "created_at": "2025-01-15T10:00:00Z",
  "collection_id": 1
}
```

**Update Dashboard:**
```
PUT /api/dashboard/{id}

Request:
{
  "name": "Updated Dashboard Name",
  "description": "Updated description"
}
```

**List Dashboards:**
```
GET /api/dashboard

Response:
[
  {
    "id": 123,
    "name": "Finance Executive Dashboard",
    "description": "...",
    "collection_id": 1
  }
]
```

### Card/Widget Management

**Create Dashboard Widget (Card):**
```
POST /api/card

Request:
{
  "name": "Monthly Cost Trend",
  "display": "line",
  "dataset_query": {
    "type": "native",
    "native": {
      "query": "SELECT date, SUM(cost) FROM costs GROUP BY date"
    },
    "database": 1
  },
  "visualization_settings": {
    "graph.dimensions": ["date"],
    "graph.metrics": ["sum"]
  }
}
```

**Get Card Details:**
```
GET /api/card/{id}
```

### Export Functionality

**Supported Export Formats:**
- **CSV** - Raw data export for spreadsheet analysis
- **XLSX** - Formatted Excel with charts preserved
- **JSON** - API-friendly programmatic format
- **PNG** - Dashboard screenshots for presentations

**Export Endpoint Pattern:**
```
GET /api/card/{card_id}/query/csv
GET /api/card/{card_id}/query/xlsx
GET /api/card/{card_id}/query/json
GET /api/dashboard/{dashboard_id}/png
```

## Dashboard Suite Design

### 1. Finance Executive Dashboard
**Target Users:** C-Suite, Finance Leadership
**Data Source:** `vw_monthly_finance`, `vw_executive_total_investment`

**Key Metrics:**
- Total monthly AI investment
- Month-over-month growth rates
- Cost per user averages
- Platform cost distribution

**Visualizations:**
- KPI cards (total spend, growth %)
- Line charts (cost trends)
- Pie charts (platform distribution)
- Bar charts (budget variance)

### 2. Cost Allocation Workbench
**Target Users:** Finance Team, Department Heads
**Data Source:** `vw_cost_allocation`

**Key Metrics:**
- Detailed user cost breakdowns
- Team/department cost groupings
- ROI analysis per user
- Efficiency rankings

**Visualizations:**
- Detailed tables (user costs)
- Bar charts (team comparisons)
- Scatter plots (cost vs productivity)
- Ranking tables (efficiency tiers)

### 3. Engineering Productivity Analytics
**Target Users:** Engineering Managers, Team Leads
**Data Source:** `vw_ai_coding_productivity`, `vw_productivity_metrics`

**Key Metrics:**
- Lines of code assisted by AI
- Acceptance rates
- Productivity trends
- Tool effectiveness (Cursor vs Claude Code)

**Visualizations:**
- Line charts (acceptance rate trends)
- Heatmaps (team productivity)
- Distribution charts (performance tiers)
- Comparison tables (tool effectiveness)

### 4. Platform ROI Analysis
**Target Users:** Technical Architects, Cost Engineers
**Data Source:** `vw_api_consumption`, cross-category views

**Key Metrics:**
- Cost per productivity unit
- Platform efficiency comparison
- ROI trends over time
- Value generation estimates

**Visualizations:**
- ROI trend lines
- Efficiency comparison charts
- Cost-per-productivity analysis
- Platform recommendation insights

### 5. System Administration Panel
**Target Users:** System Administrators, DevOps
**Data Source:** System metadata, pipeline logs

**Key Metrics:**
- Data freshness indicators
- Pipeline health status
- Attribution coverage
- System resource utilization

**Visualizations:**
- Status indicators (green/yellow/red)
- Health monitoring charts
- Error tracking tables
- Performance metrics

### 6. Compliance & Security View
**Target Users:** Security Team, Compliance Officers
**Data Source:** Audit logs, access tracking

**Key Metrics:**
- User access auditing
- API key usage monitoring
- Cost anomaly detection
- Data governance compliance

**Visualizations:**
- Access audit tables
- Anomaly detection alerts
- Compliance status indicators
- Security event timelines

## Collections & Access Control

**Organization Structure:**
```
Metabase Collections
├── Finance Collection
│   ├── Executive Dashboard (read: finance team)
│   └── Cost Allocation Workbench (read: finance team)
├── Engineering Collection
│   ├── Productivity Analytics (read: engineering team)
│   └── Platform ROI Analysis (read: engineering team)
└── Admin Collection
    ├── System Administration Panel (read: admins only)
    └── Compliance & Security View (read: security team)
```

**User Groups:**
- **Finance Team** - Read access to Finance collection
- **Engineering Team** - Read access to Engineering collection
- **Security Team** - Read access to Compliance & Security
- **Administrators** - Full access to all collections

**Note:** Free version requires manual user management. RBAC available in paid version.

## Security Configuration

### Firewall Rules
```
Allow Ports:
- 3000 (Metabase) - From company IP ranges only
- 22 (SSH) - From admin IP ranges only

Deny:
- All other inbound traffic
```

### Authentication
- SSH key-based authentication only
- No root login (dedicated metabase user)
- VM service account with minimal BigQuery permissions
- Metabase admin password stored in Secret Manager

### Network Security
- Static external IP with firewall restrictions
- Internal PostgreSQL (no external access)
- BigQuery access via service account only

## Backup & Disaster Recovery

### PostgreSQL Backups
**Frequency:** Daily automated backups
**Destination:** GCP Cloud Storage
**Retention:** 30 days
**Method:** pg_dump via cron job

**Backup Script:**
```bash
#!/bin/bash
# Daily PostgreSQL backup to Cloud Storage
pg_dump -U metabase metabase | \
  gzip | \
  gsutil cp - gs://metabase-backups/$(date +%Y%m%d).sql.gz
```

### VM Snapshots
**Frequency:** Weekly
**Retention:** 4 weeks
**Purpose:** Full system recovery

### Disaster Recovery
**RTO (Recovery Time Objective):** 2 hours
**RPO (Recovery Point Objective):** 24 hours

**Recovery Steps:**
1. Provision new VM from latest snapshot
2. Restore PostgreSQL from Cloud Storage backup
3. Update DNS/firewall rules
4. Verify dashboard functionality

## Monitoring & Alerting

### Cloud Monitoring Metrics
- VM health (uptime, CPU, memory)
- Disk usage (alert at 80%)
- Service availability (Metabase, PostgreSQL)
- Network traffic patterns

### Custom Alerts
- **VM Downtime** - Immediate notification
- **Disk Usage >80%** - 24-hour warning
- **PostgreSQL Unavailable** - Immediate notification
- **Backup Failure** - Daily check

### Health Check Script
```bash
#!/bin/bash
# Metabase health check
curl -f http://localhost:3000/api/health || \
  echo "Metabase health check failed" | \
  mail -s "Alert: Metabase Down" admin@example.com
```

## Performance Optimization

### Query Performance
**Target:** <5 seconds for all dashboard queries
**Strategy:**
- Pre-aggregated summary tables for Metabase
- BigQuery materialized views
- Proper indexing on date fields
- Query result caching in Metabase

### Summary Tables
```sql
-- Monthly summary for fast dashboard performance
CREATE TABLE mb_monthly_summary (
  summary_month DATE,
  user_email STRING,
  total_coding_cost FLOAT64,
  total_api_cost FLOAT64,
  total_assistant_cost FLOAT64,
  total_ai_investment FLOAT64
);

-- Current month live view
CREATE VIEW mb_current_month_live AS
SELECT * FROM daily_facts
WHERE DATE_TRUNC(activity_date, MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH);
```

### Caching Strategy
- **Historical data:** 24-hour cache
- **Current month:** 1-hour cache
- **Real-time metrics:** No cache

## Automation & Scheduled Reports

### Email Reports
**Frequency:** Monthly (first Monday of month)
**Recipients:** Finance team, executive leadership
**Format:** PDF dashboard exports + XLSX data

**Configuration in Metabase:**
- Set up email subscription per dashboard
- Configure delivery schedule
- Specify recipient lists

### API-Driven Exports
```python
# Automated monthly export script
import requests

session = authenticate_metabase()
dashboard_id = 123

# Export as PDF
response = requests.get(
    f"{METABASE_URL}/api/dashboard/{dashboard_id}/pdf",
    headers={"X-Metabase-Session": session}
)

# Save to Cloud Storage
upload_to_gcs(response.content, "monthly_report.pdf")
```

## Implementation Timeline

**Week 1: Infrastructure**
- GCP VM provisioning
- Docker and PostgreSQL setup
- Metabase installation

**Week 2: Integration**
- BigQuery service account connection
- First dashboard prototype (Finance Executive)
- API workflow validation

**Week 3-4: Dashboard Development**
- Build all 6 dashboard types
- Configure export functionality
- User management setup

**Week 5: Production Readiness**
- Performance optimization
- Backup/monitoring implementation
- Documentation and handoff

## Cost Analysis

**Infrastructure Costs:**
- GCP VM (e2-medium): ~$25/month
- Cloud Storage (backups): ~$5/month
- Network egress: ~$2/month
- **Total: ~$32/month**

**vs Looker Studio Alternative:**
- Looker licensing: Variable (potentially $0-$100s/month)
- Limited API capabilities
- Less programmatic control

**ROI Calculation:**
- Development time: Same (5 weeks)
- Ongoing costs: Lower (~$32/month guaranteed)
- API capabilities: Superior (full programmatic control)
- **Conclusion: Metabase provides better value**

## Migration Path

**Future Considerations:**
- If user management becomes complex: Upgrade to Metabase Cloud or Enterprise
- If VM management overhead increases: Consider managed Metabase hosting
- If scale increases significantly: Move to Kubernetes deployment

**Current Recommendation:** Start with free self-hosted version, evaluate after 6 months of usage.

## Resources

**Official Documentation:**
- Metabase API: https://www.metabase.com/docs/latest/api-documentation.html
- Metabase Installation: https://www.metabase.com/docs/latest/operations-guide/installing-metabase.html
- BigQuery Integration: https://www.metabase.com/docs/latest/administration-guide/databases/bigquery.html

**Internal Documentation:**
- Deployment guide: `/docs/deployment/metabase-deployment.md`
- API scripts: `/scripts/metabase/` (to be created)
- User stories: `/docs/stories/6.*.md`
