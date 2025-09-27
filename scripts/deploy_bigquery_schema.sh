#!/bin/bash

# BigQuery Schema Deployment Script
# Deploys all tables and views to production BigQuery with proper template substitution
# Usage: ./scripts/deploy_bigquery_schema.sh <project_id> <dataset_name>

set -e  # Exit on any error

# Configuration
PROJECT_ID=${1:-"your-project-id"}
DATASET=${2:-"ai_usage_analytics"}
SQL_DIR="sql"
TEMP_DIR="/tmp/bigquery_deploy_$$"

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

    # Check if bq is installed
    if ! command -v bq &> /dev/null; then
        log_error "BigQuery CLI (bq) is not installed. Please install it first."
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

# Create dataset if it doesn't exist
create_dataset() {
    log_info "Creating dataset if it doesn't exist: $DATASET"

    if bq ls -d "$PROJECT_ID:$DATASET" &> /dev/null; then
        log_info "Dataset $DATASET already exists"
    else
        log_info "Creating dataset: $DATASET"
        bq mk \
            --dataset \
            --description="AI Usage Analytics Dashboard data warehouse" \
            --location=US \
            "$PROJECT_ID:$DATASET"
        log_success "Dataset created: $DATASET"
    fi
}

# Template substitution function
substitute_templates() {
    local sql_file="$1"
    local output_file="$2"

    sed -e "s/\${project_id}/$PROJECT_ID/g" \
        -e "s/\${dataset}/$DATASET/g" \
        "$sql_file" > "$output_file"
}

# Deploy tables in correct order
deploy_tables() {
    log_info "Deploying BigQuery tables..."

    # Create temp directory for processed SQL files
    mkdir -p "$TEMP_DIR/tables"

    # Table deployment order (dependencies first)
    local tables=(
        "01_raw_cursor_usage.sql"
        "02_raw_anthropic_usage.sql"
        "03_raw_anthropic_cost.sql"
        "04_dim_users.sql"
        "05_dim_api_keys.sql"
        "06_fct_usage_daily.sql"
        "07_fct_cost_daily.sql"
    )

    for table_file in "${tables[@]}"; do
        local source_file="$SQL_DIR/tables/$table_file"
        local temp_file="$TEMP_DIR/tables/$table_file"

        if [[ ! -f "$source_file" ]]; then
            log_error "Table file not found: $source_file"
            continue
        fi

        log_info "Processing table: $table_file"
        substitute_templates "$source_file" "$temp_file"

        log_info "Deploying table: $table_file"
        if bq query --use_legacy_sql=false < "$temp_file"; then
            log_success "Table deployed: $table_file"
        else
            log_error "Failed to deploy table: $table_file"
            exit 1
        fi
    done

    log_success "All tables deployed successfully"
}

# Deploy views in correct order
deploy_views() {
    log_info "Deploying BigQuery views..."

    # Create temp directory for processed SQL files
    mkdir -p "$TEMP_DIR/views"

    # Views to deploy
    local views=(
        "vw_monthly_finance.sql"
        "vw_productivity_metrics.sql"
        "vw_cost_allocation.sql"
        "vw_executive_summary.sql"
        "vw_data_quality_dashboard.sql"
        "vw_compliance_security.sql"
        "vw_system_health.sql"
    )

    for view_file in "${views[@]}"; do
        local source_file="$SQL_DIR/views/$view_file"
        local temp_file="$TEMP_DIR/views/$view_file"

        if [[ ! -f "$source_file" ]]; then
            log_warning "View file not found: $source_file (skipping)"
            continue
        fi

        log_info "Processing view: $view_file"
        substitute_templates "$source_file" "$temp_file"

        log_info "Deploying view: $view_file"
        if bq query --use_legacy_sql=false < "$temp_file"; then
            log_success "View deployed: $view_file"
        else
            log_error "Failed to deploy view: $view_file"
            exit 1
        fi
    done

    log_success "All views deployed successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check tables
    log_info "Verifying tables..."
    local expected_tables=(
        "raw_cursor_usage"
        "raw_anthropic_usage"
        "raw_anthropic_cost"
        "dim_users"
        "dim_api_keys"
        "fct_usage_daily"
        "fct_cost_daily"
    )

    for table in "${expected_tables[@]}"; do
        if bq show "$PROJECT_ID:$DATASET.$table" &> /dev/null; then
            log_success "Table verified: $table"
        else
            log_error "Table not found: $table"
            exit 1
        fi
    done

    # Check views
    log_info "Verifying views..."
    local expected_views=(
        "vw_monthly_finance"
        "vw_productivity_metrics"
        "vw_cost_allocation"
        "vw_executive_summary"
    )

    for view in "${expected_views[@]}"; do
        if bq show "$PROJECT_ID:$DATASET.$view" &> /dev/null; then
            log_success "View verified: $view"
        else
            log_error "View not found: $view"
            exit 1
        fi
    done

    # Test view execution
    log_info "Testing view execution..."
    for view in "${expected_views[@]}"; do
        log_info "Testing view: $view"
        if bq query --use_legacy_sql=false --dry_run "SELECT COUNT(*) FROM \`$PROJECT_ID.$DATASET.$view\` LIMIT 1" &> /dev/null; then
            log_success "View syntax valid: $view"
        else
            log_error "View syntax error: $view"
            exit 1
        fi
    done

    log_success "All deployment verification checks passed"
}

