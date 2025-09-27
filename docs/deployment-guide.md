# AI Usage Analytics - Deployment Guide

## 🎯 Purpose
Step-by-step guide to deploy the AI Usage Analytics Dashboard from development to production.

## 📋 Prerequisites
Before starting deployment, ensure you have:
- [ ] GCP project with billing enabled
- [ ] Owner or Editor role on target GCP project
- [ ] Terraform CLI installed (`brew install terraform`)
- [ ] Google Cloud CLI installed and authenticated (`gcloud auth login`)
- [ ] Docker installed and running
- [ ] Cursor API key with admin access
- [ ] Anthropic API key with organization access
- [ ] Google Sheets service account key

## 🚀 Deployment Process

### Step 1: Validate Prerequisites

```bash
# Run prerequisite validation
./scripts/validate-deployment-prerequisites.sh YOUR_PROJECT_ID

# Expected: All checks pass with green ✅
# If any fail, follow the provided fix instructions
```

### Step 2: Execute Infrastructure Provisioning (Story 5.1)

```bash
# Navigate to Terraform directory
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan infrastructure (review before applying)
terraform plan -var="project_id=YOUR_PROJECT_ID"

# Apply infrastructure (creates all GCP resources)
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

**Expected Results:**
- BigQuery dataset: `ai_usage_analytics` created
- Service accounts: `ai-usage-pipeline@` and `ai-usage-scheduler@` created
- Secret Manager: 3 secrets created (empty, to be populated)
- IAM roles: Proper permissions assigned
- APIs: All required APIs enabled

### Step 3: Configure API Keys (Manual)

```bash
# Add Cursor API key
echo "YOUR_CURSOR_API_KEY" | gcloud secrets create cursor-api-key --data-file=-

# Add Anthropic API key
echo "YOUR_ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-

# Add Google Sheets service account key (JSON file)
gcloud secrets create sheets-service-account-key --data-file=path/to/service-account.json
```

### Step 4: Deploy BigQuery Schema (Story 5.2)

```bash
# Deploy tables
for sql_file in sql/tables/*.sql; do
    if [[ -f "$sql_file" && "$(basename "$sql_file")" != "create_all_tables.sql" ]]; then
        echo "Creating table from $sql_file"
        sed "s/\${project_id}/YOUR_PROJECT_ID/g; s/\${dataset}/ai_usage_analytics/g" "$sql_file" | \
        bq query --use_legacy_sql=false --project_id=YOUR_PROJECT_ID
    fi
done

# Deploy views
for view_file in sql/views/*.sql; do
    if [[ -f "$view_file" && "$(basename "$view_file")" != "create_all_views.sql" ]]; then
        echo "Creating view from $view_file"
        sed "s/\${project_id}/YOUR_PROJECT_ID/g; s/\${dataset}/ai_usage_analytics/g" "$view_file" | \
        bq query --use_legacy_sql=false --project_id=YOUR_PROJECT_ID
    fi
done
```

### Step 5: Deploy Cloud Run Service (Story 5.3)

```bash
# Build and push Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/ai-usage-analytics-pipeline .
docker push gcr.io/YOUR_PROJECT_ID/ai-usage-analytics-pipeline

# Deploy Cloud Run service
gcloud run deploy ai-usage-analytics-pipeline \
    --image gcr.io/YOUR_PROJECT_ID/ai-usage-analytics-pipeline \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 3600 \
    --max-instances 10 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,ENVIRONMENT=production,BIGQUERY_DATASET=ai_usage_analytics" \
    --service-account="ai-usage-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```

### Step 6: Configure Cloud Scheduler

```bash
# Get Cloud Run service URL
SERVICE_URL=$(gcloud run services describe ai-usage-analytics-pipeline --region=us-central1 --format="value(status.url)")

# Create daily scheduler job
gcloud scheduler jobs create http daily-usage-analytics \
    --location=us-central1 \
    --schedule="0 6 * * *" \
    --uri="$SERVICE_URL/run-daily-job" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"mode": "production", "days": 1}' \
    --oidc-service-account-email="ai-usage-scheduler@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --oidc-token-audience="$SERVICE_URL" \
    --time-zone="America/Los_Angeles"
```

### Step 7: Execute Production Validation (Story 5.4)

```bash
# Test health endpoint
curl -f "$SERVICE_URL/health"

# Run manual pipeline test
curl -X POST "$SERVICE_URL/run-daily-job" \
    -H "Content-Type: application/json" \
    -d '{"mode": "dry_run", "days": 1}'

# Test with real data (small date range)
curl -X POST "$SERVICE_URL/run-daily-job" \
    -H "Content-Type: application/json" \
    -d '{"mode": "production", "days": 1}'
```

## 🔍 Validation Checks

### Infrastructure Validation
```bash
# Check BigQuery dataset
bq ls --project_id=YOUR_PROJECT_ID

# Check service accounts
gcloud iam service-accounts list --project=YOUR_PROJECT_ID

# Check secrets
gcloud secrets list --project=YOUR_PROJECT_ID

# Check Cloud Run service
gcloud run services list --platform=managed --region=us-central1

# Check Cloud Scheduler
gcloud scheduler jobs list --location=us-central1
```

### Data Pipeline Validation
```bash
# Check BigQuery tables
bq ls ai_usage_analytics --project_id=YOUR_PROJECT_ID

# Test analytics views
bq query --use_legacy_sql=false --project_id=YOUR_PROJECT_ID \
  'SELECT COUNT(*) as table_count FROM `YOUR_PROJECT_ID.ai_usage_analytics.INFORMATION_SCHEMA.TABLES`'

# Check recent pipeline execution
gcloud logs read 'resource.type=cloud_run_revision AND jsonPayload.message:"Pipeline execution completed"' \
  --project=YOUR_PROJECT_ID --since="24h" --limit=5
```

## 🚨 Troubleshooting

### Common Issues

**Terraform Permission Errors:**
```bash
# Solution: Ensure your account has sufficient permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:your-email@company.com" \
    --role="roles/editor"
```

**Cloud Run Deployment Fails:**
```bash
# Solution: Check service account exists
gcloud iam service-accounts describe ai-usage-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Solution: Verify image was pushed correctly
gcloud container images list --repository=gcr.io/YOUR_PROJECT_ID
```

**BigQuery Table Creation Fails:**
```bash
# Solution: Check dataset exists
bq show --project_id=YOUR_PROJECT_ID ai_usage_analytics

# Solution: Verify permissions
bq query --use_legacy_sql=false 'SELECT 1' --project_id=YOUR_PROJECT_ID
```

## 📊 Success Criteria

✅ **Infrastructure Ready:** All Terraform resources created successfully
✅ **Services Deployed:** Cloud Run service responds to health checks
✅ **Data Layer Ready:** BigQuery tables and views accessible
✅ **Automation Configured:** Cloud Scheduler triggers pipeline
✅ **Real Data Flowing:** Pipeline ingests actual API data successfully

## 🔄 Rollback Procedures

**If deployment fails:**
```bash
# Rollback Cloud Run service
gcloud run services delete ai-usage-analytics-pipeline --region=us-central1

# Rollback infrastructure (careful - this deletes everything)
cd infrastructure/terraform
terraform destroy -var="project_id=YOUR_PROJECT_ID"

# Rollback BigQuery (if needed)
bq rm -r -f ai_usage_analytics
```

## 📞 Support

- **Documentation Issues:** Review docs/operations/
- **Infrastructure Problems:** Contact DevOps team
- **API Access Issues:** Contact platform administrators
- **Emergency:** Follow escalation procedures in runbook.md