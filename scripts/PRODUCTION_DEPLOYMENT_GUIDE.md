# AI Usage Analytics Pipeline - Production Deployment Guide

This guide provides step-by-step instructions for deploying the AI Usage Analytics Pipeline to production and executing comprehensive validation.

## 📋 Prerequisites

### Required Access and Permissions
- **GCP Project**: Admin access to target GCP project
- **API Keys**: Valid API keys for Cursor and Anthropic services
- **Google Sheets**: Service account with access to attribution spreadsheet
- **GitHub**: Repository access for CI/CD configuration

### Required Tools
```bash
# Install required tools
gcloud components install alpha beta
pip install -r requirements.txt
```

### Environment Setup
```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  scheduler.googleapis.com
```

## 🚀 Deployment Process

### Phase 1: Secret Configuration

1. **Configure Production Secrets**
   ```bash
   ./scripts/setup_production_secrets.sh $PROJECT_ID
   ```

   This script will:
   - Enable Secret Manager API
   - Create required secrets interactively
   - Configure IAM permissions
   - Validate secret access

2. **Required Secrets**
   - `cursor-api-key`: Cursor API key for samba.tv organization
   - `anthropic-api-key`: Anthropic API key for usage/cost data
   - `sheets-service-account-key`: Google Sheets service account JSON

### Phase 2: Infrastructure Deployment

3. **Deploy BigQuery Schema**
   ```bash
   ./scripts/deploy_bigquery_schema.sh $PROJECT_ID ai_usage_analytics
   ```

   Validates deployment:
   ```bash
   ./scripts/validate_bigquery_deployment.sh $PROJECT_ID ai_usage_analytics
   ```

4. **Deploy Cloud Run Service**
   ```bash
   ./scripts/deploy_cloud_run.sh $PROJECT_ID
   ```

   This includes:
   - Docker image build and push
   - Blue-green deployment with health validation
   - Cloud Scheduler configuration
   - Traffic routing

### Phase 3: Production Validation

5. **Execute Comprehensive Validation**
   ```bash
   python scripts/validate_production_deployment.py \
     --project-id $PROJECT_ID \
     --service-url https://your-service-url \
     --output-file validation_report.json \
     --verbose
   ```

## 🧪 Validation Framework

### Validation Categories

#### 1. Secret Manager Validation
- ✅ All required secrets exist and accessible
- ✅ Service account permissions configured
- ✅ Secret values are valid format and length

#### 2. BigQuery Schema Validation
- ✅ Dataset and all tables exist
- ✅ All analytics views are valid
- ✅ Proper partitioning and clustering configured
- ✅ Performance meets < 5 second target

#### 3. Cloud Run Service Validation
- ✅ Health endpoints respond correctly
- ✅ Service configuration matches requirements
- ✅ Authentication and permissions working

#### 4. End-to-End Pipeline Validation
- ✅ Real API data ingestion (Cursor: 76+ users, Anthropic: token volumes)
- ✅ Data transformation and attribution working
- ✅ BigQuery insertion successful
- ✅ Pipeline execution within 2-hour SLA

#### 5. User Attribution Validation
- ✅ Google Sheets integration functional
- ✅ API key mapping working
- ✅ > 90% attribution coverage achieved

#### 6. Cloud Scheduler Validation
- ✅ Daily job configured correctly
- ✅ Authentication working
- ✅ Target URL pointing to production service

### Expected Data Volumes

Based on samba.tv organization requirements:

**Cursor API Data:**
- **Users**: 76+ active users expected
- **Data**: Daily usage metrics per user
- **Coverage**: All samba.tv email addresses

**Anthropic API Data:**
- **Input Tokens**: 118M+ expected
- **Output Tokens**: 5.4M+ expected
- **Records**: 606+ usage entries
- **Cost Attribution**: > 90% target coverage

**Performance Targets:**
- **Pipeline Execution**: < 2 hours end-to-end
- **Analytics Views**: < 5 seconds query response
- **API Error Rate**: < 5%
- **System Availability**: > 99.5%

## 📊 Production Monitoring

### Health Check Endpoints

```bash
# Service health
curl https://your-service-url/health

# Readiness check
curl https://your-service-url/ready

# Service status
curl https://your-service-url/status
```

### Manual Pipeline Trigger

```bash
# Execute pipeline manually
curl -X POST -H "Content-Type: application/json" \
  -d '{"mode":"production","days":1,"force":true}' \
  https://your-service-url/run-daily-job
```

### Analytics Views Testing

```sql
-- Test monthly finance view performance
SELECT COUNT(*) as record_count,
       MIN(cost_month) as earliest_data,
       MAX(cost_month) as latest_data
FROM `project.ai_usage_analytics.vw_monthly_finance`
LIMIT 100;

-- Test user attribution coverage
SELECT platform,
       COUNT(*) as total_records,
       COUNT(user_email) as attributed_records,
       SAFE_DIVIDE(COUNT(user_email), COUNT(*)) as attribution_rate
FROM `project.ai_usage_analytics.fct_cost_daily`
WHERE cost_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAYS)
GROUP BY platform;
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Secret Access Errors
```bash
# Check secret existence
gcloud secrets list --project=$PROJECT_ID

