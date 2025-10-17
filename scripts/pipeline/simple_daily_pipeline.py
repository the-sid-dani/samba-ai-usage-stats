#!/usr/bin/env python3
"""
Simple Daily Pipeline - Direct Implementation
Bypasses complex imports and runs data ingestion directly.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from google.cloud import bigquery, secretmanager

# Environment setup
os.environ['GOOGLE_CLOUD_PROJECT'] = 'ai-workflows-459123'
os.environ['BIGQUERY_DATASET'] = 'ai_usage_analytics'
os.environ['ENVIRONMENT'] = 'production'

def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('simple_pipeline.log')
        ]
    )
    return logging.getLogger('simple_pipeline')

def get_secret(secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def fetch_cursor_data(days_back=1):
    """Fetch data from Cursor API."""
    import requests

    logger = logging.getLogger('simple_pipeline')
    logger.info("Fetching Cursor data...")

    try:
        # Get API key
        api_key = get_secret("cursor-api-key")

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        # API call
        url = "https://api.cursor.com/teams/daily-usage-data"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            records = result.get('data', [])
            logger.info(f"✅ Cursor API: Retrieved {len(records)} records")
            return records
        else:
            logger.error(f"❌ Cursor API error: {response.status_code} - {response.text[:200]}")
            return []

    except Exception as e:
        logger.error(f"❌ Cursor API failed: {e}")
        return []

def fetch_anthropic_data(days_back=1):
    """Fetch data from Anthropic API."""
    import requests

    logger = logging.getLogger('simple_pipeline')
    logger.info("Fetching Anthropic data...")

    try:
        # Get API key
        api_key = get_secret("anthropic-api-key")

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        # Usage data
        usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        params = {
            "starting_at": start_date.strftime("%Y-%m-%d"),
            "ending_at": end_date.strftime("%Y-%m-%d")
        }

        response = requests.get(usage_url, headers=headers, params=params, timeout=30)

        usage_records = []
        if response.status_code == 200:
            result = response.json()
            usage_records = result.get('data', [])
            logger.info(f"✅ Anthropic Usage API: Retrieved {len(usage_records)} records")
        else:
            logger.error(f"❌ Anthropic Usage API error: {response.status_code}")

        # Cost data
        cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
        cost_response = requests.get(cost_url, headers=headers, params=params, timeout=30)

        cost_records = []
        if cost_response.status_code == 200:
            cost_result = cost_response.json()
            cost_records = cost_result.get('data', [])
            logger.info(f"✅ Anthropic Cost API: Retrieved {len(cost_records)} records")
        else:
            logger.error(f"❌ Anthropic Cost API error: {cost_response.status_code}")

        return {"usage": usage_records, "cost": cost_records}

    except Exception as e:
        logger.error(f"❌ Anthropic API failed: {e}")
        return {"usage": [], "cost": []}

def store_cursor_data(records):
    """Store Cursor data in BigQuery."""
    logger = logging.getLogger('simple_pipeline')

    if not records:
        logger.info("No Cursor data to store")
        return 0

    try:
        client = bigquery.Client(project="ai-workflows-459123")
        table_id = "ai-workflows-459123.ai_usage_analytics.fact_cursor_daily_usage"

        # Transform records for new fact table schema
        bq_records = []
        for record in records:
            # Convert date - could be timestamp or date string
            usage_date = record.get("date", datetime.now().date().strftime("%Y-%m-%d"))
            if isinstance(usage_date, (int, float)) or (isinstance(usage_date, str) and usage_date.isdigit()):
                # Convert Unix timestamp to date
                timestamp = int(float(str(usage_date))) / 1000  # Convert milliseconds to seconds
                usage_date = datetime.fromtimestamp(timestamp).date().strftime("%Y-%m-%d")
            elif isinstance(usage_date, str) and len(usage_date) > 10:
                # Already a date string, truncate if needed
                usage_date = usage_date[:10]

            # Generate unique event ID
            event_id = f"cursor_{record.get('email', 'unknown')}_{usage_date}_{datetime.now().strftime('%H%M%S')}"

            bq_record = {
                "event_id": event_id,
                "usage_date": usage_date,
                "user_email": record.get("email", "unknown"),
                "total_lines_added": record.get("total_lines_added", 0),
                "total_lines_deleted": record.get("total_lines_deleted", 0),
                "accepted_lines_added": record.get("accepted_lines_added", 0),
                "accepted_lines_deleted": record.get("accepted_lines_deleted", 0),
                "net_lines_accepted": record.get("accepted_lines_added", 0) - record.get("accepted_lines_deleted", 0),
                "total_applies": record.get("total_applies", 0),
                "total_accepts": record.get("total_accepts", 0),
                "total_rejects": record.get("total_rejects", 0),
                "total_tabs_shown": record.get("total_tabs_shown", 0),
                "total_tabs_accepted": record.get("total_tabs_accepted", 0),
                "composer_requests": record.get("composer_requests", 0),
                "chat_requests": record.get("chat_requests", 0),
                "agent_requests": record.get("agent_requests", 0),
                "cmdk_usages": record.get("cmdk_usages", 0),
                "subscription_included_reqs": record.get("subscription_included_reqs", 0),
                "usage_based_reqs": record.get("usage_based_reqs", 0),
                "api_key_reqs": record.get("api_key_reqs", 0),
                "most_used_model": record.get("most_used_model", "unknown"),
                "client_version": record.get("client_version", "unknown"),
                "is_active": record.get("is_active", True),
                "line_acceptance_rate": record.get("line_acceptance_rate", 0.0),
                "tab_acceptance_rate": record.get("tab_acceptance_rate", 0.0),
                "overall_acceptance_rate": record.get("overall_acceptance_rate", 0.0),
                "productivity_velocity": record.get("productivity_velocity", 0.0),
                "estimated_subscription_cost": record.get("estimated_subscription_cost", 0.0),
                "estimated_overage_cost": record.get("estimated_overage_cost", 0.0),
                "estimated_total_cost": record.get("estimated_total_cost", 0.0),
                "attribution_confidence": 1.0,
                "pipeline_run_id": f"simple_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            bq_records.append(bq_record)

        # Insert data
        table = client.get_table(table_id)
        errors = client.insert_rows_json(table, bq_records)

        if not errors:
            logger.info(f"✅ Inserted {len(bq_records)} Cursor records into BigQuery")
            return len(bq_records)
        else:
            logger.error(f"❌ BigQuery insertion errors: {errors}")
            return 0

    except Exception as e:
        logger.error(f"❌ Cursor data storage failed: {e}")
        return 0

def store_anthropic_data(data):
    """Store Anthropic data in new fact_claude_daily_usage table."""
    logger = logging.getLogger('simple_pipeline')

    usage_records = data.get("usage", [])
    cost_records = data.get("cost", [])

    if not usage_records and not cost_records:
        return 0

    try:
        client = bigquery.Client(project="ai-workflows-459123")
        table_id = "ai-workflows-459123.ai_usage_analytics.fact_claude_daily_usage"

        # Create separate records for each usage/cost entry - don't combine yet
        all_records = []

        # Process each usage record as individual fact record
        for record in usage_records:
            usage_date = record.get("usage_date", datetime.now().date().strftime("%Y-%m-%d"))
            api_key_id = record.get("api_key_id", "unknown")

            fact_record = {
                "api_key_id": api_key_id,
                "usage_date": usage_date,
                "model": record.get("model", "unknown"),
                "uncached_input_tokens": record.get("uncached_input_tokens", 0),
                "cached_input_tokens": record.get("cached_input_tokens", 0),
                "cache_read_input_tokens": record.get("cache_read_input_tokens", 0),
                "output_tokens": record.get("output_tokens", 0),
                "total_tokens": record.get("uncached_input_tokens", 0) + record.get("cached_input_tokens", 0) + record.get("output_tokens", 0),
                "claude_api_cost_usd": 0.0,  # Will be populated from cost records
                "total_cost_usd": 0.0,
                "record_type": "usage"
            }
            all_records.append(fact_record)

        # Process each cost record as individual fact record
        for record in cost_records:
            cost_date = record.get("cost_date", datetime.now().date().strftime("%Y-%m-%d"))
            api_key_id = record.get("api_key_id", "unknown")

            fact_record = {
                "api_key_id": api_key_id,
                "usage_date": cost_date,
                "model": record.get("model", "unknown"),
                "uncached_input_tokens": 0,
                "cached_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "claude_api_cost_usd": record.get("cost_usd", 0.0),
                "total_cost_usd": record.get("cost_usd", 0.0),
                "record_type": "cost"
            }
            all_records.append(fact_record)

        # Transform to BigQuery records
        bq_records = []
        for i, data in enumerate(all_records):
            event_id = f"claude_api_{data['api_key_id']}_{data['usage_date']}_{data['record_type']}_{i}"

            bq_record = {
                "event_id": event_id,
                "usage_date": data["usage_date"],
                "platform": "claude_api",  # Platform detection - API usage
                "user_email": None,  # Will be populated via API key mapping later
                "api_key_id": data["api_key_id"],
                "workspace_id": None,
                "claude_code_sessions": 0,
                "claude_code_lines_added": 0,
                "claude_code_lines_removed": 0,
                "claude_code_net_lines": 0,
                "claude_code_commits": 0,
                "claude_code_prs": 0,
                "edit_tool_accepted": 0,
                "edit_tool_rejected": 0,
                "multi_edit_tool_accepted": 0,
                "multi_edit_tool_rejected": 0,
                "write_tool_accepted": 0,
                "write_tool_rejected": 0,
                "notebook_edit_tool_accepted": 0,
                "notebook_edit_tool_rejected": 0,
                "uncached_input_tokens": data.get("uncached_input_tokens", 0),
                "cached_input_tokens": data.get("cached_input_tokens", 0),
                "cache_read_input_tokens": data.get("cache_read_input_tokens", 0),
                "cache_creation_1h_tokens": 0,
                "cache_creation_5m_tokens": 0,
                "output_tokens": data.get("output_tokens", 0),
                "web_search_requests": 0,
                "claude_ai_conversations": 0,
                "claude_ai_projects": 0,
                "claude_ai_files_uploaded": 0,
                "claude_ai_messages_sent": 0,
                "claude_ai_active_time_minutes": 0,
                "claude_code_cost_usd": 0.0,
                "claude_api_cost_usd": data.get("claude_api_cost_usd", 0.0),
                "claude_ai_cost_usd": 0.0,
                "total_cost_usd": data.get("total_cost_usd", 0.0),
                "input_token_cost_usd": 0.0,
                "output_token_cost_usd": 0.0,
                "cache_read_cost_usd": 0.0,
                "web_search_cost_usd": 0.0,
                "subscription_cost_usd": 0.0,
                "claude_code_total_tool_suggestions": 0,
                "claude_code_total_tool_accepted": 0,
                "claude_code_total_tool_rejected": 0,
                "claude_code_acceptance_rate": 0.0,
                "claude_code_lines_per_session": 0.0,
                "claude_code_productivity_score": 0.0,
                "total_tokens": data.get("total_tokens", 0),
                "tokens_per_session": 0.0,
                "cost_per_token": data.get("total_cost_usd", 0.0) / max(data.get("total_tokens", 1), 1),
                "cost_per_interaction": 0.0,
                "claude_ai_engagement_score": 0.0,
                "claude_api_efficiency_ratio": 0.0,
                "model": data.get("model", "unknown"),
                "service_tier": "unknown",
                "context_window": "unknown",
                "actor_type": "api_user",
                "platform_detection_method": "api_key_based",
                "attribution_method": "api_key_mapping",
                "attribution_confidence": 0.8,  # Lower confidence until user mapping
                "data_source": "anthropic_api",
                "has_productivity_data": False,
                "has_token_data": data.get("total_tokens", 0) > 0,
                "has_cost_data": data.get("total_cost_usd", 0.0) > 0,
                "data_completeness_score": 0.7,
                "ingest_date": datetime.now().date().strftime("%Y-%m-%d"),
                "pipeline_run_id": f"simple_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "source_api_endpoint": "anthropic_usage_api",
                "raw_response": json.dumps({"usage": usage_records, "cost": cost_records})
            }
            bq_records.append(bq_record)

        # Insert data
        table = client.get_table(table_id)
        errors = client.insert_rows_json(table, bq_records)

        if not errors:
            logger.info(f"✅ Inserted {len(bq_records)} Anthropic records into fact_claude_daily_usage")
            return len(bq_records)
        else:
            logger.error(f"❌ BigQuery insertion errors: {errors}")
            return 0

    except Exception as e:
        logger.error(f"❌ Anthropic data storage failed: {e}")
        return 0

def main():
    """Main pipeline execution."""
    logger = setup_logging()

    logger.info("🚀 Simple Daily Pipeline Execution")
    logger.info("=" * 50)

    try:
        # Fetch data from APIs
        cursor_data = fetch_cursor_data(days_back=1)
        anthropic_data = fetch_anthropic_data(days_back=1)

        # Store data in BigQuery
        cursor_stored = store_cursor_data(cursor_data)
        anthropic_stored = store_anthropic_data(anthropic_data)

        # Summary
        total_stored = cursor_stored + anthropic_stored
        logger.info("=" * 50)
        logger.info("🎉 Pipeline Execution Summary")
        logger.info(f"Cursor records: {cursor_stored}")
        logger.info(f"Anthropic records: {anthropic_stored}")
        logger.info(f"Total stored: {total_stored}")

        if total_stored > 0:
            logger.info("✅ Data successfully ingested into BigQuery")
            logger.info("✅ Analytics views ready for dashboard access")
            return True
        else:
            logger.warning("⚠️ No data was stored")
            return False

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        return False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple AI Usage Analytics Pipeline")
    parser.add_argument("--days", type=int, default=1, help="Days to process")
    args = parser.parse_args()

    success = main()
    sys.exit(0 if success else 1)