#!/bin/bash
set -e

# Claude Data Ingestion - Cloud Run Deployment Script
# This script builds and deploys the Claude ingestion job to Cloud Run

PROJECT_ID="ai-workflows-459123"
REGION="us-central1"
SERVICE_NAME="claude-data-ingestion"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "================================================"
echo "Claude Data Ingestion - Cloud Run Deployment"
echo "================================================"

# Step 1: Build Docker image
echo ""
echo "Step 1: Building Docker image..."
docker build -f Dockerfile.claude-ingestion -t ${IMAGE_NAME}:latest .

# Step 2: Push to Google Container Registry
echo ""
echo "Step 2: Pushing image to GCR..."
docker push ${IMAGE_NAME}:latest

# Step 3: Deploy Cloud Run Job
echo ""
echo "Step 3: Deploying Cloud Run Job..."
gcloud run jobs create ${SERVICE_NAME} \
  --image=${IMAGE_NAME}:latest \
  --region=${REGION} \
  --set-env-vars=ANTHROPIC_ORGANIZATION_ID=1233d3ee-9900-424a-a31a-fb8b8dcd0be3 \
  --set-env-vars=BIGQUERY_PROJECT_ID=${PROJECT_ID} \
  --set-env-vars=BIGQUERY_DATASET=ai_usage_analytics \
  --service-account=ai-usage-pipeline@${PROJECT_ID}.iam.gserviceaccount.com \
  --max-retries=3 \
  --task-timeout=15m \
  --memory=512Mi \
  --cpu=1 \
  --execute-now=false \
  || gcloud run jobs update ${SERVICE_NAME} \
     --image=${IMAGE_NAME}:latest \
     --region=${REGION}

echo ""
echo "================================================"
echo "Deployment complete!"
echo "================================================"
echo ""
echo "To execute manually:"
echo "  gcloud run jobs execute ${SERVICE_NAME} --region=${REGION}"
echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${SERVICE_NAME}\" --limit=50"
