#!/bin/bash
# Infrastructure Deployment Prerequisites Validation
# Usage: ./scripts/validate-deployment-prerequisites.sh [project-id]

set -euo pipefail

PROJECT_ID=${1:-""}
REGION="us-central1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Validation results
VALIDATION_PASSED=true

validate_prerequisite() {
    local description="$1"
    local command="$2"
    local fix_hint="$3"

    log_step "Checking: $description"

    if eval "$command" >/dev/null 2>&1; then
        log_info "✅ $description - OK"
    else
        log_error "❌ $description - FAILED"
        log_warn "Fix: $fix_hint"
        VALIDATION_PASSED=false
    fi
}

# Start validation
log_info "🚀 Starting deployment prerequisites validation"
echo

if [[ -z "$PROJECT_ID" ]]; then
    log_error "Project ID is required"
    echo "Usage: $0 [project-id]"
    exit 1
fi

log_info "Target Project: $PROJECT_ID"
log_info "Target Region: $REGION"
echo

# Check prerequisites
log_step "=== TOOL PREREQUISITES ==="

validate_prerequisite "Terraform installed" \
    "terraform version" \
    "Install: brew install terraform OR curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -"

validate_prerequisite "Google Cloud CLI installed" \
    "gcloud version" \
    "Install: curl https://sdk.cloud.google.com | bash"

validate_prerequisite "Docker installed" \
    "docker --version" \
    "Install: brew install docker OR install Docker Desktop"

validate_prerequisite "bq command available" \
    "bq version" \
    "Install: gcloud components install bq"

echo
log_step "=== AUTHENTICATION PREREQUISITES ==="

validate_prerequisite "gcloud authenticated" \
    "gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -1" \
    "Run: gcloud auth login"

validate_prerequisite "Application Default Credentials" \
    "gcloud auth application-default print-access-token" \
    "Run: gcloud auth application-default login"

validate_prerequisite "Docker authentication" \
    "gcloud auth configure-docker --quiet" \
    "Run: gcloud auth configure-docker"

echo
log_step "=== PROJECT ACCESS PREREQUISITES ==="

validate_prerequisite "Project access" \
    "gcloud projects describe $PROJECT_ID" \
    "Verify project ID '$PROJECT_ID' exists and you have access"

validate_prerequisite "Project billing enabled" \
    "gcloud billing projects describe $PROJECT_ID" \
    "Enable billing for project '$PROJECT_ID' in GCP Console"

validate_prerequisite "Terraform permissions" \
    "gcloud iam roles describe roles/owner --project=$PROJECT_ID" \
    "Ensure your account has Editor or Owner role on project '$PROJECT_ID'"

echo
log_step "=== API ENABLEMENT CHECK ==="

# Required APIs
REQUIRED_APIS=(
    "bigquery.googleapis.com"
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "cloudscheduler.googleapis.com"
    "secretmanager.googleapis.com"
    "sheets.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    validate_prerequisite "API: $api" \
        "gcloud services list --enabled --project=$PROJECT_ID --filter='name:$api' --format='value(name)' | grep -q '$api'" \
        "Enable: gcloud services enable $api --project=$PROJECT_ID"
done

echo
log_step "=== TERRAFORM CONFIGURATION CHECK ==="

validate_prerequisite "Terraform directory exists" \
    "test -d infrastructure/terraform" \
    "Ensure infrastructure/terraform directory exists with main.tf"

validate_prerequisite "Terraform main.tf exists" \
    "test -f infrastructure/terraform/main.tf" \
    "Ensure main.tf file exists in infrastructure/terraform/"

if [[ -f infrastructure/terraform/main.tf ]]; then
    validate_prerequisite "Terraform configuration valid" \
        "cd infrastructure/terraform && terraform validate" \
        "Fix Terraform configuration syntax errors"
fi

echo
log_step "=== SECRET REQUIREMENTS CHECK ==="

log_warn "📋 MANUAL SETUP REQUIRED:"
echo "After infrastructure provisioning, you'll need to manually add:"
echo "  1. Cursor API key → Secret Manager: cursor-api-key"
echo "  2. Anthropic API key → Secret Manager: anthropic-api-key"
echo "  3. Google Sheets service account JSON → Secret Manager: sheets-service-account-key"

echo
# Final result
if [[ "$VALIDATION_PASSED" == true ]]; then
    log_info "🎉 All prerequisites validated successfully!"
    echo
    echo "=== NEXT STEPS ==="
    echo "1. Run Terraform infrastructure provisioning:"
    echo "   cd infrastructure/terraform"
    echo "   terraform init"
    echo "   terraform plan -var=\"project_id=$PROJECT_ID\""
    echo "   terraform apply -var=\"project_id=$PROJECT_ID\""
    echo
    echo "2. Add API keys to Secret Manager (manual step)"
    echo "3. Proceed to Story 5.2: Deploy BigQuery Schema"
    exit 0
else
    log_error "❌ Prerequisites validation failed"
    echo
    echo "Please fix the failed prerequisites above before proceeding with deployment."
    exit 1
fi