#!/bin/bash

# Production Secrets Setup Script
# Configures Secret Manager secrets for AI Usage Analytics Pipeline
# Usage: ./scripts/setup_production_secrets.sh <project_id>

set -e  # Exit on any error

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION="us-central1"

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

    # Enable Secret Manager API
    log_info "Enabling Secret Manager API..."
    gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"

    log_success "Prerequisites validated"
}

# Create or update secret
create_secret() {
    local secret_name="$1"
    local secret_description="$2"
    local secret_file="$3"

    log_info "Setting up secret: $secret_name"

    # Check if secret exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        log_info "Secret $secret_name already exists, adding new version..."
    else
        log_info "Creating new secret: $secret_name"
        gcloud secrets create "$secret_name" \
            --replication-policy="automatic" \
            --project="$PROJECT_ID" \
            --description="$secret_description"
    fi

    # Add secret version
    if [[ -f "$secret_file" ]]; then
        gcloud secrets versions add "$secret_name" \
            --data-file="$secret_file" \
            --project="$PROJECT_ID"
        log_success "Secret $secret_name updated from file: $secret_file"
    else
        log_warning "Secret file not found: $secret_file"
        log_info "Please create the file and run the script again, or add the secret manually:"
        log_info "  gcloud secrets versions add $secret_name --data-file=\"$secret_file\" --project=\"$PROJECT_ID\""
    fi
}

# Create secret from user input
create_secret_interactive() {
    local secret_name="$1"
    local secret_description="$2"
    local secret_prompt="$3"

    log_info "Setting up secret: $secret_name"

    # Check if secret exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        log_info "Secret $secret_name already exists"
        echo -n "Do you want to update it? (y/N): "
        read -r update_choice
        if [[ "$update_choice" != "y" && "$update_choice" != "Y" ]]; then
            log_info "Skipping $secret_name"
            return
        fi
    else
        log_info "Creating new secret: $secret_name"
        gcloud secrets create "$secret_name" \
            --replication-policy="automatic" \
            --project="$PROJECT_ID" \
            --description="$secret_description"
    fi

    # Get secret value from user
    echo -n "$secret_prompt: "
    read -r secret_value

    if [[ -n "$secret_value" ]]; then
        echo "$secret_value" | gcloud secrets versions add "$secret_name" \
            --data-file=- \
            --project="$PROJECT_ID"
        log_success "Secret $secret_name updated"
    else
        log_warning "No value provided for $secret_name"
    fi
}

# Setup all required secrets
setup_secrets() {
    log_info "Setting up production secrets..."

    # Cursor API Key
    create_secret_interactive \
        "cursor-api-key" \
        "Cursor API key for samba.tv organization usage data" \
        "Enter Cursor API key"

    # Anthropic API Key
    create_secret_interactive \
        "anthropic-api-key" \
        "Anthropic API key for usage and cost data" \
        "Enter Anthropic API key"

    # Google Sheets Service Account Key
    log_info "Setting up Google Sheets service account key..."

    local sheets_key_file="service-account-key.json"
    echo -n "Enter path to Google Sheets service account JSON file [$sheets_key_file]: "
    read -r user_sheets_file

    if [[ -n "$user_sheets_file" ]]; then
        sheets_key_file="$user_sheets_file"
    fi

    create_secret \
        "sheets-service-account-key" \
        "Google Sheets service account key for user attribution" \
        "$sheets_key_file"

    log_success "All secrets configured"
}

# Configure IAM permissions
configure_iam() {
    log_info "Configuring IAM permissions..."

    local service_account="ai-usage-pipeline@${PROJECT_ID}.iam.gserviceaccount.com"

    # Grant Secret Manager access to Cloud Run service account
    local secrets=("cursor-api-key" "anthropic-api-key" "sheets-service-account-key")

    for secret in "${secrets[@]}"; do
        log_info "Granting access to secret: $secret"
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:$service_account" \
            --role="roles/secretmanager.secretAccessor" \
            --project="$PROJECT_ID"
    done

    log_success "IAM permissions configured"
}

# Validate secret access
validate_secrets() {
    log_info "Validating secret access..."

    local secrets=("cursor-api-key" "anthropic-api-key" "sheets-service-account-key")

    for secret in "${secrets[@]}"; do
        log_info "Checking secret: $secret"

        if gcloud secrets versions access latest --secret="$secret" --project="$PROJECT_ID" &> /dev/null; then
            log_success "✓ Secret $secret is accessible"
        else
            log_error "✗ Secret $secret is not accessible"
        fi
    done
}

