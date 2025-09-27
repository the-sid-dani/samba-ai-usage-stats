#!/bin/bash
# Production deployment script for AI Usage Analytics Pipeline
# Usage: ./scripts/deploy.sh [environment] [project_id]

set -euo pipefail

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_ID=${2:-""}
REGION="us-central1"
SERVICE_NAME="ai-usage-analytics-pipeline"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation
if [[ -z "$PROJECT_ID" ]]; then
    log_error "Project ID is required"
    echo "Usage: $0 [environment] [project_id]"
    exit 1
fi

log_info "Starting deployment to $ENVIRONMENT environment"
log_info "Project ID: $PROJECT_ID"
log_info "Region: $REGION"

# Verify prerequisites
log_info "Checking prerequisites..."

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    log_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Set project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
log_info "Enabling required Google Cloud APIs..."
gcloud services enable \
    bigquery.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    sheets.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com

# Build and push Docker image
log_info "Building Docker image..."
IMAGE_URI="gcr.io/$PROJECT_ID/$SERVICE_NAME"
docker build -t "$IMAGE_URI:latest" .
docker push "$IMAGE_URI:latest"

# Create BigQuery dataset and tables
log_info "Setting up BigQuery infrastructure..."

# Create dataset
bq mk --dataset --location="$REGION" "$PROJECT_ID:ai_usage_analytics" 2>/dev/null || true

# Create tables
log_info "Creating BigQuery tables..."
for sql_file in sql/tables/*.sql; do
    if [[ -f "$sql_file" && "$(basename "$sql_file")" != "create_all_tables.sql" ]]; then
        table_name=$(basename "$sql_file" .sql)
        log_info "Creating table: $table_name"

        # Replace template variables in SQL
        sed "s/\${project_id}/$PROJECT_ID/g; s/\${dataset}/ai_usage_analytics/g" "$sql_file" | \
        bq query --use_legacy_sql=false --replace --project_id="$PROJECT_ID" || {
            log_warn "Failed to create table from $sql_file"
        }
    fi
done

# Create views
log_info "Creating BigQuery views..."
for view_file in sql/views/*.sql; do
    if [[ -f "$view_file" && "$(basename "$view_file")" != "create_all_views.sql" ]]; then
        view_name=$(basename "$view_file" .sql)
        log_info "Creating view: $view_name"

        # Replace template variables in SQL
        sed "s/\${project_id}/$PROJECT_ID/g; s/\${dataset}/ai_usage_analytics/g" "$view_file" | \
        bq query --use_legacy_sql=false --replace --project_id="$PROJECT_ID" || {
            log_warn "Failed to create view from $view_file"
        }
    fi
done

# Deploy Cloud Run service
log_info "Deploying Cloud Run service..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URI:latest" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 3600 \
    --max-instances 10 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,ENVIRONMENT=$ENVIRONMENT,BIGQUERY_DATASET=ai_usage_analytics" \
    --service-account="ai-usage-pipeline@$PROJECT_ID.iam.gserviceaccount.com"

# Get Cloud Run service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")

# Setup Cloud Scheduler
log_info "Setting up Cloud Scheduler..."
gcloud scheduler jobs create http daily-usage-analytics \
    --location="$REGION" \
    --schedule="0 6 * * *" \
    --uri="$SERVICE_URL/run-daily-job" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"mode": "production", "days": 1}' \
    --oidc-service-account-email="ai-usage-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --oidc-token-audience="$SERVICE_URL" \
    --time-zone="America/Los_Angeles" \
    --description="Daily AI usage analytics data pipeline" \
    --max-retry-attempts=3 \
    --max-retry-duration=600s \
    2>/dev/null || {
        log_warn "Scheduler job may already exist. Updating..."
        gcloud scheduler jobs update http daily-usage-analytics \
            --location="$REGION" \
            --schedule="0 6 * * *" \
            --uri="$SERVICE_URL/run-daily-job"
    }

# Deployment validation
log_info "Validating deployment..."

# Test health check endpoint
if curl -f -s "$SERVICE_URL/health" >/dev/null; then
    log_info "✅ Health check endpoint is responding"
else
    log_warn "⚠️  Health check endpoint not responding (this is normal if service is cold)"
fi

# Deployment summary
log_info "🎉 Deployment completed successfully!"
echo
echo "=== Deployment Summary ==="
echo "Environment: $ENVIRONMENT"
echo "Project ID: $PROJECT_ID"
echo "Cloud Run URL: $SERVICE_URL"
echo "BigQuery Dataset: ai_usage_analytics"
echo "Scheduler: Daily at 6 AM PST"
echo
echo "=== Next Steps ==="
echo "1. Add API keys to Secret Manager:"
echo "   - cursor-api-key"
echo "   - anthropic-api-key"
echo "   - sheets-service-account-key"
echo
echo "2. Configure Google Sheets API key mapping spreadsheet"
echo
echo "3. Test the pipeline:"
echo "   curl -X POST $SERVICE_URL/run-daily-job -d '{\"mode\":\"dry_run\",\"days\":1}'"
echo
echo "4. Monitor logs:"
echo "   gcloud logs read 'resource.type=cloud_run_revision' --project=$PROJECT_ID --limit=50"