#!/bin/bash
# Phase 2: Drop Old Tables (Breaking Change)
# ⚠️ POINT OF NO RETURN - Execute only after new tables are validated

set -e  # Exit on any error

PROJECT_ID="ai-workflows-459123"
DATASET="ai_usage_analytics"

echo "🚨 BREAKING CHANGE: Dropping Old Tables"
echo "======================================="
echo "Project: $PROJECT_ID"
echo "Dataset: $DATASET"
echo ""
echo "⚠️  WARNING: This operation cannot be undone!"
echo "⚠️  Ensure new tables are working correctly before proceeding"
echo ""

# Confirmation prompt
read -p "Are you sure you want to drop all old tables? (type 'DROP_TABLES' to confirm): " confirmation
if [ "$confirmation" != "DROP_TABLES" ]; then
    echo "❌ Operation cancelled - confirmation not provided"
    exit 1
fi

echo ""
echo "🗑️ Dropping old tables..."

# Drop old tables in dependency order
echo "Dropping raw_cursor_usage..."
bq rm -f -t $PROJECT_ID:$DATASET.raw_cursor_usage
echo "✅ raw_cursor_usage dropped"

echo "Dropping raw_anthropic_usage..."
bq rm -f -t $PROJECT_ID:$DATASET.raw_anthropic_usage
echo "✅ raw_anthropic_usage dropped"

echo "Dropping raw_anthropic_cost..."
bq rm -f -t $PROJECT_ID:$DATASET.raw_anthropic_cost
echo "✅ raw_anthropic_cost dropped"

echo "Dropping fct_usage_daily..."
bq rm -f -t $PROJECT_ID:$DATASET.fct_usage_daily
echo "✅ fct_usage_daily dropped"

echo "Dropping fct_cost_daily..."
bq rm -f -t $PROJECT_ID:$DATASET.fct_cost_daily
echo "✅ fct_cost_daily dropped"

echo "Dropping dim_users..."
bq rm -f -t $PROJECT_ID:$DATASET.dim_users
echo "✅ dim_users dropped"

echo "Dropping dim_api_keys..."
bq rm -f -t $PROJECT_ID:$DATASET.dim_api_keys
echo "✅ dim_api_keys dropped"

echo ""
echo "🎉 OLD SCHEMA CLEANUP COMPLETE!"
echo "✅ All old tables successfully dropped"
echo "✅ Ready for new architecture pipeline deployment"
echo ""
echo "📋 Next Steps:"
echo "1. Update pipeline to write to new tables"
echo "2. Test end-to-end data ingestion"
echo "3. Build category-specific analytical views"
echo "4. Deploy Metabase dashboards"