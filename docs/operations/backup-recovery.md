# Backup and Disaster Recovery Procedures

## 🎯 Purpose
Comprehensive backup and disaster recovery procedures to ensure business continuity and data protection.

## 🔄 Recovery Time Objectives (RTO)
- **Critical System Recovery**: 2 hours
- **Full Data Recovery**: 4 hours
- **Dashboard Restoration**: 1 hour
- **Pipeline Restoration**: 30 minutes

## 💾 Recovery Point Objectives (RPO)
- **Transaction Data**: 24 hours (daily pipeline)
- **Configuration Data**: 1 hour (version controlled)
- **User Mappings**: 1 hour (Google Sheets sync)

---

## 📦 Backup Components

### 1. Data Backups

#### BigQuery Automatic Backups
**Coverage**: All tables and views
**Retention**: 7 days automatic, 90 days manual snapshots
**Location**: Multi-region (US)

**Manual Snapshot Creation**:
```bash
# Create table snapshots
bq cp ai_usage_analytics.fct_usage_daily ai_usage_analytics.fct_usage_daily_backup_$(date +%Y%m%d)
bq cp ai_usage_analytics.fct_cost_daily ai_usage_analytics.fct_cost_daily_backup_$(date +%Y%m%d)

# Create dataset backup
bq extract --destination_format=AVRO ai_usage_analytics.fct_usage_daily gs://your-backup-bucket/backups/usage_daily_$(date +%Y%m%d).avro
```

#### Google Sheets Backup
**Coverage**: API key mappings
**Method**: Automated export to Cloud Storage
**Frequency**: Daily

```bash
# Manual backup
python scripts/backup_sheets.py --output-path=gs://backup-bucket/sheets/mappings_$(date +%Y%m%d).csv
```

### 2. Configuration Backups

#### Infrastructure as Code
**Coverage**: Terraform configurations, Cloud Run configs
**Location**: Git repository
**Retention**: Indefinite (version controlled)

#### Secret Manager
**Coverage**: API keys, service account keys
**Method**: Encrypted backups
**Retention**: 90 days

```bash
# Backup secrets (encrypted)
gcloud secrets versions list cursor-api-key --format="value(name)" | head -1 | \
  xargs gcloud secrets versions access > cursor-key-backup-$(date +%Y%m%d).enc
```

### 3. Application Code
**Coverage**: Complete source code
**Location**: Git repository with CI/CD history
**Retention**: Indefinite

---

## 🚨 Disaster Recovery Scenarios

### Scenario 1: Complete BigQuery Dataset Loss

#### Impact Assessment
- **Severity**: Critical
- **Business Impact**: All analytics unavailable
- **Data Loss**: Up to 7 days (depends on backup age)

#### Recovery Steps

1. **Immediate Response** (0-15 minutes):
   ```bash
   # Stop all data ingestion
   gcloud scheduler jobs pause daily-usage-analytics --location=us-central1

   # Assess damage scope
   bq ls ai_usage_analytics 2>/dev/null || echo "Dataset not found"
   ```

2. **Restore Infrastructure** (15-60 minutes):
   ```bash
   # Recreate dataset
   bq mk --dataset --location=US your-project:ai_usage_analytics

   # Restore table schemas
   cd infrastructure/terraform
   terraform apply -var="project_id=your-project"

   # Recreate tables
   for sql_file in sql/tables/*.sql; do
     bq query --use_legacy_sql=false < "$sql_file"
   done
   ```

3. **Restore Data** (1-2 hours):
   ```bash
   # Restore from most recent backup
   BACKUP_DATE=$(date -d '1 day ago' +%Y%m%d)
   bq load --source_format=AVRO ai_usage_analytics.fct_usage_daily gs://backup-bucket/backups/usage_daily_$BACKUP_DATE.avro
   bq load --source_format=AVRO ai_usage_analytics.fct_cost_daily gs://backup-bucket/backups/cost_daily_$BACKUP_DATE.avro
   ```

4. **Recreate Views** (30 minutes):
   ```bash
   # Recreate analytics views
   for view_file in sql/views/*.sql; do
     sed "s/\${project_id}/your-project/g; s/\${dataset}/ai_usage_analytics/g" "$view_file" | \
     bq query --use_legacy_sql=false
   done
   ```

5. **Validate and Resume** (30 minutes):
   ```bash
   # Test data integrity
   bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `your-project.ai_usage_analytics.fct_usage_daily`'

   # Resume pipeline
   gcloud scheduler jobs resume daily-usage-analytics --location=us-central1
   ```

### Scenario 2: Cloud Run Service Failure

#### Impact Assessment
- **Severity**: High
- **Business Impact**: No new data ingestion
- **Data Loss**: None (data preserved in BigQuery)

#### Recovery Steps

1. **Immediate Response** (0-5 minutes):
   ```bash
   # Check service status
   gcloud run services describe ai-usage-analytics-pipeline --region=us-central1
   ```

2. **Redeploy Service** (5-15 minutes):
   ```bash
   # Quick redeploy from latest image
   gcloud run deploy ai-usage-analytics-pipeline \
     --image gcr.io/your-project/ai-usage-analytics-pipeline:latest \
     --region us-central1
   ```

3. **Alternative: Deploy from Source** (15-30 minutes):
   ```bash
   # Build and deploy fresh image
   docker build -t gcr.io/your-project/ai-usage-analytics-pipeline:recovery .
   docker push gcr.io/your-project/ai-usage-analytics-pipeline:recovery

   gcloud run deploy ai-usage-analytics-pipeline \
     --image gcr.io/your-project/ai-usage-analytics-pipeline:recovery \
     --region us-central1
   ```

