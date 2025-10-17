# Alternative Deployment Methods

Since the storage constraint is blocking container builds, try these approaches:

## Option 1: Source-based Deployment (Try First)

```bash
cd samba-ai-usage-stats
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

## Option 2: Use Existing Service + Manual Pipeline

Since APIs are working and BigQuery is ready, run data ingestion manually:

```bash
# Test API connectivity
python test_apis_simple_standalone.py

# Manually trigger data pipeline (if working)
python -c "
import sys, os
sys.path.append('src')
from orchestration.daily_job import DailyJobOrchestrator
orchestrator = DailyJobOrchestrator()
result = orchestrator.run_daily_pipeline(days_back=1)
print(f'Pipeline result: {result.success}')
"
```

## Option 3: Work Around Storage Constraint

Ask your GCP admin to temporarily modify the organization policy:

1. Go to: IAM & Admin → Organization Policies
2. Find: `constraints/storage.softDeletePolicySeconds`
3. Temporarily disable or set to 0
4. Run deployment
5. Re-enable policy

## What's Already Working

✅ BigQuery data warehouse fully operational
✅ Both APIs (Cursor + Anthropic) returning real data
✅ Secret Manager with API keys configured
✅ Cloud Run service infrastructure deployed

## Expected Results

If Option 1 works, you'll get:
- Working Flask web application
- Health endpoints responding
- Manual pipeline execution capability
- Complete production system

Try Option 1 first - it might bypass the storage constraint!