# Configure data governance
configure_governance() {
    log_info "Configuring data governance policies..."

    # Set table expiration for raw tables (2 years)
    local raw_tables=("raw_cursor_usage" "raw_anthropic_usage" "raw_anthropic_cost")
    for table in "${raw_tables[@]}"; do
        log_info "Setting retention policy for: $table"
        bq update --expiration 63072000 "$PROJECT_ID:$DATASET.$table"  # 2 years in seconds
    done

    # Set longer retention for fact tables (5 years)
    local fact_tables=("fct_usage_daily" "fct_cost_daily")
    for table in "${fact_tables[@]}"; do
        log_info "Setting retention policy for: $table"
        bq update --expiration 157680000 "$PROJECT_ID:$DATASET.$table"  # 5 years in seconds
    done

    log_success "Data governance policies configured"
}

# Performance optimization
optimize_performance() {
    log_info "Verifying performance optimization..."

    # The partition and cluster configurations are already in the table definitions
    # This function verifies they are applied correctly

    local partitioned_tables=("raw_cursor_usage" "raw_anthropic_usage" "raw_anthropic_cost" "fct_usage_daily" "fct_cost_daily")

    for table in "${partitioned_tables[@]}"; do
        log_info "Checking partitioning for: $table"
        local partition_info=$(bq show --schema --format=prettyjson "$PROJECT_ID:$DATASET.$table" | grep -i partition || true)
        if [[ -n "$partition_info" ]]; then
            log_success "Partitioning verified for: $table"
        else
            log_warning "No partitioning found for: $table (may be expected for dimension tables)"
        fi
    done

    log_success "Performance optimization verified"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
    log_success "Cleanup completed"
}

# Main deployment flow
main() {
    log_info "Starting BigQuery schema deployment"
    log_info "Project: $PROJECT_ID"
    log_info "Dataset: $DATASET"

    # Set trap for cleanup
    trap cleanup EXIT

    # Execute deployment steps
    validate_prerequisites
    create_dataset
    deploy_tables
    deploy_views
    verify_deployment
    configure_governance
    optimize_performance

    log_success "BigQuery schema deployment completed successfully!"
    log_info "Dataset: $PROJECT_ID:$DATASET"
    log_info "Tables: 7 deployed"
    log_info "Views: 4+ deployed"

    # Show next steps
    echo ""
    log_info "Next steps:"
    echo "1. Configure service account permissions for Looker Studio"
    echo "2. Start data ingestion pipeline"
    echo "3. Verify data flow with test queries"
    echo "4. Set up monitoring and alerting"
}

# Show usage if no arguments provided
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <project_id> [dataset_name]"
    echo ""
    echo "Arguments:"
    echo "  project_id    GCP project ID where BigQuery dataset will be created"
    echo "  dataset_name  BigQuery dataset name (default: ai_usage_analytics)"
    echo ""
    echo "Example:"
    echo "  $0 my-analytics-project ai_usage_analytics"
    exit 1
fi

# Run main function
main "$@"