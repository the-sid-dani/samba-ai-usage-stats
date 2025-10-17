#!/usr/bin/env python3
"""
Production AI Usage Analytics Pipeline with Platform Distinction
Implements efficient daily aggregation with Claude.AI/Claude Code/Claude API distinction.
"""

import os
import sys
import json
import logging
from datetime import datetime, date, timedelta
from collections import defaultdict
from google.cloud import bigquery, secretmanager
import requests

# Environment setup per coding standards
os.environ['GOOGLE_CLOUD_PROJECT'] = 'ai-workflows-459123'
os.environ['BIGQUERY_DATASET'] = 'ai_usage_analytics'
os.environ['ENVIRONMENT'] = 'production'

def setup_structured_logging():
    """Configure structured JSON logging per coding standards."""
    import uuid
    request_id = str(uuid.uuid4())

    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'severity': record.levelname,
                'message': record.getMessage(),
                'request_id': request_id,
                'component': record.name
            }
            return json.dumps(log_entry)

    logger = logging.getLogger('production_pipeline')
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler('production_pipeline.log')
    file_handler.setFormatter(StructuredFormatter())
    logger.addHandler(file_handler)

    return logger, request_id

def get_secret_secure(secret_id: str) -> str:
    """Get secret using secure config pattern per coding standards."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.getLogger('production_pipeline').error(f"Secret access failed: {secret_id}", extra={'error': str(e)})
        raise

def load_anthropic_platform_mapping():
    """Load API key to platform mapping."""
    try:
        with open('anthropic_platform_mapping.json', 'r') as f:
            mapping = json.load(f)
        return mapping.get('api_keys', {})
    except FileNotFoundError:
        # Create default mapping if file doesn't exist
        return {}

def fetch_cursor_daily_aggregates(start_date: date, end_date: date, request_id: str):
    """Fetch and aggregate Cursor data with error handling per coding standards."""
    logger = logging.getLogger('production_pipeline')
    logger.info(f"Fetching Cursor data", extra={
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'request_id': request_id
    })

    try:
        api_key = get_secret_secure("cursor-api-key")
        url = "https://api.cursor.com/teams/daily-usage-data"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        # Retry logic per coding standards
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=30)
                if response.status_code == 200:
                    break
                elif attempt == max_retries - 1:
                    raise Exception(f"API call failed: {response.status_code}")
                else:
                    time.sleep(2 ** attempt)  # Exponential backoff
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

        result = response.json()
        raw_records = result.get('data', [])

        logger.info(f"Retrieved raw records", extra={
            'raw_count': len(raw_records),
            'request_id': request_id
        })

        # Aggregate by user-day per requirements
        daily_aggregates = defaultdict(lambda: {
            'total_lines_added': 0,
            'accepted_lines_added': 0,
            'total_accepts': 0,
            'subscription_included_reqs': 0,
            'usage_based_reqs': 0,
            'session_count': 0
        })

        for record in raw_records:
            # Date conversion with error handling
            usage_date = record.get("date", "")
            try:
                if isinstance(usage_date, (int, float)) or (isinstance(usage_date, str) and usage_date.isdigit()):
                    timestamp = int(float(str(usage_date))) / 1000
                    usage_date = datetime.fromtimestamp(timestamp).date().strftime("%Y-%m-%d")
                elif isinstance(usage_date, str) and len(usage_date) > 10:
                    usage_date = usage_date[:10]
            except (ValueError, OSError) as e:
                logger.warning(f"Date conversion failed", extra={'raw_date': usage_date, 'error': str(e)})
                usage_date = datetime.now().date().strftime("%Y-%m-%d")

            email = record.get("email", "unknown")
            key = (email, usage_date)

            # Aggregate metrics
            agg = daily_aggregates[key]
            agg.update({
                'email': email,
                'usage_date': usage_date,
                'total_lines_added': agg['total_lines_added'] + record.get("total_lines_added", 0),
                'accepted_lines_added': agg['accepted_lines_added'] + record.get("accepted_lines_added", 0),
                'total_accepts': agg['total_accepts'] + record.get("total_accepts", 0),
                'subscription_included_reqs': agg['subscription_included_reqs'] + record.get("subscription_included_reqs", 0),
                'usage_based_reqs': agg['usage_based_reqs'] + record.get("usage_based_reqs", 0),
                'session_count': agg['session_count'] + 1
            })

        aggregated_records = list(daily_aggregates.values())

        logger.info(f"Aggregation complete", extra={
            'aggregated_count': len(aggregated_records),
            'compression_ratio': len(raw_records) / max(len(aggregated_records), 1),
            'request_id': request_id
        })

        return aggregated_records

    except Exception as e:
        logger.error(f"Cursor data fetch failed", extra={'error': str(e), 'request_id': request_id})
        raise

def fetch_anthropic_daily_aggregates(start_date: date, end_date: date, request_id: str):
    """Fetch and aggregate Anthropic data with platform distinction."""
    logger = logging.getLogger('production_pipeline')
    logger.info(f"Fetching Anthropic data with platform mapping", extra={
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'request_id': request_id
    })

    try:
        api_key = get_secret_secure("anthropic-api-key")
        platform_mapping = load_anthropic_platform_mapping()

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Get usage data with pagination
        usage_aggregates = defaultdict(lambda: {
            'uncached_input_tokens': 0,
            'cached_input_tokens': 0,
            'cache_read_input_tokens': 0,
            'output_tokens': 0,
            'request_count': 0
        })

        params = {
            "starting_at": start_date.strftime("%Y-%m-%d"),
            "ending_at": end_date.strftime("%Y-%m-%d")
        }

        usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
        page_count = 0

        while page_count < 5:  # Limit pages for efficiency
            page_count += 1

            response = requests.get(usage_url, headers=headers, params=params, timeout=60)
            if response.status_code != 200:
                logger.error(f"Usage API error: {response.status_code}")
                break

            data = response.json()
            daily_buckets = data.get('data', [])

            for daily_bucket in daily_buckets:
                bucket_date = daily_bucket.get('starting_at', '')[:10]
                daily_results = daily_bucket.get('results', [])

                for usage_record in daily_results:
                    api_key_id = usage_record.get('api_key_id', 'unknown')
                    workspace_id = usage_record.get('workspace_id')

                    # Determine platform using mapping
                    platform = "claude_api"  # default
                    if api_key_id in platform_mapping:
                        platform = platform_mapping[api_key_id].get('platform', 'claude_api')
                    elif workspace_id == "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR":
                        platform = "claude_code"

                    key = (api_key_id or 'org_aggregate', bucket_date, platform)

                    agg = usage_aggregates[key]
                    agg.update({
                        'api_key_id': api_key_id or 'org_aggregate',
                        'usage_date': bucket_date,
                        'platform': platform,
                        'uncached_input_tokens': agg['uncached_input_tokens'] + usage_record.get('uncached_input_tokens', 0),
                        'cached_input_tokens': agg['cached_input_tokens'] + usage_record.get('cached_input_tokens', 0),
                        'cache_read_input_tokens': agg['cache_read_input_tokens'] + usage_record.get('cache_read_input_tokens', 0),
                        'output_tokens': agg['output_tokens'] + usage_record.get('output_tokens', 0),
                        'request_count': agg['request_count'] + 1
                    })

            if not data.get('has_more', False):
                break

            if data.get('next_page'):
                params['page'] = data['next_page']

        logger.info(f"Usage aggregation complete", extra={
            'usage_aggregates': len(usage_aggregates),
            'request_id': request_id
        })

        # Get cost data
        cost_aggregates = defaultdict(lambda: {'total_cost_usd': 0, 'cost_count': 0})

        cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
        params = {
            "starting_at": start_date.strftime("%Y-%m-%d"),
            "ending_at": end_date.strftime("%Y-%m-%d")
        }

        page_count = 0
        while page_count < 5:
            page_count += 1

            response = requests.get(cost_url, headers=headers, params=params, timeout=60)
            if response.status_code != 200:
                break

            data = response.json()
            daily_buckets = data.get('data', [])

            for daily_bucket in daily_buckets:
                bucket_date = daily_bucket.get('starting_at', '')[:10]
                daily_results = daily_bucket.get('results', [])

                for cost_record in daily_results:
                    # Aggregate costs by date (no API key breakdown in cost data)
                    key = bucket_date

                    agg = cost_aggregates[key]
                    agg.update({
                        'cost_date': bucket_date,
                        'total_cost_usd': agg['total_cost_usd'] + float(cost_record.get('amount', 0)),
                        'cost_count': agg['cost_count'] + 1
                    })

            if not data.get('has_more', False):
                break

            if data.get('next_page'):
                params['page'] = data['next_page']

        logger.info(f"Cost aggregation complete", extra={
            'cost_aggregates': len(cost_aggregates),
            'request_id': request_id
        })

        return {
            "usage": list(usage_aggregates.values()),
            "cost": list(cost_aggregates.values())
        }

    except Exception as e:
        logger.error(f"Anthropic data fetch failed", extra={'error': str(e), 'request_id': request_id})
        raise

def store_data_efficiently(cursor_data, anthropic_data, request_id: str):
    """Store aggregated data in BigQuery with batch processing per coding standards."""
    logger = logging.getLogger('production_pipeline')
    client = bigquery.Client(project="ai-workflows-459123")

    total_stored = 0

    # Store Cursor data in batches
    if cursor_data:
        try:
            table_id = "ai-workflows-459123.ai_usage_analytics.raw_cursor_usage"

            # Process in 1000-record batches per coding standards
            batch_size = 1000
            for i in range(0, len(cursor_data), batch_size):
                batch = cursor_data[i:i+batch_size]

                # Add metadata
                for record in batch:
                    record['ingest_date'] = datetime.now().date().strftime("%Y-%m-%d")
                    record['ingest_timestamp'] = datetime.utcnow().isoformat() + 'Z'
                    record['request_id'] = request_id
                    record['raw_response'] = json.dumps(record)

                table = client.get_table(table_id)
                errors = client.insert_rows_json(table, batch)

                if not errors:
                    total_stored += len(batch)
                    logger.info(f"Cursor batch stored", extra={
                        'batch_size': len(batch),
                        'batch_number': i // batch_size + 1,
                        'request_id': request_id
                    })
                else:
                    logger.error(f"Cursor batch errors", extra={'errors': errors[:5], 'request_id': request_id})

        except Exception as e:
            logger.error(f"Cursor storage failed", extra={'error': str(e), 'request_id': request_id})

    # Store Anthropic usage data
    if anthropic_data.get("usage"):
        try:
            table_id = "ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage"
            usage_records = anthropic_data["usage"]

            # Add metadata
            for record in usage_records:
                record['ingest_date'] = datetime.now().date().strftime("%Y-%m-%d")
                record['ingest_timestamp'] = datetime.utcnow().isoformat() + 'Z'
                record['request_id'] = request_id
                record['raw_response'] = json.dumps(record)

            table = client.get_table(table_id)
            errors = client.insert_rows_json(table, usage_records)

            if not errors:
                total_stored += len(usage_records)
                logger.info(f"Anthropic usage stored", extra={
                    'records': len(usage_records),
                    'request_id': request_id
                })

        except Exception as e:
            logger.error(f"Anthropic usage storage failed", extra={'error': str(e), 'request_id': request_id})

    # Store Anthropic cost data
    if anthropic_data.get("cost"):
        try:
            table_id = "ai-workflows-459123.ai_usage_analytics.raw_anthropic_cost"
            cost_records = anthropic_data["cost"]

            # Add metadata
            for record in cost_records:
                record['api_key_id'] = 'org_aggregate'  # Cost data is org-level
                record['ingest_date'] = datetime.now().date().strftime("%Y-%m-%d")
                record['ingest_timestamp'] = datetime.utcnow().isoformat() + 'Z'
                record['request_id'] = request_id
                record['raw_response'] = json.dumps(record)

            table = client.get_table(table_id)
            errors = client.insert_rows_json(table, cost_records)

            if not errors:
                total_stored += len(cost_records)
                logger.info(f"Anthropic cost stored", extra={
                    'records': len(cost_records),
                    'request_id': request_id
                })

        except Exception as e:
            logger.error(f"Anthropic cost storage failed", extra={'error': str(e), 'request_id': request_id})

    return total_stored

def execute_production_pipeline(days_back: int = 1):
    """Execute the complete production pipeline with platform distinction."""
    logger, request_id = setup_structured_logging()

    logger.info(f"Starting production pipeline", extra={
        'days_back': days_back,
        'request_id': request_id,
        'project': os.environ['GOOGLE_CLOUD_PROJECT'],
        'dataset': os.environ['BIGQUERY_DATASET']
    })

    try:
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        # Fetch data from both APIs
        cursor_data = fetch_cursor_daily_aggregates(start_date, end_date, request_id)
        anthropic_data = fetch_anthropic_daily_aggregates(start_date, end_date, request_id)

        # Store efficiently in BigQuery
        total_stored = store_data_efficiently(cursor_data, anthropic_data, request_id)

        # Calculate platform breakdown
        platform_counts = defaultdict(int)
        for record in anthropic_data.get("usage", []):
            platform_counts[record.get('platform', 'unknown')] += 1

        # Log summary
        logger.info(f"Pipeline execution complete", extra={
            'cursor_records': len(cursor_data),
            'anthropic_usage_records': len(anthropic_data.get("usage", [])),
            'anthropic_cost_records': len(anthropic_data.get("cost", [])),
            'total_stored': total_stored,
            'platform_breakdown': dict(platform_counts),
            'request_id': request_id
        })

        print(f"\n🎉 PRODUCTION PIPELINE COMPLETE!")
        print(f"✅ Cursor records: {len(cursor_data):,}")
        print(f"✅ Anthropic usage: {len(anthropic_data.get('usage', []))}")
        print(f"✅ Anthropic cost: {len(anthropic_data.get('cost', []))}")
        print(f"✅ Total stored: {total_stored:,}")

        if platform_counts:
            print(f"🎯 Platform breakdown:")
            for platform, count in platform_counts.items():
                print(f"  {platform}: {count} records")

        return True

    except Exception as e:
        logger.error(f"Pipeline execution failed", extra={'error': str(e), 'request_id': request_id})
        print(f"❌ Pipeline failed: {e}")
        return False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Production AI Usage Analytics Pipeline")
    parser.add_argument("--days", type=int, default=1, help="Number of days to process")
    parser.add_argument("--historical", action="store_true", help="Process from Jan 1, 2025")

    args = parser.parse_args()

    days_back = (datetime.now().date() - date(2025, 1, 1)).days if args.historical else args.days

    success = execute_production_pipeline(days_back)
    sys.exit(0 if success else 1)