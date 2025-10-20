# Claude Data Ingestion - Cloud Run Deployment Guide

Complete guide for deploying the Claude data ingestion pipeline to Google Cloud Run.

---

## Prerequisites

1. **Google Cloud CLI** installed and authenticated
   ```bash
   gcloud auth login
   gcloud config set project ai-workflows-459123
   ```

2. **Docker** installed and running
   ```bash
   docker --version
   ```

3. **Permissions**: You must have the following roles:
   - Cloud Run Admin
   - Secret Manager Admin
   - BigQuery Admin
   - Service Account Admin
   - Cloud Scheduler Admin

---

## Deployment Steps

### Step 1: Setup IAM (One-time)

This creates service accounts and grants necessary permissions.

```bash
cd infrastructure/cloud_run
./setup-iam.sh
```

**What this does:**
- Creates `ai-usage-pipeline` service account (for Cloud Run job)
- Creates `ai-usage-scheduler` service account (for Cloud Scheduler)
- Grants Secret Manager access (anthropic-admin-api-key)
- Grants BigQuery permissions (dataEditor + jobUser)
- Grants Cloud Run Invoker role

**Verify:**
```bash
# Check Secret Manager access
gcloud secrets get-iam-policy anthropic-admin-api-key --project=ai-workflows-459123

# Check service accounts
gcloud iam service-accounts list --project=ai-workflows-459123
```

---

### Step 2: Build and Deploy Cloud Run Job

This builds the Docker image and deploys to Cloud Run.

```bash
cd infrastructure/cloud_run
./deploy-claude-ingestion.sh
```

**What this does:**
- Builds Docker image from `Dockerfile.claude-ingestion`
- Pushes image to Google Container Registry
- Creates Cloud Run job `claude-data-ingestion`
- Configures environment variables
- Sets resource limits (512Mi memory, 1 CPU, 15min timeout)

**Verify:**
```bash
# Check job exists
gcloud run jobs describe claude-data-ingestion --region=us-central1

# Test manual execution
gcloud run jobs execute claude-data-ingestion --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=claude-data-ingestion" --limit=50 --format=json
```

---

### Step 3: Setup Daily Scheduler

This creates a Cloud Scheduler job to run daily at 6 AM PT.

```bash
cd infrastructure/cloud_run
./setup-scheduler.sh
```

**What this does:**
- Creates Cloud Scheduler HTTP job
- Schedule: `0 14 * * *` (6 AM PT / 14:00 UTC)
- Configures OAuth authentication with scheduler service account
- Sets retry policy (3 attempts, 1 hour max duration)

**Verify:**
```bash
# Check scheduler job
gcloud scheduler jobs describe claude-daily-ingestion --location=us-central1

# Trigger manually to test
gcloud scheduler jobs run claude-daily-ingestion --location=us-central1

# View scheduler logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit=20
```

---

## Architecture

```
┌─────────────────┐      Daily at 6 AM PT
│ Cloud Scheduler │──────────────────┐
└─────────────────┘                  │
                                     ↓
                            ┌────────────────┐
                            │  Cloud Run Job │
                            │  (15min max)   │
                            └────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
           ┌─────────────┐  ┌──────────────┐  ┌──────────┐
           │ Secret Mgr  │  │ Claude Admin │  │ BigQuery │
           │ (API Key)   │  │     API      │  │ 3 Tables │
           └─────────────┘  └──────────────┘  └──────────┘
```

---

## Configuration

### Environment Variables (Cloud Run Job)

| Variable | Value | Description |
|----------|-------|-------------|
| `ANTHROPIC_ORGANIZATION_ID` | `1233d3ee-9900-424a-a31a-fb8b8dcd0be3` | Claude org ID |
| `BIGQUERY_PROJECT_ID` | `ai-workflows-459123` | GCP project |
| `BIGQUERY_DATASET` | `ai_usage_analytics` | BigQuery dataset |

### Resource Limits

| Resource | Value | Reason |
|----------|-------|--------|
| Memory | 512Mi | Lightweight ingestion |
| CPU | 1 | Single-threaded script |
| Timeout | 15m | Daily ingestion ~2-5 min |
| Max Retries | 3 | Handle transient failures |

---

## Monitoring

### Cloud Logging Queries

**View ingestion logs:**
```bash
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=claude-data-ingestion" \
  --limit=100 \
  --format="table(timestamp,severity,textPayload)"
```

