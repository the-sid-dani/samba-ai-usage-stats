#!/usr/bin/env python3
"""
Load the REAL Anthropic data with the massive token volumes we found.
Focus on July-August 2025 where the actual usage data exists.
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

def get_real_anthropic_data():
    """Get the REAL Anthropic data from July-August where we found 100M+ tokens."""
    print("🎯 GETTING REAL ANTHROPIC DATA (July-August 2025)")
    print("=" * 60)

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
        print(f"✅ Loaded {len(api_key_mapping)} API key mappings")
    except:
        api_key_mapping = {}
        print("⚠️ No platform mapping file found")

    # Focus on the period where we found real data (July-September)
    end_date = date(2025, 9, 27)
    start_date = date(2025, 7, 1)  # July 1st

    print(f"📅 Date range: {start_date} to {end_date}")

    # Get usage data
    usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    all_usage_records = []
    total_tokens = 0

    # Get multiple pages of real data
    page_count = 0
    while page_count < 5:  # Get more pages to find the real data
        page_count += 1
        print(f"📄 Fetching usage page {page_count}...")

        response = requests.get(usage_url, headers=headers, params=params, timeout=60)
        if response.status_code != 200:
            print(f"❌ API error: {response.status_code}")
            break

        data = response.json()
        daily_buckets = data.get('data', [])

        page_records = 0
        page_tokens = 0

        for bucket in daily_buckets:
            bucket_date = bucket.get('starting_at', '')[:10]
            results = bucket.get('results', [])

            if results:  # Only process buckets with actual data
                print(f"  📅 {bucket_date}: {len(results)} records")

                for record in results:
                    api_key_id = record.get('api_key_id', 'unknown')
                    workspace_id = record.get('workspace_id')

                    # Get token counts
                    input_tokens = record.get('uncached_input_tokens', 0) + record.get('cached_input_tokens', 0)
                    output_tokens = record.get('output_tokens', 0)
                    total_record_tokens = input_tokens + output_tokens

                    if total_record_tokens > 0:  # Only include records with actual usage
                        # Determine platform
                        platform = "claude_api"  # default
                        if api_key_id in api_key_mapping:
                            platform = api_key_mapping[api_key_id].get('platform', 'claude_api')
                        elif workspace_id == "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR":
                            platform = "claude_code"

                        # Create BigQuery record
                        bq_record = {
                            "api_key_id": api_key_id or 'org_aggregate',
                            "workspace_id": workspace_id,
                            "model": record.get('model', 'unknown'),
                            "uncached_input_tokens": record.get('uncached_input_tokens', 0),
                            "cached_input_tokens": record.get('cached_input_tokens', 0),
                            "cache_read_input_tokens": record.get('cache_read_input_tokens', 0),
                            "output_tokens": record.get('output_tokens', 0),
                            "usage_date": bucket_date,
                            "usage_hour": 0,  # Default
                            "ingest_date": datetime.now().date().strftime("%Y-%m-%d"),
                            "ingest_timestamp": datetime.now().isoformat(),
                            "request_id": f"real-data-page-{page_count}",
                            "raw_response": json.dumps(record)
                        }

                        all_usage_records.append(bq_record)
                        page_records += 1
                        page_tokens += total_record_tokens

        print(f"    ✅ Page {page_count}: {page_records} records with {page_tokens:,} tokens")
        total_tokens += page_tokens

        # Check for more data
        if not data.get('has_more', False):
            print(f"  📄 No more pages available")
            break

        if data.get('next_page'):
            params['page'] = data['next_page']
        else:
            break

    print(f"\n🎉 REAL DATA SUMMARY:")
    print(f"✅ Total usage records: {len(all_usage_records)}")
    print(f"✅ Total tokens: {total_tokens:,}")
    print(f"✅ Target 100M+ tokens: {'EXCEEDED' if total_tokens > 100_000_000 else 'BELOW'}")

    return all_usage_records

def store_real_data(usage_records):
    """Store the real Anthropic data in BigQuery."""
    if not usage_records:
        print("❌ No real data to store")
        return 0

    print(f"💾 Storing {len(usage_records)} real Anthropic records...")

    client = bigquery.Client(project="ai-workflows-459123")
    table_id = "ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage"

    try:
        table = client.get_table(table_id)

        # Process in batches
        batch_size = 1000
        total_stored = 0

        for i in range(0, len(usage_records), batch_size):
            batch = usage_records[i:i+batch_size]

            errors = client.insert_rows_json(table, batch)

            if not errors:
                total_stored += len(batch)
                print(f"✅ Stored batch {i//batch_size + 1}: {len(batch)} records")
            else:
                print(f"❌ Batch {i//batch_size + 1} errors: {errors[:2]}...")

        return total_stored

    except Exception as e:
        print(f"❌ Storage failed: {e}")
        return 0

def main():
    """Load real Anthropic data with massive token volumes."""
    print("🚀 LOADING REAL ANTHROPIC DATA")
    print("=" * 50)

    try:
        # Get the real historical data
        usage_records = get_real_anthropic_data()

        if not usage_records:
            print("❌ No real data found")
            return False

        # Store in BigQuery
        stored_count = store_real_data(usage_records)

        print(f"\n🎉 REAL DATA LOADED!")
        print(f"✅ Records processed: {len(usage_records)}")
        print(f"✅ Records stored: {stored_count}")

        # Test the unified query
        print(f"\n🔍 Testing unified platform query...")
        client = bigquery.Client(project="ai-workflows-459123")

        test_query = """
        SELECT
            'cursor' as platform,
            COUNT(DISTINCT email) as users,
            SUM(total_lines_added) as activity
        FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
        WHERE ingest_date >= '2025-09-27' AND email LIKE '%samba.tv'

        UNION ALL

        SELECT
            'anthropic' as platform,
            COUNT(DISTINCT api_key_id) as users,
            SUM(uncached_input_tokens + cached_input_tokens + output_tokens) as activity
        FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
        WHERE ingest_date >= '2025-09-27'
        """

        results = list(client.query(test_query).result())

        print(f"Updated platform breakdown:")
        for row in results:
            print(f"  {row.platform}: {row.users} users, {row.activity:,} activity")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Real Anthropic data loading")