4. **Validate Recovery** (5 minutes):
   ```bash
   # Test health endpoint
   curl -f https://your-service-url/health

   # Run test execution
   curl -X POST https://your-service-url/run-daily-job \
     -H "Content-Type: application/json" \
     -d '{"mode": "dry_run", "days": 1}'
   ```

### Scenario 3: API Key Compromise

#### Impact Assessment
- **Severity**: High (Security Risk)
- **Business Impact**: Potential unauthorized access
- **Data Loss**: None

#### Recovery Steps

1. **Immediate Response** (0-15 minutes):
   ```bash
   # Immediately revoke compromised keys
   # Cursor: Admin Portal → API Keys → Revoke
   # Anthropic: Console → API Keys → Delete

   # Generate emergency replacement keys
   # (Follow emergency key rotation procedures)
   ```

2. **Assess Impact** (15-30 minutes):
   ```bash
   # Check for unauthorized usage
   gcloud logs read 'jsonPayload.component="cursor_client" OR jsonPayload.component="anthropic_client"' \
     --since="72h" --format="value(jsonPayload)"

   # Review cost patterns for anomalies
   bq query --use_legacy_sql=false '
   SELECT usage_date, platform, SUM(input_tokens + output_tokens) as total_tokens
   FROM `your-project.ai_usage_analytics.fct_usage_daily`
   WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
   GROUP BY 1, 2 ORDER BY 1 DESC'
   ```

3. **Deploy New Keys** (30-45 minutes):
   ```bash
   # Update Secret Manager with new keys
   echo "new-emergency-cursor-key" | gcloud secrets versions add cursor-api-key --data-file=-
   echo "new-emergency-anthropic-key" | gcloud secrets versions add anthropic-api-key --data-file=-

   # Force pipeline restart to pick up new keys
   gcloud run services update ai-usage-analytics-pipeline --region=us-central1
   ```

4. **Monitor and Validate** (ongoing):
   ```bash
   # Monitor for successful pipeline execution
   gcloud logs tail 'resource.type=cloud_run_revision' --filter='jsonPayload.component="daily_job_orchestrator"'
   ```

---

## 🔄 Backup Procedures

### Daily Automated Backups

**BigQuery Tables** (Automated):
- Automatic 7-day retention
- Point-in-time recovery available
- Cross-region replication enabled

**Google Sheets** (Automated):
```bash
# Scheduled daily backup script
0 2 * * * /path/to/scripts/backup_sheets_daily.sh
```

### Weekly Manual Backups

**Complete System State**:
```bash
# Create weekly snapshot
BACKUP_DATE=$(date +%Y%m%d)

# Export all tables
bq extract ai_usage_analytics.fct_usage_daily gs://backup-bucket/weekly/usage_$BACKUP_DATE.avro
bq extract ai_usage_analytics.fct_cost_daily gs://backup-bucket/weekly/cost_$BACKUP_DATE.avro

# Backup configuration
tar -czf config_backup_$BACKUP_DATE.tar.gz infrastructure/ .github/ docs/

# Upload to Cloud Storage
gsutil cp config_backup_$BACKUP_DATE.tar.gz gs://backup-bucket/weekly/
```

### Monthly Archive Backups

**Long-term Retention**:
```bash
# Create monthly archive
ARCHIVE_DATE=$(date +%Y%m)

# Full data export
bq extract --destination_format=PARQUET ai_usage_analytics.fct_usage_daily gs://archive-bucket/monthly/usage_$ARCHIVE_DATE.parquet
bq extract --destination_format=PARQUET ai_usage_analytics.fct_cost_daily gs://archive-bucket/monthly/cost_$ARCHIVE_DATE.parquet

# Archive with 7-year retention
gsutil lifecycle set archive-lifecycle.json gs://archive-bucket
```

---

## ✅ Recovery Validation

### Post-Recovery Checklist

1. **Data Integrity**:
   - [ ] All tables contain expected row counts
   - [ ] Date ranges are complete (no gaps)
   - [ ] User attribution percentages match historical
   - [ ] Cost totals match known good values

2. **System Functionality**:
   - [ ] Pipeline executes successfully
   - [ ] All APIs respond to health checks
   - [ ] Dashboards load without errors
   - [ ] Data refresh indicators show current timestamp

3. **Security Validation**:
   - [ ] All API keys are functional and secure
   - [ ] Service account permissions are correct
   - [ ] No unauthorized access detected in logs
   - [ ] All secrets properly stored in Secret Manager

4. **Business Continuity**:
   - [ ] Finance team can access all dashboards
   - [ ] Reports generate with correct data
   - [ ] Cost allocation matches expectations
   - [ ] User can perform standard operations

### Recovery Testing

**Quarterly Recovery Drills**:
1. **Planned Outage**: Schedule 2-hour maintenance window
2. **Simulate Failure**: Disable critical component
3. **Execute Recovery**: Follow documented procedures
4. **Validate Results**: Complete post-recovery checklist
5. **Document Lessons**: Update procedures based on learnings

**Annual Full DR Test**:
1. **Complete System Rebuild**: Create parallel environment
2. **Data Migration**: Restore from backups
3. **End-to-End Testing**: Validate all functionality
4. **Performance Benchmarking**: Ensure acceptable performance
5. **Documentation Update**: Refine procedures based on test results