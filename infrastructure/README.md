# Production Deployment Guide

## Overview

This directory contains all infrastructure and deployment configurations for the AI Usage Analytics Pipeline production environment.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Cloud Scheduler │───▶│   Cloud Run      │───▶│   BigQuery      │
│  (Daily 6AM)    │    │   (Pipeline)     │    │  (Data Store)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ External APIs    │
                       │ • Cursor API     │
                       │ • Anthropic API  │
                       │ • Google Sheets  │
                       └──────────────────┘
```

## Components

### 1. Cloud Run Service
- **Image**: `gcr.io/{project-id}/ai-usage-analytics-pipeline`
- **Memory**: 1GB
- **CPU**: 1 vCPU
- **Timeout**: 1 hour
- **Concurrency**: 10 requests
- **Auto-scaling**: 0-10 instances

### 2. Cloud Scheduler
- **Schedule**: Daily at 6 AM PST
- **Trigger**: HTTP POST to Cloud Run service
- **Retry**: 3 attempts with exponential backoff
- **Timeout**: 10 minutes

### 3. BigQuery Infrastructure
- **Dataset**: `ai_usage_analytics`
- **Location**: US (multi-region)
- **Tables**: 7 fact and dimension tables
- **Views**: 4 analytics views for Looker Studio

### 4. Secret Manager
- **Secrets**: API keys and service account credentials
- **Access**: Limited to pipeline service account
- **Rotation**: Manual (recommend quarterly)

## Deployment Methods

### Method 1: Automated GitHub Actions (Recommended)

1. **Setup Repository Secrets**:
   ```bash
   # Required secrets in GitHub repository:
   GCP_PROJECT_ID=your-project-id
   GCP_SERVICE_ACCOUNT_KEY={"type":"service_account",...}
   CLOUD_RUN_SERVICE_ACCOUNT=ai-usage-pipeline@your-project.iam.gserviceaccount.com
   CLOUD_SCHEDULER_SERVICE_ACCOUNT=ai-usage-scheduler@your-project.iam.gserviceaccount.com
   CLOUD_RUN_HASH=unique-hash-for-url
   ```

2. **Trigger Deployment**:
   - Push to `main` branch triggers automatic deployment
   - Manual deployment via GitHub Actions UI

### Method 2: Manual Script Deployment

1. **Prerequisites**:
   ```bash
   # Install and authenticate gcloud CLI
   gcloud auth login
   gcloud auth application-default login

   # Install Docker
   docker --version
   ```

2. **Deploy**:
   ```bash
   ./scripts/deploy.sh production your-project-id
   ```

### Method 3: Terraform Infrastructure as Code

1. **Initialize Terraform**:
   ```bash
   cd infrastructure/terraform
   terraform init
   ```

2. **Plan and Apply**:
   ```bash
   terraform plan -var="project_id=your-project-id"
   terraform apply -var="project_id=your-project-id"
   ```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | Yes | - |
| `ENVIRONMENT` | Environment name | Yes | production |
| `BIGQUERY_DATASET` | BigQuery dataset name | Yes | ai_usage_analytics |
| `LOG_LEVEL` | Logging level | No | INFO |
| `DEBUG` | Debug mode | No | false |

### Secrets Configuration

1. **Create API Key Secrets**:
   ```bash
   # Cursor API Key
   echo "your-cursor-api-key" | gcloud secrets create cursor-api-key --data-file=-

   # Anthropic API Key
   echo "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-

   # Google Sheets Service Account
   gcloud secrets create sheets-service-account-key --data-file=path/to/service-account.json
   ```

2. **Grant Access**:
   ```bash
   # Grant pipeline service account access to secrets
   gcloud secrets add-iam-policy-binding cursor-api-key \
       --member="serviceAccount:ai-usage-pipeline@your-project.iam.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

## Monitoring and Alerting

### Cloud Logging

View logs:
```bash
# Pipeline logs
gcloud logs read 'resource.type=cloud_run_revision AND resource.labels.service_name=ai-usage-analytics-pipeline' --limit=50

# Error logs only
gcloud logs read 'resource.type=cloud_run_revision AND severity>=ERROR' --limit=20
```

### Cloud Monitoring

Key metrics to monitor:
- Pipeline execution success rate
- Processing time (target: <10 minutes)
- Data freshness (target: <24 hours)
- Cost variance (alert if >20% increase)
- API error rates

### Health Checks

- **Endpoint**: `https://your-service-url/health`
- **Frequency**: Every 30 seconds
- **Timeout**: 10 seconds
- **Failure Threshold**: 3 consecutive failures

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify service account has required IAM roles
   - Check Secret Manager permissions
   - Ensure API keys are properly stored

2. **BigQuery Errors**:
   - Verify dataset exists and is accessible
   - Check table schemas match expected format
   - Ensure proper BigQuery IAM roles

3. **Memory/Timeout Issues**:
   - Increase memory allocation in Cloud Run
   - Reduce batch size for large datasets
   - Check for memory leaks in processing logic

4. **API Rate Limiting**:
   - Verify retry logic is working
   - Check API key quotas and limits
   - Consider implementing circuit breaker pattern

### Debug Commands

```bash
# Test pipeline locally
python -m src.orchestration.daily_job --mode dry_run --days 1

# Check service health
curl -X GET https://your-service-url/health

# Run manual pipeline execution
curl -X POST https://your-service-url/run-daily-job \
  -H "Content-Type: application/json" \
  -d '{"mode": "development", "days": 1}'

# View recent BigQuery data
bq query --use_legacy_sql=false \
  'SELECT * FROM `your-project.ai_usage_analytics.fct_usage_daily`
   WHERE usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
   LIMIT 10'
```

## Security Considerations

1. **Least Privilege Access**: Service accounts have minimal required permissions
2. **Secret Management**: All sensitive data stored in Secret Manager
3. **Network Security**: VPC egress restrictions for external API calls
4. **Audit Logging**: All API calls and data access logged
5. **Data Encryption**: At-rest and in-transit encryption enabled

## Cost Optimization

1. **Auto-scaling**: Cloud Run scales to zero when idle
2. **Batch Processing**: 1000-record batches optimize BigQuery costs
3. **Partition Pruning**: Date-based queries reduce scan costs
4. **Efficient Queries**: Views optimized for dashboard access patterns

## Backup and Recovery

1. **Data Backup**: BigQuery automatic backups (7-day retention)
2. **Code Backup**: Git repository with CI/CD history
3. **Configuration Backup**: Terraform state stored in Cloud Storage
4. **Recovery Time**: <2 hours for complete system restore

## Maintenance

### Regular Tasks (Monthly)
- Review and rotate API keys
- Check cost trends and optimize queries
- Update dependencies and security patches
- Validate data quality metrics

### Quarterly Tasks
- Performance review and optimization
- Security audit and compliance check
- Disaster recovery testing
- User access review