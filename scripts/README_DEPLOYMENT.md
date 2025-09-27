# BigQuery Schema Deployment Guide

This guide covers the deployment of the AI Usage Analytics BigQuery schema to production.

## Quick Start

```bash
# Deploy to production
./scripts/deploy_bigquery_schema.sh your-project-id ai_usage_analytics

# Validate deployment
./scripts/validate_bigquery_deployment.sh your-project-id ai_usage_analytics
```

## Prerequisites

1. **Google Cloud CLI** installed and authenticated
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **BigQuery CLI** available (included with gcloud)

3. **Required permissions:**
   - BigQuery Data Editor
   - BigQuery Job User
   - Project Viewer

## Deployment Process

### 1. Schema Deployment

The deployment script performs these steps:

1. **Validation**: Checks prerequisites and project access
2. **Dataset Creation**: Creates the BigQuery dataset if it doesn't exist
3. **Table Deployment**: Deploys 7 tables in dependency order:
   - Raw tables: `raw_cursor_usage`, `raw_anthropic_usage`, `raw_anthropic_cost`
   - Dimension tables: `dim_users`, `dim_api_keys`
   - Fact tables: `fct_usage_daily`, `fct_cost_daily`
4. **View Deployment**: Deploys 4+ analytics views:
   - `vw_monthly_finance`
   - `vw_productivity_metrics`
   - `vw_cost_allocation`
   - `vw_executive_summary`
5. **Verification**: Validates all components are deployed correctly
6. **Governance**: Applies data retention and access policies

### 2. Template Substitution

The scripts automatically substitute these template variables:
- `${project_id}` → Your actual GCP project ID
- `${dataset}` → Your dataset name (default: `ai_usage_analytics`)
- `ai_usage.` → `your-project.your-dataset.`

### 3. Performance Configuration

Automatically configured:
- **Partitioning**: Date-based partitioning on `ingest_date`, `usage_date`, `cost_date`
- **Clustering**: Optimized for common query patterns (email, platform, user_id)
- **Retention**: 2-year retention for raw data, 5-year for aggregated data

## Usage Examples

### Standard Deployment
```bash
./scripts/deploy_bigquery_schema.sh my-analytics-project
```

### Custom Dataset Name
```bash
./scripts/deploy_bigquery_schema.sh my-project custom_dataset_name
```

### Validation Only
```bash
./scripts/validate_bigquery_deployment.sh my-project ai_usage_analytics
```

## Validation Reports

The validation script generates several reports in `test_results/`:

- `deployment_summary.md`: Complete deployment overview
- `table_validation.json`: Table structure validation
- `performance_report.txt`: Query performance analysis
- `governance_report.txt`: Data governance compliance

## Troubleshooting

### Common Issues

1. **Authentication Error**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. **Permission Denied**
   - Ensure you have BigQuery Data Editor role
   - Check project permissions

3. **Template Substitution Failed**
   - Verify project ID is correct
   - Check dataset naming conventions

4. **View Syntax Errors**
   - Check that all referenced tables exist
   - Verify template variables were substituted correctly

### Rollback Procedures

If deployment fails:

1. **Check logs** in the deployment script output
2. **Manual cleanup** if needed:
   ```bash
   # Delete dataset (WARNING: This removes all data)
   bq rm -r -f your-project:ai_usage_analytics
   ```
3. **Re-run deployment** after fixing issues

## Post-Deployment Steps

1. **Configure Service Account** for Looker Studio:
   ```bash
   # Grant viewer permissions to your Looker Studio service account
   bq add-iam-policy-binding \
     --member="serviceAccount:looker-studio@your-project.iam.gserviceaccount.com" \
     --role="roles/bigquery.dataViewer" \
     your-project:ai_usage_analytics
   ```

2. **Test Data Ingestion**:
   - Run your data pipeline
   - Verify data appears in raw tables
   - Check that fact tables are populated

3. **Dashboard Connection**:
   - Connect Looker Studio to the views
   - Test dashboard functionality
   - Verify data freshness

4. **Monitoring Setup**:
   - Set up BigQuery monitoring
   - Configure cost alerts
   - Set up data freshness alerts

## Schema Management

### Adding New Tables
1. Create SQL file in `sql/tables/`
2. Add to deployment script table list
3. Update validation script

### Modifying Views
1. Update SQL file in `sql/views/`
2. Re-run deployment (views are CREATE OR REPLACE)
3. Test with validation script

### Schema Updates
- Use BigQuery schema evolution features
- Test in development environment first
- Consider backward compatibility

## Security Considerations

- Views only expose aggregated data, not raw usage details
- User email is hashed in fact tables for privacy
- Access controls enforced at BigQuery level
- Audit logs available through Cloud Logging

## Performance Optimization

The schema is optimized for:
- **Finance queries**: Month-over-month cost analysis
- **Usage analytics**: Daily/weekly usage patterns
- **Executive dashboards**: High-level KPI summaries
- **Compliance reporting**: User activity auditing

Expected query performance: < 5 seconds for dashboard queries