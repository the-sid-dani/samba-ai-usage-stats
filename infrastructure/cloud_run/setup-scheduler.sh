#!/bin/bash
set -e

# Claude Data Ingestion - Cloud Scheduler Setup
# Creates a daily scheduler job to run at 6 AM PT (14:00 UTC)

PROJECT_ID="ai-workflows-459123"
REGION="us-central1"
JOB_NAME="claude-daily-ingestion"
CLOUD_RUN_JOB="claude-data-ingestion"

echo "================================================"
echo "Claude Data Ingestion - Cloud Scheduler Setup"
echo "================================================"

# Step 1: Verify Cloud Run job exists
echo ""
echo "Step 1: Verifying Cloud Run job exists..."
gcloud run jobs describe ${CLOUD_RUN_JOB} --region=${REGION} --project=${PROJECT_ID}

# Step 2: Create scheduler job (or update if exists)
echo ""
echo "Step 2: Creating Cloud Scheduler job..."
gcloud scheduler jobs create http ${JOB_NAME} \
  --location=${REGION} \
  --schedule="0 14 * * *" \
  --time-zone="UTC" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${CLOUD_RUN_JOB}:run" \
  --http-method=POST \
  --oauth-service-account-email="ai-usage-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
  --max-retry-attempts=3 \
  --max-retry-duration=3600s \
  --project=${PROJECT_ID} \
  || gcloud scheduler jobs update http ${JOB_NAME} \
     --location=${REGION} \
     --schedule="0 14 * * *" \
     --project=${PROJECT_ID}

echo ""
echo "================================================"
echo "Scheduler setup complete!"
echo "================================================"
echo ""
echo "Schedule: Daily at 6 AM PT (14:00 UTC)"
echo "Next run: \$(gcloud scheduler jobs describe ${JOB_NAME} --location=${REGION} --format='value(schedule)')"
echo ""
echo "To trigger manually:"
echo "  gcloud scheduler jobs run ${JOB_NAME} --location=${REGION}"
echo ""
echo "To view scheduler logs:"
echo "  gcloud logging read \"resource.type=cloud_scheduler_job AND resource.labels.job_id=${JOB_NAME}\" --limit=20"
