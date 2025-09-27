# Troubleshooting Guide

## 🎯 Purpose
Extended troubleshooting scenarios and solutions for AI Usage Analytics Pipeline.

---

## 🚨 Critical Issues (Immediate Action Required)

### Complete Pipeline Failure

#### Symptoms
- No data updates for >24 hours
- All dashboards showing stale data
- Multiple API error alerts

#### Diagnosis Steps
1. **Check Cloud Run Service Status**:
   ```bash
   gcloud run services describe ai-usage-analytics-pipeline --region=us-central1
   ```

2. **Review Recent Logs**:
   ```bash
   gcloud logs read 'resource.type=cloud_run_revision' --since="24h" --limit=50
   ```

3. **Test Service Health**:
   ```bash
   curl -f https://your-service-url/health
   ```

#### Resolution Steps
1. **If Service Down**: Redeploy Cloud Run service
   ```bash
   gcloud run services replace infrastructure/cloud_run/service.yaml --region=us-central1
   ```

2. **If Authentication Issues**: Verify service account permissions
   ```bash
   gcloud projects get-iam-policy your-project-id --flatten="bindings[].members" --filter="bindings.members:ai-usage-pipeline@*"
   ```

3. **If API Issues**: Test individual APIs and rotate keys if needed

### Data Corruption Detected

#### Symptoms
- Negative values in cost/usage metrics
- Duplicate records in dashboards
- Attribution data inconsistencies

#### Diagnosis Steps
1. **Identify Scope**:
   ```sql
   -- Check for data anomalies
   SELECT
     usage_date,
     platform,
     COUNT(*) as record_count,
     SUM(CASE WHEN input_tokens < 0 OR output_tokens < 0 THEN 1 ELSE 0 END) as negative_values,
     COUNT(DISTINCT user_email) as unique_users
   FROM `project.ai_usage_analytics.fct_usage_daily`
   WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
   GROUP BY 1, 2
   ORDER BY 1 DESC;
   ```

2. **Check Pipeline Logs**:
   ```bash
   gcloud logs read 'jsonPayload.message:"validation failed" OR jsonPayload.message:"transformation error"' --since="7d"
   ```

#### Resolution Steps
1. **Stop Pipeline**: Disable Cloud Scheduler temporarily
2. **Backup Current Data**: Export affected tables
3. **Remove Corrupted Data**: Delete specific date ranges
4. **Re-run Pipeline**: For affected date ranges
5. **Validate Results**: Verify data integrity before re-enabling

---

## ⚠️ High Priority Issues (4-hour Response)

### BigQuery Query Performance Issues

#### Symptoms
- Dashboards loading >10 seconds
- Query timeout errors
- High BigQuery costs

#### Diagnosis Steps
1. **Check Query Performance**:
   ```sql
   -- Review slow queries
   SELECT
     job_id,
     query,
     total_bytes_processed,
     total_slot_ms,
     creation_time
   FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
   WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
     AND total_slot_ms > 1000000  -- Long-running queries
   ORDER BY creation_time DESC;
   ```

2. **Analyze View Performance**:
   ```bash
   # Test view query times
   time bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `project.ai_usage_analytics.vw_monthly_finance`'
   ```

#### Resolution Steps
1. **Optimize Date Filters**: Ensure views use partition pruning
2. **Update Clustering**: Add clustering on frequently filtered columns
3. **Consider Materialized Views**: For expensive aggregations
4. **Review Query Patterns**: Optimize Looker Studio filters

### Missing User Attribution

#### Symptoms
- Users showing as "Unknown" in dashboards
- Attribution coverage <80%
- Cost data without user assignment

#### Diagnosis Steps
1. **Check Google Sheets Access**:
   ```bash
   # Verify sheets service account permissions
   gcloud projects get-iam-policy your-project-id --flatten="bindings[].members" --filter="bindings.members:*sheets*"
   ```

2. **Review Unmapped Keys**:
   ```sql
   -- Find unmapped API keys
   SELECT DISTINCT
     api_key_id,
     platform,
     COUNT(*) as usage_count
   FROM `project.ai_usage_analytics.fct_usage_daily`
   WHERE user_email IS NULL
     AND usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
   GROUP BY 1, 2
   ORDER BY 3 DESC;
   ```