# Test secret access
gcloud secrets versions access latest \
  --secret="cursor-api-key" \
  --project=$PROJECT_ID
```

#### 2. BigQuery Permission Errors
```bash
# Check dataset permissions
bq show ai_usage_analytics

# Test BigQuery access
bq query --use_legacy_sql=false \
  "SELECT 1 as test"
```

#### 3. Cloud Run Deployment Issues
```bash
# Check service status
gcloud run services describe ai-usage-analytics-pipeline \
  --region=us-central1

# View service logs
gcloud logging read 'resource.type=cloud_run_revision' \
  --limit=50 \
  --format="table(timestamp,severity,textPayload)"
```

#### 4. API Authentication Issues
- Verify API keys are valid and have correct permissions
- Check that Cursor API key is for samba.tv organization
- Ensure Anthropic API key has usage data access
- Validate Google Sheets service account permissions

### Validation Failures

#### Pipeline Execution Fails
1. Check API connectivity and authentication
2. Verify BigQuery permissions
3. Review service logs for specific errors
4. Validate environment variable configuration

#### Attribution Coverage < 90%
1. Verify Google Sheets access and data
2. Check API key mapping completeness
3. Validate attribution logic in transformer
4. Review user email data quality

#### Performance Issues
1. Check BigQuery table partitioning
2. Review analytics view query complexity
3. Verify clustering configuration
4. Consider query optimization

## 📈 Post-Deployment Validation

### 72-Hour Autonomous Operation Test

After successful deployment, validate autonomous operation:

1. **Day 1**: Monitor first automated execution
2. **Day 2**: Validate data freshness and completeness
3. **Day 3**: Confirm error handling and recovery

```bash
# Monitor daily executions
gcloud scheduler jobs list --location=us-central1

# Check execution history
gcloud logging read 'resource.type=cloud_run_revision' \
  --filter='jsonPayload.message:"Pipeline execution"' \
  --limit=10
```

### Data Quality Validation

```sql
-- Check data freshness
SELECT
  MAX(ingest_date) as latest_ingest,
  DATE_DIFF(CURRENT_DATE(), MAX(ingest_date), DAY) as days_old
FROM `project.ai_usage_analytics.raw_cursor_usage`;

-- Validate data volumes
SELECT
  platform,
  COUNT(*) as records,
  MIN(usage_date) as earliest_date,
  MAX(usage_date) as latest_date
FROM `project.ai_usage_analytics.fct_usage_daily`
WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAYS)
GROUP BY platform;
```

## ✅ Production Readiness Checklist

### Pre-Deployment
- [ ] All secrets configured in Secret Manager
- [ ] BigQuery schema deployed and validated
- [ ] Cloud Run service deployed with health checks
- [ ] Cloud Scheduler configured for daily execution
- [ ] Service account permissions configured

### Validation
- [ ] End-to-end pipeline execution successful
- [ ] Real API data ingestion working (76+ users, token volumes)
- [ ] User attribution > 90% coverage achieved
- [ ] Analytics views performance < 5 seconds
- [ ] 72-hour autonomous operation validated

### Monitoring
- [ ] Health check endpoints responding
- [ ] Cloud logging configured and accessible
- [ ] Error alerting configured
- [ ] Performance metrics captured
- [ ] Data freshness monitoring active

### Documentation
- [ ] Production configuration documented
- [ ] Troubleshooting procedures available
- [ ] Runbook for operations team created
- [ ] Finance team training materials prepared

## 🚀 Go-Live Process

### Final Validation
```bash
# Run comprehensive validation
python scripts/validate_production_deployment.py \
  --project-id $PROJECT_ID \
  --service-url https://your-service-url \
  --output-file final_validation.json

# Generate validation report
echo "Production readiness: $(jq -r '.production_readiness.ready_for_production' final_validation.json)"
```

### Finance Team Handoff
1. **Dashboard Access**: Provide Looker Studio dashboard links
2. **Training**: Schedule training session on analytics views
3. **Documentation**: Provide user guides and troubleshooting
4. **Support**: Establish support process for data questions

### Ongoing Operations
- **Daily Monitoring**: Automated pipeline execution
- **Weekly Reviews**: Data quality and attribution coverage
- **Monthly Analysis**: Performance optimization opportunities
- **Quarterly Updates**: API integration health checks

---

## 📞 Support and Escalation

### Primary Contacts
- **DevOps Team**: Pipeline infrastructure and deployment
- **Data Team**: Analytics views and data quality
- **Finance Team**: Business requirements and dashboard usage

### Escalation Process
1. **Level 1**: Check automated monitoring and health endpoints
2. **Level 2**: Review service logs and error patterns
3. **Level 3**: Engage development team for code issues
4. **Level 4**: Vendor support for API integration issues

For additional support, refer to the operational runbooks and monitoring dashboards.