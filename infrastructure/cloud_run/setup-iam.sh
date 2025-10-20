#!/bin/bash
set -e

# Claude Data Ingestion - IAM Setup
# Configures service accounts and Secret Manager permissions

PROJECT_ID="ai-workflows-459123"
PROJECT_NUMBER="201626763325"
PIPELINE_SA="ai-usage-pipeline@${PROJECT_ID}.iam.gserviceaccount.com"
SCHEDULER_SA="ai-usage-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"

echo "================================================"
echo "Claude Data Ingestion - IAM Setup"
echo "================================================"

# Step 1: Verify service accounts exist
echo ""
echo "Step 1: Verifying service accounts..."
gcloud iam service-accounts describe ${PIPELINE_SA} --project=${PROJECT_ID} || {
  echo "Creating ai-usage-pipeline service account..."
  gcloud iam service-accounts create ai-usage-pipeline \
    --display-name="AI Usage Pipeline" \
    --description="Service account for Claude data ingestion pipeline" \
    --project=${PROJECT_ID}
}

gcloud iam service-accounts describe ${SCHEDULER_SA} --project=${PROJECT_ID} || {
  echo "Creating ai-usage-scheduler service account..."
  gcloud iam service-accounts create ai-usage-scheduler \
    --display-name="AI Usage Scheduler" \
    --description="Service account for Cloud Scheduler to trigger ingestion jobs" \
    --project=${PROJECT_ID}
}

# Step 2: Grant Secret Manager access to pipeline SA
echo ""
echo "Step 2: Granting Secret Manager access..."
gcloud secrets add-iam-policy-binding anthropic-admin-api-key \
  --member="serviceAccount:${PIPELINE_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=${PROJECT_ID}

# Step 3: Grant BigQuery permissions to pipeline SA
echo ""
echo "Step 3: Granting BigQuery permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PIPELINE_SA}" \
  --role="roles/bigquery.dataEditor" \
  --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PIPELINE_SA}" \
  --role="roles/bigquery.jobUser" \
  --condition=None

# Step 4: Grant Cloud Run Invoker role to scheduler SA
echo ""
echo "Step 4: Granting Cloud Run Invoker role to scheduler..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SCHEDULER_SA}" \
  --role="roles/run.invoker" \
  --condition=None

echo ""
echo "================================================"
echo "IAM setup complete!"
echo "================================================"
echo ""
echo "Service Accounts:"
echo "  Pipeline: ${PIPELINE_SA}"
echo "  Scheduler: ${SCHEDULER_SA}"
echo ""
echo "Permissions granted:"
echo "  ✓ Secret Manager (anthropic-admin-api-key)"
echo "  ✓ BigQuery Data Editor (ai_usage_analytics)"
echo "  ✓ BigQuery Job User"
echo "  ✓ Cloud Run Invoker"
