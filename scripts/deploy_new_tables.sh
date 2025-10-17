#!/bin/bash
# Deploy New Two-Table Architecture to BigQuery
# Phase 1: Safe deployment of new schema alongside existing tables

set -e  # Exit on any error

PROJECT_ID="ai-workflows-459123"
DATASET="ai_usage_analytics"

echo "🏗️ Deploying New Two-Table Architecture to BigQuery"
echo "=================================================="
echo "Project: $PROJECT_ID"
echo "Dataset: $DATASET"
echo ""

# Verify BigQuery CLI is available
if ! command -v bq &> /dev/null; then
    echo "❌ BigQuery CLI (bq) not found. Please install Google Cloud SDK:"
    echo "   curl https://sdk.cloud.google.com | bash"
    echo "   gcloud auth login"
    echo "   gcloud config set project $PROJECT_ID"
    exit 1
fi

echo "✅ BigQuery CLI found"

# Deploy new tables one by one with error handling
echo ""
echo "📊 Deploying new fact tables..."

echo "Creating fact_cursor_daily_usage..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < sql/tables/fact_cursor_daily_usage.sql
if [ $? -eq 0 ]; then
    echo "✅ fact_cursor_daily_usage created successfully"
else
    echo "❌ Failed to create fact_cursor_daily_usage"
    exit 1
fi

echo "Creating fact_claude_daily_usage..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < sql/tables/fact_claude_daily_usage.sql
if [ $? -eq 0 ]; then
    echo "✅ fact_claude_daily_usage created successfully"
else
    echo "❌ Failed to create fact_claude_daily_usage"
    exit 1
fi

echo ""
echo "📋 Deploying dimension tables..."

echo "Creating dim_users_enhanced..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < sql/tables/dim_users_enhanced.sql
if [ $? -eq 0 ]; then
    echo "✅ dim_users_enhanced created successfully"
else
    echo "❌ Failed to create dim_users_enhanced"
    exit 1
fi

echo "Creating dim_date..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < sql/tables/dim_date.sql
if [ $? -eq 0 ]; then
    echo "✅ dim_date created successfully"
else
    echo "❌ Failed to create dim_date"
    exit 1
fi

echo ""
echo "🧪 Running basic validation tests..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < sql/tables/test_new_schema.sql
if [ $? -eq 0 ]; then
    echo "✅ Schema validation tests passed"
else
    echo "❌ Schema validation tests failed"
    exit 1
fi

echo ""
echo "🎉 NEW SCHEMA DEPLOYMENT COMPLETE!"
echo "✅ All new tables created successfully"
echo "✅ Validation tests passed"
echo ""
echo "📋 Next Steps:"
echo "1. Test pipeline with new tables"
echo "2. Validate data ingestion works correctly"
echo "3. Execute Phase 2: Drop old tables (breaking change)"
echo ""
echo "🚨 Old tables still exist - no breaking changes executed yet"