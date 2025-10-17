# Cloud Shell Deployment Commands

## Step 1: Open Google Cloud Shell
1. Go to https://console.cloud.google.com
2. Click the Cloud Shell icon `>_` in the top-right corner
3. Wait for Cloud Shell to initialize

## Step 2: Clone Repository

```bash
git clone https://github.com/the-sid-dani/samba-ai-usage-stats.git
cd samba-ai-usage-stats
gcloud config set project ai-workflows-459123
```

## Step 3: Deploy Flask Application

### Option A: Source-based Deployment (Try First - Bypasses Storage Constraint)

```bash
gcloud run deploy ai-usage-analytics-pipeline \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 10 \
  --concurrency 1 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=ai-workflows-459123,ENVIRONMENT=production,BIGQUERY_DATASET=ai_usage_analytics,LOG_LEVEL=INFO,DEBUG=false" \
  --port 8080 \
  --service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com
```

### Option B: Container Build Method (If Option A Fails)

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/ai-workflows-459123/ai-usage-analytics/pipeline:latest .
```

```bash
gcloud run deploy ai-usage-analytics-pipeline \
  --image us-central1-docker.pkg.dev/ai-workflows-459123/ai-usage-analytics/pipeline:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 10 \
  --concurrency 1 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=ai-workflows-459123,ENVIRONMENT=production,BIGQUERY_DATASET=ai_usage_analytics,LOG_LEVEL=INFO,DEBUG=false" \
  --port 8080 \
  --service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com
```

## Step 4: Test Deployment

```bash
curl https://ai-usage-analytics-pipeline-201626763325.us-central1.run.app/health
```

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"mode":"production","days":1}' \
  https://ai-usage-analytics-pipeline-201626763325.us-central1.run.app/run-daily-job
```

## Step 5: Set Up Daily Scheduler

```bash
gcloud scheduler jobs create http daily-usage-analytics \
  --location=us-central1 \
  --schedule="0 6 * * *" \
  --uri="https://ai-usage-analytics-pipeline-201626763325.us-central1.run.app/run-daily-job" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"mode": "production", "days": 1}' \
  --oidc-service-account-email=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com \
  --oidc-token-audience="https://ai-usage-analytics-pipeline-201626763325.us-central1.run.app" \
  --time-zone="America/Los_Angeles" \
  --description="Daily AI usage analytics data pipeline" \
  --max-retry-attempts=3 \
  --max-retry-duration=600s
```

## Expected Results

After successful deployment:
- Health check returns JSON with service status
- Pipeline execution returns execution results
- Daily scheduler configured for 6 AM PST
- Full production system operational

## Timeline
- Build: 5-10 minutes
- Deploy: 2-3 minutes
- Total: ~15 minutes