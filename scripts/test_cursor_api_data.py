#!/usr/bin/env python3
"""
Test Cursor API to see exactly what data we get back.
Let's understand what Cursor reports for costs and usage.
"""

import os
import requests
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import json

# Try to get Cursor API key
def get_cursor_api_key():
    """Get Cursor API key from various sources."""
    # Try Secret Manager first
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/ai-workflows-459123/secrets/cursor-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except:
        pass

    # Try environment variable
    api_key = os.getenv("CURSOR_API_KEY_SECRET")
    if api_key:
        return api_key

    # Try .env file
    try:
        with open('.env', 'r') as f:
            for line in f:
                if 'CURSOR_API_KEY' in line:
                    return line.split('=')[1].strip()
    except:
        pass

    return None

def test_cursor_api():
    """Test what the Cursor API actually returns."""
    print("🔍 TESTING CURSOR API - STEP BY STEP")
    print("="*60)

    api_key = get_cursor_api_key()
    if not api_key:
        print("❌ No Cursor API key found")
        return

    print(f"✅ Found Cursor API key: {api_key[:20]}...")

    # Cursor uses Basic Auth with API key as username
    auth = (api_key, "")
    headers = {"Content-Type": "application/json"}

    # Test different date ranges
    print("\n📊 Testing Cursor API responses for different months:\n")

    # Test last 6 months individually
    current_date = date.today()

    monthly_data = {}

    for i in range(6):
        # Calculate month start and end
        month_end = current_date - relativedelta(months=i)
        month_start = month_end - relativedelta(months=1)

        # Adjust if we go into the future
        if month_end > date.today():
            month_end = date.today()

        month_label = month_end.strftime('%b %Y')

        print(f"📅 {month_label} ({month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')})")

        payload = {
            "startDate": int(datetime.combine(month_start, datetime.min.time()).timestamp() * 1000),  # milliseconds
            "endDate": int(datetime.combine(month_end, datetime.min.time()).timestamp() * 1000)
        }

        try:
            response = requests.post(
                "https://api.cursor.com/teams/daily-usage-data",
                auth=auth,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Analyze the response structure
                print(f"  Status: ✅ 200 OK")

                if isinstance(data, dict) and 'data' in data:
                    records = data['data']
                    print(f"  Records found: {len(records)}")

                    # Calculate totals for this month
                    total_usage_based_reqs = 0
                    total_subscription_reqs = 0
                    total_lines_added = 0
                    total_lines_accepted = 0
                    unique_users = set()

                    for record in records:
                        # Show first record structure
                        if len(monthly_data) == 0 and total_usage_based_reqs == 0:
                            print(f"\n  📋 Sample record structure:")
                            for key, value in record.items():
                                if key != 'email':  # Don't show PII
                                    print(f"    {key}: {value}")
                            print()

                        total_usage_based_reqs += record.get('usageBasedReqs', 0)
                        total_subscription_reqs += record.get('subscriptionIncludedReqs', 0)
                        total_lines_added += record.get('totalLinesAdded', 0)
                        total_lines_accepted += record.get('acceptedLinesAdded', 0)

                        if record.get('email'):
                            unique_users.add(record.get('email'))

                    monthly_data[month_label] = {
                        'usage_based_reqs': total_usage_based_reqs,
                        'subscription_reqs': total_subscription_reqs,
                        'lines_added': total_lines_added,
                        'lines_accepted': total_lines_accepted,
                        'users': len(unique_users)
                    }

                    print(f"  📊 Monthly totals:")
                    print(f"    Usage-based requests: {total_usage_based_reqs:,}")
                    print(f"    Subscription requests: {total_subscription_reqs:,}")
                    print(f"    Lines added: {total_lines_added:,}")
                    print(f"    Lines accepted: {total_lines_accepted:,}")
                    print(f"    Active users: {len(unique_users)}")

                    # IMPORTANT: Does Cursor provide cost data?
                    print(f"  💰 Cost data in response: ", end="")

                    # Check if any cost fields exist
                    cost_fields = ['cost', 'amount', 'price', 'charge', 'fee', 'billing']
                    has_cost = False
                    for record in records:
                        for field in cost_fields:
                            if field in record:
                                print(f"YES - field '{field}' found!")
                                has_cost = True
                                break
                        if has_cost:
                            break

                    if not has_cost:
                        print("NO - Only usage metrics, no cost data")

                else:
                    print(f"  Unexpected response structure: {type(data)}")
                    print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

            else:
                print(f"  Status: ❌ {response.status_code}")
                print(f"  Error: {response.text[:200]}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")

        print()

    # Summary
    print("\n" + "="*60)
    print("📊 CURSOR API SUMMARY")
    print("="*60)

    if monthly_data:
        print("\n✅ Data Retrieved Successfully")
        print("\n📈 Monthly Usage (API Requests):")

        total_api_reqs = 0
        for month, data in monthly_data.items():
            api_reqs = data['usage_based_reqs']
            total_api_reqs += api_reqs
            print(f"  {month}: {api_reqs:,} usage-based requests")

        print(f"\n  TOTAL: {total_api_reqs:,} usage-based requests")

        print("\n⚠️ IMPORTANT FINDINGS:")
        print("  1. Cursor API returns USAGE data (requests, lines of code)")
        print("  2. Cursor API does NOT return COST/BILLING data")
        print("  3. We can see usage-based requests vs subscription requests")
        print("  4. To calculate costs, we need the pricing model")

        print("\n💡 COST ESTIMATION:")
        print("  Without pricing info from Cursor, we cannot calculate exact costs")
        print("  The 'usageBasedReqs' likely incur additional charges")
        print("  The 'subscriptionIncludedReqs' are likely covered by the $50/month")

    else:
        print("❌ No data retrieved from Cursor API")

if __name__ == "__main__":
    test_cursor_api()