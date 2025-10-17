#!/usr/bin/env python3
"""
Debug Anthropic billing API to see what data we're actually getting.
"""

import requests
from datetime import datetime, date, timedelta
import json

# Read API key
with open('/tmp/anthropic_key.txt', 'r') as f:
    API_KEY = f.read().strip()

def test_billing_api():
    """Test different date ranges and endpoints to find the data."""
    print("🔍 DEBUGGING ANTHROPIC BILLING API")
    print("="*60)

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Test 1: Last 30 days
    print("\n1️⃣ Testing last 30 days...")
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    print(f"   Date range: {params['starting_at']} to {params['ending_at']}")

    # Test cost endpoint
    cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
    response = requests.get(cost_url, headers=headers, params=params, timeout=60)

    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   Response keys: {list(data.keys())}")

        # Analyze the data structure
        if 'data' in data:
            print(f"   Number of buckets: {len(data['data'])}")

            total_records = 0
            total_cost = 0
            dates_with_data = []

            for bucket in data['data']:
                bucket_date = bucket.get('starting_at', 'unknown')
                results = bucket.get('results', [])

                if results:
                    dates_with_data.append(bucket_date)
                    total_records += len(results)

                    for record in results:
                        # Debug first record structure
                        if total_records == 1:
                            print(f"\n   📊 Sample record structure:")
                            for key, value in record.items():
                                print(f"      {key}: {value}")

                        # Amount could be in different formats
                        amount = record.get('amount', 0)
                        if isinstance(amount, str):
                            amount = float(amount)

                        # Check if already in dollars or micro-dollars
                        if amount > 0:
                            # If amount is very large, it's likely micro-dollars
                            if amount > 1000:
                                amount = amount / 1000000
                            total_cost += amount

            print(f"\n   ✅ Results:")
            print(f"      Total records: {total_records}")
            print(f"      Total cost: ${total_cost:,.2f}")
            print(f"      Dates with data: {dates_with_data[:5]}...")  # Show first 5
            print(f"      Has more pages: {data.get('has_more', False)}")

            if data.get('has_more'):
                print(f"      Next page token: {data.get('next_page_token', 'N/A')[:20]}...")

    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

    # Test 2: Try different date ranges
    print("\n2️⃣ Testing different date ranges...")

    test_ranges = [
        ("Last 7 days", 7),
        ("Last 60 days", 60),
        ("Last 90 days", 90),
        ("Year to date", (date.today() - date(2025, 1, 1)).days),
        ("Since Sep 1", (date.today() - date(2025, 9, 1)).days)
    ]

    for range_name, days in test_ranges:
        print(f"\n   Testing {range_name}...")
        start = date.today() - timedelta(days=days)
        params = {
            "starting_at": start.strftime("%Y-%m-%d"),
            "ending_at": date.today().strftime("%Y-%m-%d")
        }

        try:
            response = requests.get(cost_url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()

                total_cost = 0
                record_count = 0

                for bucket in data.get('data', []):
                    for record in bucket.get('results', []):
                        amount = record.get('amount', 0)
                        if isinstance(amount, str):
                            amount = float(amount)
                        if amount > 1000:
                            amount = amount / 1000000
                        total_cost += amount
                        record_count += 1

                print(f"      ✅ Records: {record_count}, Cost: ${total_cost:,.2f}")
            else:
                print(f"      ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"      ❌ Exception: {e}")

    # Test 3: Check usage endpoint too
    print("\n3️⃣ Testing usage endpoint...")
    usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"

    params = {
        "starting_at": (date.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "ending_at": date.today().strftime("%Y-%m-%d")
    }

    response = requests.get(usage_url, headers=headers, params=params, timeout=60)

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Usage endpoint working")
        print(f"   Number of buckets: {len(data.get('data', []))}")

        total_tokens = 0
        for bucket in data.get('data', []):
            for record in bucket.get('results', []):
                total_tokens += record.get('uncached_input_tokens', 0)
                total_tokens += record.get('output_tokens', 0)

        print(f"   Total tokens: {total_tokens:,}")
    else:
        print(f"   ❌ Usage endpoint error: {response.status_code}")

    # Test 4: Check organization info
    print("\n4️⃣ Checking organization endpoint...")
    org_url = "https://api.anthropic.com/v1/organizations"

    try:
        response = requests.get(org_url, headers=headers, timeout=30)
        if response.status_code == 200:
            print(f"   ✅ Organization endpoint accessible")
            org_data = response.json()
            print(f"   Response type: {type(org_data)}")
            if isinstance(org_data, dict):
                print(f"   Keys: {list(org_data.keys())[:5]}")
        else:
            print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_billing_api()