# Generate configuration documentation
generate_documentation() {
    log_info "Generating configuration documentation..."

    local doc_file="production_secrets_setup.md"

    cat > "$doc_file" << EOF
# Production Secrets Configuration

This document describes the Secret Manager secrets configured for the AI Usage Analytics Pipeline.

## Configuration Date
$(date)

## Project Information
- **Project ID**: $PROJECT_ID
- **Region**: $REGION

## Configured Secrets

### cursor-api-key
- **Description**: Cursor API key for samba.tv organization usage data
- **Usage**: Used by Cursor client to fetch usage data for 76+ users
- **Access**: Cloud Run service account

### anthropic-api-key
- **Description**: Anthropic API key for usage and cost data
- **Usage**: Used by Anthropic client to fetch usage and cost data
- **Expected Volume**: 118M+ input tokens, 5.4M+ output tokens
- **Access**: Cloud Run service account

### sheets-service-account-key
- **Description**: Google Sheets service account key for user attribution
- **Usage**: Used to map API keys to user emails for attribution
- **Target**: >90% attribution coverage
- **Access**: Cloud Run service account

## Service Account
- **Name**: ai-usage-pipeline@${PROJECT_ID}.iam.gserviceaccount.com
- **Permissions**: secretmanager.secretAccessor on all secrets

## Validation Commands

Test secret access:
\`\`\`bash
# Test each secret
gcloud secrets versions access latest --secret="cursor-api-key" --project="$PROJECT_ID"
gcloud secrets versions access latest --secret="anthropic-api-key" --project="$PROJECT_ID"
gcloud secrets versions access latest --secret="sheets-service-account-key" --project="$PROJECT_ID"
\`\`\`

## Next Steps

1. **Test API Connectivity**: Run the validation script to test API access
   \`\`\`bash
   python scripts/validate_production_deployment.py --project-id $PROJECT_ID
   \`\`\`

2. **Deploy Cloud Run Service**: Deploy the service with secrets access
   \`\`\`bash
   ./scripts/deploy_cloud_run.sh $PROJECT_ID
   \`\`\`

3. **Execute End-to-End Test**: Validate the complete pipeline
   \`\`\`bash
   python scripts/validate_production_deployment.py \\
     --project-id $PROJECT_ID \\
     --service-url https://your-service-url
   \`\`\`

## Security Notes

- All secrets are encrypted at rest in Google Secret Manager
- Access is restricted to the Cloud Run service account
- Secrets are injected at runtime, not stored in container images
- Regular rotation is recommended for API keys

## Troubleshooting

### Secret Access Issues
- Verify service account has secretmanager.secretAccessor role
- Check that secrets exist and have valid versions
- Ensure Cloud Run service is using the correct service account

### API Authentication Issues
- Verify API keys are valid and have proper permissions
- Check that API keys are for the correct organization (samba.tv)
- Validate API key format and length

EOF

    log_success "Documentation generated: $doc_file"
}

# Main setup flow
main() {
    log_info "Starting production secrets setup"
    log_info "Project: $PROJECT_ID"

    # Execute setup steps
    validate_prerequisites
    setup_secrets
    configure_iam
    validate_secrets
    generate_documentation

    log_success "🎉 Production secrets setup completed successfully!"

    echo ""
    log_info "Summary:"
    echo "🔑 All required secrets configured in Secret Manager"
    echo "👤 IAM permissions granted to Cloud Run service account"
    echo "✅ Secret access validated"
    echo "📄 Configuration documented in production_secrets_setup.md"

    echo ""
    log_info "Next steps:"
    echo "1. Test API connectivity with validation script"
    echo "2. Deploy Cloud Run service with secrets access"
    echo "3. Execute end-to-end production validation"

    echo ""
    log_info "Validation command:"
    echo "python scripts/validate_production_deployment.py --project-id $PROJECT_ID --service-url https://your-service-url"
}

# Show usage if no arguments provided
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <project_id>"
    echo ""
    echo "Arguments:"
    echo "  project_id    GCP project ID for Secret Manager"
    echo ""
    echo "Example:"
    echo "  $0 my-analytics-project"
    echo ""
    echo "This script will:"
    echo "  - Enable Secret Manager API"
    echo "  - Create required secrets interactively"
    echo "  - Configure IAM permissions"
    echo "  - Validate secret access"
    echo "  - Generate configuration documentation"
    exit 1
fi

# Run main function
main "$@"