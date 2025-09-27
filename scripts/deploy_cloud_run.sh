#!/bin/bash

# Cloud Run Deployment Script
# Deploys AI Usage Analytics Pipeline to Cloud Run with proper configuration
# Usage: ./scripts/deploy_cloud_run.sh <project_id> [service_account_email]

set -e  # Exit on any error

# Configuration
PROJECT_ID=${1:-"your-project-id"}
SERVICE_ACCOUNT=${2:-"ai-usage-pipeline@${PROJECT_ID}.iam.gserviceaccount.com"}
REGION="us-central1"
SERVICE_NAME="ai-usage-analytics-pipeline"
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/ai-usage-analytics/pipeline"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation functions
validate_prerequisites() {
    log_info "Validating prerequisites..."

    # Check if gcloud is installed and authenticated
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi

    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
        log_error "No active gcloud authentication found. Please run: gcloud auth login"
        exit 1
    fi

    # Validate project access
    if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        log_error "Cannot access project: $PROJECT_ID. Please check project ID and permissions."
        exit 1
    fi

    log_success "Prerequisites validated"
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building and pushing Docker image..."

    # Configure Docker to use gcloud
    gcloud auth configure-docker

    # Build image with latest tag
    local build_tag="${IMAGE_NAME}:latest"
    local commit_tag="${IMAGE_NAME}:$(git rev-parse --short HEAD 2>/dev/null || echo 'manual')"

    log_info "Building Docker image: $build_tag"
    docker build -t "$build_tag" -t "$commit_tag" .

    # Push both tags
    log_info "Pushing Docker image to GCR..."
    docker push "$build_tag"
    docker push "$commit_tag"

    log_success "Docker image built and pushed successfully"
}

# Deploy to Cloud Run
deploy_service() {
    log_info "Deploying to Cloud Run..."

    # Deploy with staging tag first (no traffic)
    gcloud run deploy "$SERVICE_NAME" \
        --image "$IMAGE_NAME:latest" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --memory 1Gi \
        --cpu 1 \
        --timeout 3600 \
        --max-instances 10 \
        --min-instances 0 \
        --concurrency 1 \
        --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
        --set-env-vars="ENVIRONMENT=production" \
        --set-env-vars="BIGQUERY_DATASET=ai_usage_analytics" \
        --set-env-vars="LOG_LEVEL=INFO" \
        --set-env-vars="DEBUG=false" \
        --service-account="$SERVICE_ACCOUNT" \
        --port 8080 \
        --no-traffic \
        --tag staging

    log_success "Service deployed to staging"
}

# Validate deployment
validate_deployment() {
    log_info "Validating deployment..."

    # Get staging URL
    local staging_url
    staging_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.traffic[0].url)")

    if [[ -z "$staging_url" ]]; then
        log_error "Could not get staging URL"
        exit 1
    fi

    log_info "Testing staging deployment at: $staging_url"

    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    sleep 30

    # Test health check
    local max_attempts=5
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts"

        if curl -f -s "$staging_url/health" > /dev/null; then
            log_success "Health check passed"
            break
        elif [[ $attempt -eq $max_attempts ]]; then
            log_error "Health check failed after $max_attempts attempts"
            exit 1
        else
            log_warning "Health check failed, retrying in 10 seconds..."
            sleep 10
            ((attempt++))
        fi
    done

    # Test readiness
    if curl -f -s "$staging_url/ready" > /dev/null; then
        log_success "Readiness check passed"
    else
        log_error "Readiness check failed"
        exit 1
    fi

    log_success "Deployment validation completed"
}

# Route traffic to new version
route_traffic() {
    log_info "Routing traffic to new version..."

    # Route 100% traffic to latest
    gcloud run services update-traffic "$SERVICE_NAME" \
        --region="$REGION" \
        --to-latest

    # Get service URL
    local service_url
    service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")

    log_success "Traffic routed to new version"
    log_success "Service available at: $service_url"
}

# Setup Cloud Scheduler
setup_scheduler() {
    log_info "Setting up Cloud Scheduler..."

    # Get service URL for scheduler
    local service_url
    service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")

    # Create or update scheduler job
    local job_name="daily-usage-analytics"
    local schedule="0 6 * * *"  # 6 AM PST daily
    local endpoint_url="${service_url}/run-daily-job"

    log_info "Creating scheduler job: $job_name"

    # Try to create the job, if it exists, update it
    if gcloud scheduler jobs describe "$job_name" --location="$REGION" &> /dev/null; then
        log_info "Updating existing scheduler job"
        gcloud scheduler jobs update http "$job_name" \
            --location="$REGION" \
            --schedule="$schedule" \
            --uri="$endpoint_url" \
            --http-method=POST \
            --headers="Content-Type=application/json" \
            --message-body='{"mode": "production", "days": 1}' \
            --oidc-service-account-email="$SERVICE_ACCOUNT" \
            --oidc-token-audience="$service_url"
    else
        log_info "Creating new scheduler job"
        gcloud scheduler jobs create http "$job_name" \
            --location="$REGION" \
            --schedule="$schedule" \
            --uri="$endpoint_url" \
            --http-method=POST \
            --headers="Content-Type=application/json" \
            --message-body='{"mode": "production", "days": 1}' \
            --oidc-service-account-email="$SERVICE_ACCOUNT" \
            --oidc-token-audience="$service_url" \
            --time-zone="America/Los_Angeles" \
            --description="Daily AI usage analytics data pipeline" \
            --max-retry-attempts=3 \
            --max-retry-duration=600s
    fi

    log_success "Cloud Scheduler configured"
}

# Main deployment flow
main() {
    log_info "Starting Cloud Run deployment"
    log_info "Project: $PROJECT_ID"
    log_info "Service Account: $SERVICE_ACCOUNT"
    log_info "Region: $REGION"
    log_info "Service: $SERVICE_NAME"

    # Execute deployment steps
    validate_prerequisites
    build_and_push_image
    deploy_service
    validate_deployment
    route_traffic
    setup_scheduler

    log_success "🎉 Cloud Run deployment completed successfully!"

    # Show final status
    local service_url
    service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")

    echo ""
    log_info "Deployment Summary:"
    echo "🌐 Service URL: $service_url"
    echo "🔍 Health Check: $service_url/health"
    echo "📊 Status: $service_url/status"
    echo "⏰ Scheduler: Daily at 6 AM PST"
    echo "🔧 Manual Trigger: POST $service_url/run-daily-job"

    echo ""
    log_info "Next steps:"
    echo "1. Test the health endpoint: curl $service_url/health"
    echo "2. Verify scheduler job: gcloud scheduler jobs list --location=$REGION"
    echo "3. Monitor service logs: gcloud logging read 'resource.type=cloud_run_revision' --limit=50"
    echo "4. Test manual execution: curl -X POST -H 'Content-Type: application/json' -d '{\"mode\":\"production\",\"days\":1}' $service_url/run-daily-job"
}

# Show usage if no arguments provided
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <project_id> [service_account_email]"
    echo ""
    echo "Arguments:"
    echo "  project_id            GCP project ID for deployment"
    echo "  service_account_email Service account email (optional)"
    echo ""
    echo "Example:"
    echo "  $0 my-analytics-project"
    echo "  $0 my-analytics-project ai-pipeline@my-project.iam.gserviceaccount.com"
    exit 1
fi

# Run main function
main "$@"