#!/usr/bin/env python3
"""Test Anthropic API with broader historical range to find the data."""

import requests
from datetime import datetime, date, timedelta
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def test_anthropic_ranges():
    """Test different date ranges to find where the data is."""
    print("🔍 Testing Anthropic API Date Ranges")
    print("=" * 50)

    api_key = get_secret("anthropic-api-key")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Test different historical ranges
    ranges = [
        ("Last 30 days", 30),
        ("Last 60 days", 60),
        ("Last 90 days", 90),
        ("Since Jan 1, 2025", (datetime.now().date() - date(2025, 1, 1)).days)
    ]

    for range_name, days_back in ranges:
        print(f"\n📅 {range_name} ({days_back} days)")
        print("-" * 30)

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back) if days_back < 365 else date(2025, 1, 1)

        params = {
            "starting_at": start_date.strftime("%Y-%m-%d"),
            "ending_at": end_date.strftime("%Y-%m-%d")
        }

        # Test usage endpoint
        usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
        response = requests.get(usage_url, headers=headers, params=params, timeout=60)

        if response.status_code == 200:
            data = response.json()
            daily_buckets = data.get('data', [])

            total_usage_records = 0
            total_tokens = 0
            days_with_data = 0

            for bucket in daily_buckets:
                results = bucket.get('results', [])
                if results:  # Only count days with actual data
                    days_with_data += 1
                    total_usage_records += len(results)

                    # Sum tokens from this day
                    for record in results:
                        total_tokens += record.get('uncached_input_tokens', 0)
                        total_tokens += record.get('cached_input_tokens', 0)

            print(f"Daily buckets: {len(daily_buckets)}")
            print(f"Days with data: {days_with_data}")
            print(f"Total usage records: {total_usage_records:,}")
            print(f"Total tokens (sample): {total_tokens:,}")
            print(f"Has more pages: {data.get('has_more', False)}")

            if total_usage_records > 0:
                print(f"✅ FOUND DATA! {total_usage_records:,} records, {total_tokens:,} tokens")
            else:
                print("⚠️ No usage data in this range")

        else:
            print(f"❌ API Error: {response.status_code}")

        # Test cost endpoint
        cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
        cost_response = requests.get(cost_url, headers=headers, params=params, timeout=60)

        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            cost_buckets = cost_data.get('data', [])

            total_cost_records = 0
            total_cost = 0

            for bucket in cost_buckets:
                results = bucket.get('results', [])
                total_cost_records += len(results)

                for record in results:
                    total_cost += float(record.get('amount', 0))

            print(f"Cost records: {total_cost_records:,}")
            print(f"Total cost: ${total_cost:,.2f}")

            if total_cost > 0:
                print(f"✅ COST DATA FOUND! {total_cost_records:,} records, ${total_cost:,.2f}")

if __name__ == "__main__":
    test_anthropic_ranges()