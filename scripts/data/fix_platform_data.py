#!/usr/bin/env python3
"""
Fix platform data by adding platform columns and getting historical Anthropic data.
"""

import requests
import json
from datetime import datetime, date, timedelta
from google.cloud import bigquery, secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def add_platform_to_cursor_data():
    """Add platform field to existing Cursor data."""
    print("🔧 Adding platform field to Cursor data...")

    client = bigquery.Client(project="ai-workflows-459123")

    # Update existing Cursor records to have platform = 'cursor'
    query = """
    UPDATE `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    SET raw_response = JSON_SET(raw_response, '$.platform', 'cursor')
    WHERE ingest_date = '2025-09-27'
    """

    try:
        job = client.query(query)
        job.result()
        print("✅ Updated Cursor records with platform field")
        return True
    except Exception as e:
        print(f"❌ Update failed: {e}")
        return False

def get_historical_anthropic_data():
    """Get historical Anthropic data from periods with actual usage."""
    print("🔍 Getting historical Anthropic data with platform mapping...")

    api_key = get_secret("anthropic-api-key")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Load platform mapping
    try:
        with open('anthropic_platform_mapping.json', 'r') as f:
            mapping = json.load(f)
        api_key_mapping = mapping.get('api_keys', {})
    except:
        api_key_mapping = {}

    # Get last 60 days (where we found data)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=60)

    # Get usage data
    usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    usage_records = []
    cost_records = []

    # Get usage data with pagination
    page_count = 0
    while page_count < 3:  # Limit to first 3 pages for now
        page_count += 1
        print(f"📄 Fetching usage page {page_count}...")

        response = requests.get(usage_url, headers=headers, params=params, timeout=60)
        if response.status_code != 200:
            print(f"❌ Usage API error: {response.status_code}")
            break

        data = response.json()
        daily_buckets = data.get('data', [])

        for bucket in daily_buckets:
            bucket_date = bucket.get('starting_at', '')[:10]
            results = bucket.get('results', [])

            print(f"  📅 {bucket_date}: {len(results)} usage records")

            for record in results:
                api_key_id = record.get('api_key_id', 'unknown')

                # Determine platform
                platform = "claude_api"  # default
                if api_key_id in api_key_mapping:
                    platform = api_key_mapping[api_key_id].get('platform', 'claude_api')
                elif record.get('workspace_id') == "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR":
                    platform = "claude_code"

                # Create BigQuery record
                bq_record = {
                    "api_key_id": api_key_id,
                    "usage_date": bucket_date,
                    "model": record.get('model', 'unknown'),
                    "uncached_input_tokens": record.get('uncached_input_tokens', 0),
                    "cached_input_tokens": record.get('cached_input_tokens', 0),
                    "cache_read_input_tokens": record.get('cache_read_input_tokens', 0),
                    "output_tokens": record.get('output_tokens', 0),
                    "platform": platform,  # KEY: Platform distinction
                    "ingest_date": datetime.now().date().strftime("%Y-%m-%d"),
                    "ingest_timestamp": datetime.now().isoformat(),
                    "request_id": f"historical-{page_count}",
                    "raw_response": json.dumps(record)
                }
                usage_records.append(bq_record)

        if not data.get('has_more', False):
            break

        if data.get('next_page'):
            params['page'] = data['next_page']

    # Get cost data
    cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
    cost_params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    print("💰 Fetching cost data...")
    cost_response = requests.get(cost_url, headers=headers, params=cost_params, timeout=60)

    if cost_response.status_code == 200:
        cost_data = cost_response.json()
        cost_buckets = cost_data.get('data', [])

        for bucket in cost_buckets:
            bucket_date = bucket.get('starting_at', '')[:10]
            results = bucket.get('results', [])

            for record in results:
                bq_record = {
                    "api_key_id": "org_aggregate",  # Cost is org-level
                    "cost_date": bucket_date,
                    "model": record.get('model', 'unknown'),
                    "cost_usd": float(record.get('amount', 0)),
                    "cost_type": record.get('cost_type', 'usage'),
                    "platform": "anthropic_aggregate",  # Org-level costs
                    "ingest_date": datetime.now().date().strftime("%Y-%m-%d"),
                    "ingest_timestamp": datetime.now().isoformat(),
                    "request_id": "historical-cost",
                    "raw_response": json.dumps(record)
                }
                cost_records.append(bq_record)

    print(f"✅ Prepared {len(usage_records)} Anthropic usage records")
    print(f"✅ Prepared {len(cost_records)} Anthropic cost records")

    return usage_records, cost_records

def store_platform_data(usage_records, cost_records):
    """Store the platform-aware data in BigQuery."""
    print("💾 Storing platform-aware data in BigQuery...")

    client = bigquery.Client(project="ai-workflows-459123")
    total_stored = 0

    # Store usage records
    if usage_records:
        try:
            table_id = "ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage"
            table = client.get_table(table_id)

            # Process in batches
            batch_size = 1000
            for i in range(0, len(usage_records), batch_size):
                batch = usage_records[i:i+batch_size]
                errors = client.insert_rows_json(table, batch)

                if not errors:
                    total_stored += len(batch)
                    print(f"✅ Stored usage batch {i//batch_size + 1}: {len(batch)} records")
                else:
                    print(f"❌ Usage batch errors: {errors[:3]}...")

        except Exception as e:
            print(f"❌ Usage storage failed: {e}")

    # Store cost records
    if cost_records:
        try:
            table_id = "ai-workflows-459123.ai_usage_analytics.raw_anthropic_cost"
            table = client.get_table(table_id)

            errors = client.insert_rows_json(table, cost_records)

            if not errors:
                total_stored += len(cost_records)
                print(f"✅ Stored {len(cost_records)} cost records")
            else:
                print(f"❌ Cost storage errors: {errors[:3]}...")

        except Exception as e:
            print(f"❌ Cost storage failed: {e}")

    return total_stored

def main():
    """Execute platform data fix."""
    print("🎯 FIXING PLATFORM DATA FOR DASHBOARD")
    print("=" * 50)

    try:
        # Get historical Anthropic data with platform mapping
        usage_records, cost_records = get_historical_anthropic_data()

        # Store in BigQuery
        total_stored = store_platform_data(usage_records, cost_records)

        print(f"\n🎉 PLATFORM DATA FIX COMPLETE!")
        print(f"✅ Anthropic usage records: {len(usage_records)}")
        print(f"✅ Anthropic cost records: {len(cost_records)}")
        print(f"✅ Total stored: {total_stored}")

        # Test query
        print(f"\n🔍 Testing platform query...")
        client = bigquery.Client(project="ai-workflows-459123")

        query = """
        SELECT
            'cursor' as platform,
            COUNT(*) as records,
            COUNT(DISTINCT email) as users
        FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
        WHERE ingest_date = '2025-09-27'

        UNION ALL

        SELECT
            platform,
            COUNT(*) as records,
            COUNT(DISTINCT api_key_id) as api_keys
        FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
        WHERE ingest_date = '2025-09-27'
        GROUP BY platform
        """

        results = list(client.query(query).result())

        print(f"Platform breakdown:")
        for row in results:
            print(f"  {row.platform}: {row.records} records")

        return True

    except Exception as e:
        print(f"❌ Platform fix failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)