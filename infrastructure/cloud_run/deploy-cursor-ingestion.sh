#!/bin/bash
set -euo pipefail

# Deploy Cursor Daily Ingestion to Cloud Run
# Based on Claude ingestion deployment pattern

PROJECT_ID="ai-workflows-459123"
REGION="us-central1"
SERVICE_NAME="cursor-daily-ingest"
IMAGE_NAME="gcr.io/${PROJECT_ID}/cursor-daily-ingest:latest"
SERVICE_ACCOUNT="ai-usage-pipeline@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=================================================="
echo "Deploying Cursor Daily Ingestion to Cloud Run"
echo "=================================================="

# Build container image LOCALLY (avoids Cloud Build soft delete policy)
echo "Step 1: Building container image locally..."
cd "$(dirname "$0")/../.."
docker build --platform linux/amd64 -f src/ingestion/Dockerfile -t ${IMAGE_NAME} .

echo "Step 1b: Pushing image to GCR..."
docker push ${IMAGE_NAME}

# Deploy or update Cloud Run Job
echo "Step 2: Deploying to Cloud Run..."
gcloud run jobs deploy "${SERVICE_NAME}" \
  --image="${IMAGE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-env-vars="TARGET_GCP_PROJECT=${PROJECT_ID}" \
  --set-env-vars="TARGET_BQ_DATASET=ai_usage_analytics" \
  --set-env-vars="CURSOR_SECRET_PROJECT=${PROJECT_ID}" \
  --set-env-vars="CURSOR_SECRET_ID=cursor-api-key" \
  --set-env-vars="CURSOR_SECRET_VERSION=latest" \
  --set-env-vars="LOG_LEVEL=INFO" \
  --max-retries=1 \
  --task-timeout=30m \
  --memory=512Mi \
  --cpu=1

echo "Step 3: Deployment complete!"
echo "Job name: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo ""
echo "To run manually:"
echo "  gcloud run jobs execute ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "To check logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${SERVICE_NAME}\" --limit=50 --project=${PROJECT_ID}"