**Filter for errors only:**
```bash
gcloud logging read \
  "resource.type=cloud_run_job AND severity>=ERROR" \
  --limit=50
```

**Check scheduler execution:**
```bash
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=claude-daily-ingestion" \
  --limit=20
```

### BigQuery Validation

**Check latest ingestion:**
```sql
SELECT
  MAX(activity_date) as latest_date,
  MAX(ingestion_timestamp) as last_run,
  COUNT(DISTINCT activity_date) as total_days,
  SUM(amount_usd) as total_cost
FROM `ai_usage_analytics.claude_costs`;
```

**Verify no gaps in dates:**
```sql
WITH expected AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY('2025-01-01', CURRENT_DATE() - 1)) as date
)
SELECT
  e.date as missing_date
FROM expected e
LEFT JOIN (SELECT DISTINCT activity_date FROM `ai_usage_analytics.claude_costs`) c
  ON e.date = c.activity_date
WHERE c.activity_date IS NULL
ORDER BY e.date;
```

---

## Troubleshooting

### Issue: Job fails with "Permission Denied" on Secret Manager

**Cause**: Service account doesn't have secretAccessor role

**Fix:**
```bash
gcloud secrets add-iam-policy-binding anthropic-admin-api-key \
  --member="serviceAccount:ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: Job fails with BigQuery "Access Denied"

**Cause**: Service account doesn't have BigQuery permissions

**Fix:**
```bash
gcloud projects add-iam-policy-binding ai-workflows-459123 \
  --member="serviceAccount:ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

### Issue: Scheduler doesn't trigger job

**Cause**: Scheduler SA can't invoke Cloud Run

**Fix:**
```bash
gcloud run jobs add-iam-policy-binding claude-data-ingestion \
  --region=us-central1 \
  --member="serviceAccount:ai-usage-scheduler@ai-workflows-459123.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Issue: Job timeout (15 minutes exceeded)

**Cause**: API rate limiting or network issues

**Fix:** Increase timeout:
```bash
gcloud run jobs update claude-data-ingestion \
  --region=us-central1 \
  --task-timeout=30m
```

---

## Updating the Pipeline

### Update Code Only

```bash
cd infrastructure/cloud_run
./deploy-claude-ingestion.sh
```

This rebuilds and redeploys with new code.

### Update Environment Variables

```bash
gcloud run jobs update claude-data-ingestion \
  --region=us-central1 \
  --set-env-vars=NEW_VAR=value
```

### Update Schedule

```bash
gcloud scheduler jobs update http claude-daily-ingestion \
  --location=us-central1 \
  --schedule="0 10 * * *"  # Example: Change to 2 AM PT
```

---

## Rollback

### Rollback to Previous Image

```bash
# List previous images
gcloud container images list-tags gcr.io/ai-workflows-459123/claude-data-ingestion

# Deploy specific version
gcloud run jobs update claude-data-ingestion \
  --region=us-central1 \
  --image=gcr.io/ai-workflows-459123/claude-data-ingestion:TAG
```

### Disable Scheduler (Emergency)

```bash
gcloud scheduler jobs pause claude-daily-ingestion --location=us-central1
```

### Re-enable Scheduler

```bash
gcloud scheduler jobs resume claude-daily-ingestion --location=us-central1
```

---

## Cost Estimation

| Resource | Cost | Notes |
|----------|------|-------|
| Cloud Run | ~$0.05/day | 512Mi × 5min/day |
| Cloud Scheduler | $0.10/month | 1 job × 30 runs |
| Container Registry | ~$0.50/month | Storage for images |
| **Total** | **~$2/month** | Very low cost |

---

## Security Best Practices

1. **Rotate API Key**: Rotate Anthropic API key quarterly
2. **Least Privilege**: Service accounts have minimal required permissions
3. **No Public Access**: Cloud Run job is private (not HTTP endpoint)
4. **Audit Logs**: Enable Cloud Audit Logging for all services
5. **VPC Service Controls**: Consider for production (optional)

---

## Next Steps After Deployment

1. Monitor first scheduled run (next 6 AM PT)
2. Set up alerting for failures (Cloud Monitoring)
3. Create dashboard in Metabase using new tables
4. Document runbook for on-call engineers

---

**Deployment Complete!** 🎉

Your Claude data ingestion pipeline is now running automatically every day at 6 AM PT.