#### Resolution Steps
1. **Update Google Sheets**: Add missing user mappings
2. **Standardize Email Formats**: Ensure consistency across platforms
3. **Re-run Attribution**: For recent date ranges
4. **Validate Coverage**: Monitor attribution metrics

---

## 📊 Medium Priority Issues (Same Day Response)

### API Rate Limiting

#### Symptoms
- 429 (Too Many Requests) errors
- Incomplete data ingestion
- Extended pipeline execution times

#### Diagnosis Steps
1. **Review Rate Limit Logs**:
   ```bash
   gcloud logs read 'jsonPayload.message:"Rate limited"' --since="24h"
   ```

2. **Check API Call Frequency**:
   ```bash
   # Count API calls per hour
   gcloud logs read 'jsonPayload.message:"Making request"' --since="24h" | wc -l
   ```

#### Resolution Steps
1. **Implement Backoff**: Verify exponential backoff is working
2. **Reduce Concurrency**: Lower parallel API calls
3. **Contact Platform Support**: Request quota increases
4. **Optimize Date Ranges**: Use smaller chunks if needed

### Inconsistent Data Between Platforms

#### Symptoms
- User appears on one platform but not another
- Mismatched usage patterns
- Attribution inconsistencies

#### Diagnosis Steps
1. **Compare Platform Data**:
   ```sql
   -- Check user presence across platforms
   SELECT
     user_email,
     platform,
     COUNT(*) as days_active,
     SUM(sessions) as total_sessions
   FROM `project.ai_usage_analytics.fct_usage_daily`
   WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
     AND user_email IS NOT NULL
   GROUP BY 1, 2
   ORDER BY 1, 2;
   ```

2. **Review Attribution Logic**:
   - Check Google Sheets mapping completeness
   - Verify email format consistency
   - Look for platform-specific issues

#### Resolution Steps
1. **Standardize User Data**: Update email formats across platforms
2. **Complete Mappings**: Add missing platform-specific mappings
3. **Validate Cross-Platform**: Ensure users appear consistently
4. **Update Business Logic**: If attribution rules need refinement

---

## 🔧 Low Priority Issues (Next Business Day)

### Dashboard Display Issues

#### Chart Not Rendering
**Cause**: Data type mismatches, null values
**Solution**: Check view data types, handle nulls in SQL

#### Incorrect Calculations
**Cause**: Business logic errors in views
**Solution**: Review view SQL, test calculations manually

#### Slow Dashboard Loading
**Cause**: Large date ranges, complex filters
**Solution**: Add default filters, optimize view performance

### Data Quality Warnings

#### Future Dates in Data
**Cause**: API timezone issues, incorrect date parsing
**Solution**: Add date validation, fix timezone handling

#### Negative Values
**Cause**: Data corruption, calculation errors
**Solution**: Add validation rules, investigate data source

#### Duplicate Records
**Cause**: Pipeline re-runs, data ingestion issues
**Solution**: Add deduplication logic, fix pipeline idempotency

---

## 🛠️ Diagnostic Tools and Commands

### Pipeline Diagnostics

```bash
# Check pipeline execution history
gcloud logs read 'resource.type=cloud_run_revision AND jsonPayload.component="daily_job_orchestrator"' --since="7d" --format="value(jsonPayload.message)"

# Test individual components
python -c "
from src.ingestion.cursor_client import CursorClient
from src.ingestion.anthropic_client import AnthropicClient
cursor = CursorClient()
anthropic = AnthropicClient()
print('Cursor health:', cursor.health_check())
print('Anthropic health:', anthropic.health_check())
"

# Validate transformations
python -c "
from src.processing.multi_platform_transformer import MultiPlatformTransformer
transformer = MultiPlatformTransformer()
# Add validation tests here
"
```

### BigQuery Diagnostics

