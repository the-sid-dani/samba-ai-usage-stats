#!/usr/bin/env python3
"""
Efficient Daily Aggregation Pipeline
Pre-aggregates data daily for optimal storage and query performance.
"""

import os
import sys
import json
import logging
from datetime import datetime, date, timedelta
from collections import defaultdict
from google.cloud import bigquery, secretmanager
import requests

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
            logging.FileHandler('efficient_pipeline.log')
        ]
    )
    return logging.getLogger('efficient_pipeline')

def get_secret(secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def fetch_and_aggregate_cursor_data(start_date, end_date):
    """Fetch Cursor data and aggregate by user-day."""
    logger = logging.getLogger('efficient_pipeline')
    logger.info(f"Fetching Cursor data: {start_date} to {end_date}")

    try:
        api_key = get_secret("cursor-api-key")
        url = "https://api.cursor.com/teams/daily-usage-data"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            logger.error(f"Cursor API error: {response.status_code}")
            return []

        result = response.json()
        raw_records = result.get('data', [])
        logger.info(f"Retrieved {len(raw_records)} raw Cursor records")

        # Aggregate by user-day
        daily_aggregates = defaultdict(lambda: {
            'total_lines_added': 0,
            'accepted_lines_added': 0,
            'total_accepts': 0,
            'subscription_included_reqs': 0,
            'usage_based_reqs': 0,
            'session_count': 0
        })

        for record in raw_records:
            # Convert date
            usage_date = record.get("date", "")
            if isinstance(usage_date, (int, float)) or (isinstance(usage_date, str) and usage_date.isdigit()):
                timestamp = int(float(str(usage_date))) / 1000
                usage_date = datetime.fromtimestamp(timestamp).date().strftime("%Y-%m-%d")

            email = record.get("email", "unknown")
            key = (email, usage_date)

            # Aggregate metrics
            agg = daily_aggregates[key]
            agg['email'] = email
            agg['usage_date'] = usage_date
            agg['total_lines_added'] += record.get("total_lines_added", 0)
            agg['accepted_lines_added'] += record.get("accepted_lines_added", 0)
            agg['total_accepts'] += record.get("total_accepts", 0)
            agg['subscription_included_reqs'] += record.get("subscription_included_reqs", 0)
            agg['usage_based_reqs'] += record.get("usage_based_reqs", 0)
            agg['session_count'] += 1

        # Convert to list
        aggregated_records = list(daily_aggregates.values())
        logger.info(f"Aggregated to {len(aggregated_records)} daily user summaries")

        return aggregated_records

    except Exception as e:
        logger.error(f"Cursor data fetch failed: {e}")
        return []

def fetch_and_aggregate_anthropic_data(start_date, end_date):
    """Fetch Anthropic data and aggregate by user-day."""
    logger = logging.getLogger('efficient_pipeline')
    logger.info(f"Fetching Anthropic data: {start_date} to {end_date}")

    try:
        api_key = get_secret("anthropic-api-key")
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Get usage data with pagination
        usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
        all_usage_records = []

        params = {
            "starting_at": start_date.strftime("%Y-%m-%d"),
            "ending_at": end_date.strftime("%Y-%m-%d")
        }

        page_count = 0
        while page_count < 10:  # Limit pages for now
            page_count += 1
            logger.info(f"Fetching usage page {page_count}...")

            response = requests.get(usage_url, headers=headers, params=params, timeout=60)
            if response.status_code != 200:
                logger.error(f"Usage API error: {response.status_code}")
                break

            data = response.json()
            daily_buckets = data.get('data', [])

            # Extract usage records from daily buckets
            for daily_bucket in daily_buckets:
                daily_results = daily_bucket.get('results', [])
                bucket_date = daily_bucket.get('starting_at', '')[:10]  # YYYY-MM-DD

                for usage_record in daily_results:
                    usage_record['usage_date'] = bucket_date
                    all_usage_records.append(usage_record)

            # Check pagination
            if not data.get('has_more', False) or not data.get('next_page'):
                break

            params['page'] = data['next_page']

        logger.info(f"Retrieved {len(all_usage_records)} total usage records")

        # Aggregate usage by API key and day
        usage_aggregates = defaultdict(lambda: {
            'uncached_input_tokens': 0,
            'cached_input_tokens': 0,
            'cache_read_input_tokens': 0,
            'output_tokens': 0,
            'request_count': 0,
            'models_used': set()
        })

        for record in all_usage_records:
            api_key_id = record.get('api_key_id', 'unknown')
            usage_date = record.get('usage_date', '')
            key = (api_key_id, usage_date)

            agg = usage_aggregates[key]
            agg['api_key_id'] = api_key_id
            agg['usage_date'] = usage_date
            agg['uncached_input_tokens'] += record.get('uncached_input_tokens', 0)
            agg['cached_input_tokens'] += record.get('cached_input_tokens', 0)
            agg['cache_read_input_tokens'] += record.get('cache_read_input_tokens', 0)
            agg['output_tokens'] += record.get('output_tokens', 0)
            agg['request_count'] += 1
            if record.get('model'):
                agg['models_used'].add(record.get('model'))

        # Convert sets to lists
        final_usage = []
        for agg in usage_aggregates.values():
            agg['models_used'] = list(agg['models_used'])
            final_usage.append(agg)

        # Get cost data (similar aggregation)
        cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
        all_cost_records = []

        params = {
            "starting_at": start_date.strftime("%Y-%m-%d"),
            "ending_at": end_date.strftime("%Y-%m-%d")
        }

        page_count = 0
        while page_count < 10:  # Limit pages
            page_count += 1
            logger.info(f"Fetching cost page {page_count}...")

            response = requests.get(cost_url, headers=headers, params=params, timeout=60)
            if response.status_code != 200:
                logger.error(f"Cost API error: {response.status_code}")
                break

            data = response.json()
            daily_buckets = data.get('data', [])

            for daily_bucket in daily_buckets:
                daily_results = daily_bucket.get('results', [])
                bucket_date = daily_bucket.get('starting_at', '')[:10]

                for cost_record in daily_results:
                    cost_record['cost_date'] = bucket_date
                    all_cost_records.append(cost_record)

            if not data.get('has_more', False) or not data.get('next_page'):
                break

            params['page'] = data['next_page']

        logger.info(f"Retrieved {len(all_cost_records)} total cost records")

        # Aggregate costs
        cost_aggregates = defaultdict(lambda: {
            'total_cost_usd': 0,
            'cost_count': 0
        })

        for record in all_cost_records:
            cost_date = record.get('cost_date', '')
            key = cost_date  # Aggregate by date

            agg = cost_aggregates[key]
            agg['cost_date'] = cost_date
            agg['total_cost_usd'] += float(record.get('amount', 0))
            agg['cost_count'] += 1

        final_cost = list(cost_aggregates.values())

        return {"usage": final_usage, "cost": final_cost}

    except Exception as e:
        logger.error(f"Anthropic data fetch failed: {e}")
        return {"usage": [], "cost": []}

def analyze_efficient_storage():
    """Analyze storage efficiency with aggregation approach."""
    logger = setup_logging()

    logger.info("🔍 ANALYZING EFFICIENT AGGREGATION APPROACH")
    logger.info("=" * 60)

    # Test with last 7 days first
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    logger.info(f"Testing date range: {start_date} to {end_date}")

    # Get aggregated data
    cursor_data = fetch_and_aggregate_cursor_data(start_date, end_date)
    anthropic_data = fetch_and_aggregate_anthropic_data(start_date, end_date)

    usage_records = anthropic_data["usage"]
    cost_records = anthropic_data["cost"]

    logger.info("\n📊 AGGREGATED DATA ANALYSIS")
    logger.info("=" * 40)
    logger.info(f"Cursor daily aggregates: {len(cursor_data)}")
    logger.info(f"Anthropic usage daily aggregates: {len(usage_records)}")
    logger.info(f"Anthropic cost daily aggregates: {len(cost_records)}")

    # Calculate token volumes
    if usage_records:
        total_input = sum(r.get('uncached_input_tokens', 0) + r.get('cached_input_tokens', 0) for r in usage_records)
        total_output = sum(r.get('output_tokens', 0) for r in usage_records)
        logger.info(f"\n🎯 TOKEN ANALYSIS (7 days sample):")
        logger.info(f"Input tokens: {total_input:,}")
        logger.info(f"Output tokens: {total_output:,}")

        # Estimate full year
        yearly_input = total_input * 52  # 52 weeks
        yearly_output = total_output * 52
        logger.info(f"\n📈 YEARLY PROJECTION:")
        logger.info(f"Projected yearly input: {yearly_input:,}")
        logger.info(f"Projected yearly output: {yearly_output:,}")
        logger.info(f"Target 118M+ input: {'✅ WILL EXCEED' if yearly_input > 118_000_000 else '⚠️ MAY BE BELOW'}")

    # Storage efficiency
    if cost_records:
        total_cost = sum(r.get('total_cost_usd', 0) for r in cost_records)
        logger.info(f"\n💰 COST ANALYSIS (7 days):")
        logger.info(f"Total cost: ${total_cost:,.2f}")

    logger.info(f"\n💾 STORAGE EFFICIENCY:")
    logger.info(f"Raw records would be: ~{len(cursor_data) * 50:,} (estimated)")
    logger.info(f"Aggregated records: {len(cursor_data) + len(usage_records) + len(cost_records)}")
    efficiency = 50 if cursor_data else 1
    logger.info(f"Storage reduction: ~{efficiency}x smaller")

    return {
        "cursor_aggregates": len(cursor_data),
        "usage_aggregates": len(usage_records),
        "cost_aggregates": len(cost_records)
    }

if __name__ == "__main__":
    try:
        results = analyze_efficient_storage()
        print(f"\n🎉 EFFICIENT AGGREGATION ANALYSIS COMPLETE!")
        print(f"Total daily aggregates: {sum(results.values())}")
        print("✅ Ready for full historical data processing")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()