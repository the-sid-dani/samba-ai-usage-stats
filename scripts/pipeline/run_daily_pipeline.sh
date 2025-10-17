#!/bin/bash

# Daily AI Usage Analytics Pipeline Execution Script
# Designed for cron scheduling

# Configuration
PROJECT_DIR="/Users/sid/Desktop/4. Coding Projects/samba-ai-usage-stats"
VENV_PATH="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/cron_pipeline.log"

# Environment variables
export GOOGLE_CLOUD_PROJECT=ai-workflows-459123
export BIGQUERY_DATASET=ai_usage_analytics
export ENVIRONMENT=production
export PYTHONPATH="$PROJECT_DIR/src"

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Main execution
main() {
    log_message "🚀 Starting AI Usage Analytics Daily Pipeline"
    log_message "Project: $GOOGLE_CLOUD_PROJECT"
    log_message "Dataset: $BIGQUERY_DATASET"

    # Change to project directory
    cd "$PROJECT_DIR" || {
        log_message "❌ Failed to change to project directory: $PROJECT_DIR"
        exit 1
    }

    # Activate virtual environment
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        source "$VENV_PATH/bin/activate"
        log_message "✅ Virtual environment activated"
    else
        log_message "❌ Virtual environment not found: $VENV_PATH"
        exit 1
    fi

    # Execute pipeline
    log_message "Executing data pipeline..."

    if python run_daily_pipeline.py --days 1; then
        log_message "🎉 Pipeline execution completed successfully"
        log_message "✅ Data available in BigQuery: ai-workflows-459123.ai_usage_analytics"
    else
        log_message "❌ Pipeline execution failed"
        exit 1
    fi

    log_message "Pipeline execution finished"
}

# Execute main function
main "$@"