```sql
-- Check table sizes and growth
SELECT
  table_name,
  row_count,
  size_bytes,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_modified_time, HOUR) as hours_since_update
FROM `project.ai_usage_analytics.INFORMATION_SCHEMA.TABLE_STORAGE`
WHERE table_schema = 'ai_usage_analytics'
ORDER BY last_modified_time DESC;

-- Check data quality metrics
SELECT
  usage_date,
  platform,
  COUNT(*) as total_records,
  COUNT(DISTINCT user_email) as unique_users,
  AVG(CASE WHEN user_email IS NOT NULL THEN 1.0 ELSE 0.0 END) as attribution_rate
FROM `project.ai_usage_analytics.fct_usage_daily`
WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- Check for data anomalies
SELECT
  usage_date,
  platform,
  user_email,
  input_tokens,
  output_tokens,
  lines_of_code_added,
  lines_of_code_accepted
FROM `project.ai_usage_analytics.fct_usage_daily`
WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (
    input_tokens < 0 OR
    output_tokens < 0 OR
    lines_of_code_added < 0 OR
    lines_of_code_accepted < 0 OR
    lines_of_code_accepted > lines_of_code_added * 2
  )
ORDER BY usage_date DESC;
```

### API Diagnostics

```bash
# Test Cursor API directly
curl -X POST https://api.cursor.com/teams/daily-usage-data \
  -u "$(gcloud secrets versions access latest --secret=cursor-api-key):" \
  -H "Content-Type: application/json" \
  -d "{\"startDate\": $(date -d '1 day ago' +%s)000, \"endDate\": $(date +%s)000}"

# Test Anthropic API directly
curl -X GET "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=$(date -d '1 day ago' +%Y-%m-%d)&ending_at=$(date +%Y-%m-%d)" \
  -H "x-api-key: $(gcloud secrets versions access latest --secret=anthropic-api-key)" \
  -H "anthropic-version: 2023-06-01"

# Test Google Sheets access
python -c "
from src.ingestion.sheets_client import GoogleSheetsClient
client = GoogleSheetsClient()
mappings = client.get_api_key_mappings()
print(f'Retrieved {len(mappings)} mappings')
"
```

---

## 📋 Issue Escalation Matrix

### Level 1: Self-Service (Finance Team)
**Scope**: Dashboard navigation, report generation, data interpretation
**Resources**: User Guide, Dashboard help, FAQ
**Resolution Time**: Immediate

### Level 2: Operations Support (Data Engineering)
**Scope**: Data quality, API key management, minor configuration
**Contact**: data-engineering@company.com, #ai-analytics-support
**Resolution Time**: 4 hours response, 24 hours resolution

### Level 3: Technical Support (Platform Engineering)
**Scope**: Infrastructure, security, major system issues
**Contact**: platform-team@company.com, #platform-emergency
**Resolution Time**: 1 hour response, 8 hours resolution

### Level 4: Emergency Escalation
**Scope**: Security breaches, data loss, business-critical failures
**Contact**: Director of Engineering, CTO
**Resolution Time**: Immediate response, 4 hours resolution

---

## 📚 Reference Materials

### Log Message Patterns

**Success Patterns**:
- `"Pipeline execution completed successfully"`
- `"Successfully retrieved X records"`
- `"Health check passed"`

**Warning Patterns**:
- `"Rate limited, waiting"`
- `"Validation warning"`
- `"Attribution coverage below target"`

**Error Patterns**:
- `"API request failed"`
- `"Pipeline execution failed"`
- `"Critical error detected"`

### Common Error Codes

| Code | Component | Meaning | Action |
|------|-----------|---------|--------|
| CURSOR_API_ERROR | Cursor Client | API authentication/access issue | Check API key, verify permissions |
| ANTHROPIC_API_ERROR | Anthropic Client | API authentication/access issue | Check API key, verify permissions |
| BIGQUERY_INSERT_ERROR | Storage | BigQuery insertion failure | Check table schema, verify permissions |
| TRANSFORMATION_ERROR | Processing | Data transformation failure | Review input data quality |
| SHEETS_ERROR | Sheets Client | Google Sheets access issue | Check service account permissions |

### Quick Reference Commands

```bash
# View pipeline status
gcloud run services list --filter="ai-usage-analytics-pipeline"

# Check scheduler job
gcloud scheduler jobs list --location=us-central1

# View recent errors
gcloud logs read 'severity>=ERROR' --since="24h" --limit=20

# Test pipeline manually
curl -X POST https://your-service-url/run-daily-job \
  -H "Content-Type: application/json" \
  -d '{"mode": "development", "days": 1}'

# Check BigQuery table status
bq ls ai_usage_analytics

# View recent data
bq query --use_legacy_sql=false \
  'SELECT * FROM `project.ai_usage_analytics.fct_usage_daily`
   WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
   ORDER BY usage_date DESC LIMIT 10'
```