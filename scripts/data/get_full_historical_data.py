#!/usr/bin/env python3
"""
Get Full Historical Data from Jan 1, 2025
Properly extracts ALL usage records from API responses with pagination.
"""

import requests
import json
import time
from datetime import datetime, date, timedelta
from google.cloud import secretmanager, bigquery

def get_secret(secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def get_all_anthropic_usage_data(start_date=date(2025, 1, 1)):
    """Get ALL Anthropic usage data with proper pagination and record extraction."""
    print(f"🔍 Getting ALL Anthropic usage data from {start_date}")

    api_key = get_secret("anthropic-api-key")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    end_date = datetime.now().date()

    # Get usage data
    usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
    all_usage_records = []

    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    page_count = 0
    while True:
        page_count += 1
        print(f"📄 Fetching usage page {page_count}...")

        response = requests.get(usage_url, headers=headers, params=params, timeout=60)

        if response.status_code != 200:
            print(f"❌ Usage API error: {response.status_code} - {response.text[:200]}")
            break

        data = response.json()
        daily_buckets = data.get('data', [])

        # Extract usage records from each daily bucket
        page_records = 0
        for daily_bucket in daily_buckets:
            daily_results = daily_bucket.get('results', [])
            page_records += len(daily_results)

            # Process each usage record
            for usage_record in daily_results:
                # Add metadata from daily bucket
                usage_record['bucket_start'] = daily_bucket.get('starting_at')
                usage_record['bucket_end'] = daily_bucket.get('ending_at')
                all_usage_records.append(usage_record)

        print(f"  Found {page_records} usage records in {len(daily_buckets)} daily buckets")

        # Check for pagination
        has_more = data.get('has_more', False)
        if has_more and data.get('next_page'):
            params['page'] = data['next_page']
            time.sleep(0.5)  # Rate limiting
        else:
            break

    print(f"✅ Total usage records: {len(all_usage_records)}")

    # Get cost data
    cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
    all_cost_records = []

    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    page_count = 0
    while True:
        page_count += 1
        print(f"💰 Fetching cost page {page_count}...")

        response = requests.get(cost_url, headers=headers, params=params, timeout=60)

        if response.status_code != 200:
            print(f"❌ Cost API error: {response.status_code} - {response.text[:200]}")
            break

        data = response.json()
        daily_buckets = data.get('data', [])

        # Extract cost records from each daily bucket
        page_records = 0
        for daily_bucket in daily_buckets:
            daily_results = daily_bucket.get('results', [])
            page_records += len(daily_results)

            # Process each cost record
            for cost_record in daily_results:
                # Add metadata from daily bucket
                cost_record['bucket_start'] = daily_bucket.get('starting_at')
                cost_record['bucket_end'] = daily_bucket.get('ending_at')
                all_cost_records.append(cost_record)

        print(f"  Found {page_records} cost records in {len(daily_buckets)} daily buckets")

        # Check for pagination
        has_more = data.get('has_more', False)
        if has_more and data.get('next_page'):
            params['page'] = data['next_page']
            time.sleep(0.5)  # Rate limiting
        else:
            break

    print(f"✅ Total cost records: {len(all_cost_records)}")

    return {"usage": all_usage_records, "cost": all_cost_records}

def get_all_cursor_data(start_date=date(2025, 1, 1)):
    """Get ALL Cursor data from Jan 1, 2025."""
    print(f"🔍 Getting ALL Cursor data from {start_date}")

    api_key = get_secret("cursor-api-key")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    end_date = datetime.now().date()
    all_cursor_records = []

    # Process in chunks (API might have limits)
    current_start = start_date
    chunk_days = 30  # 30-day chunks

    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_days), end_date)

        print(f"📅 Fetching Cursor data: {current_start} to {current_end}")

        url = "https://api.cursor.com/teams/daily-usage-data"
        data = {
            "start_date": current_start.strftime("%Y-%m-%d"),
            "end_date": current_end.strftime("%Y-%m-%d")
        }

        response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code == 200:
            result = response.json()
            records = result.get('data', [])
            all_cursor_records.extend(records)
            print(f"  ✅ Got {len(records)} records for this period")
        else:
            print(f"  ❌ Error: {response.status_code} - {response.text[:200]}")

        current_start = current_end + timedelta(days=1)
        time.sleep(0.5)  # Rate limiting

    print(f"✅ Total Cursor records: {len(all_cursor_records)}")
    return all_cursor_records

def analyze_data_volume():
    """Analyze the true data volume we're getting."""
    print("🔍 ANALYZING FULL DATA VOLUME FROM JAN 1, 2025")
    print("=" * 60)

    # Get all data
    cursor_data = get_all_cursor_data()
    anthropic_data = get_all_anthropic_usage_data()

    usage_records = anthropic_data["usage"]
    cost_records = anthropic_data["cost"]

    print("\n📊 DATA VOLUME ANALYSIS")
    print("=" * 40)
    print(f"Cursor records: {len(cursor_data):,}")
    print(f"Anthropic usage records: {len(usage_records):,}")
    print(f"Anthropic cost records: {len(cost_records):,}")
    print(f"TOTAL RECORDS: {len(cursor_data) + len(usage_records) + len(cost_records):,}")

    # Analyze Anthropic token volumes
    if usage_records:
        total_input_tokens = sum(r.get('uncached_input_tokens', 0) + r.get('cached_input_tokens', 0) for r in usage_records)
        total_output_tokens = sum(r.get('output_tokens', 0) for r in usage_records)
        print(f"\n🎯 ANTHROPIC TOKEN ANALYSIS:")
        print(f"Total input tokens: {total_input_tokens:,}")
        print(f"Total output tokens: {total_output_tokens:,}")
        print(f"Expected 118M+ input: {'✅ EXCEEDED' if total_input_tokens > 118_000_000 else '⚠️ BELOW TARGET'}")
        print(f"Expected 5.4M+ output: {'✅ EXCEEDED' if total_output_tokens > 5_400_000 else '⚠️ BELOW TARGET'}")

    # Analyze costs
    if cost_records:
        total_cost = sum(float(r.get('amount', 0)) for r in cost_records)
        print(f"\n💰 COST ANALYSIS:")
        print(f"Total cost: ${total_cost:,.2f}")

    return {
        "cursor_records": len(cursor_data),
        "anthropic_usage": len(usage_records),
        "anthropic_cost": len(cost_records),
        "total_input_tokens": total_input_tokens if usage_records else 0,
        "total_output_tokens": total_output_tokens if usage_records else 0,
        "total_cost": total_cost if cost_records else 0
    }

if __name__ == "__main__":
    try:
        results = analyze_data_volume()

        print("\n🎉 FULL DATA ANALYSIS COMPLETE!")
        print("=" * 60)

        if results["total_input_tokens"] > 118_000_000:
            print("🚀 SUCCESS: Found the massive Anthropic dataset!")
            print(f"   Input tokens: {results['total_input_tokens']:,}")
            print(f"   Output tokens: {results['total_output_tokens']:,}")
        else:
            print("⚠️ May need to check date range or API permissions")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()