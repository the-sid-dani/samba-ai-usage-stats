#!/usr/bin/env python3
"""Test Cursor API with correct parameters from documentation."""

import os
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()


def test_cursor_api_corrected():
    """Test Cursor API with correct POST method and authentication."""
    print("\n🧪 TESTING CURSOR API (CORRECTED)")
    print("-" * 40)

    api_key = os.getenv("CURSOR_API_KEY_SECRET")
    if not api_key:
        print("❌ Cursor API key not found")
        return False

    print(f"✓ API key loaded: {api_key[:12]}...")

    # Correct authentication: Basic auth with API key as username, empty password
    auth = (api_key, "")

    headers = {
        "Content-Type": "application/json"
    }

    # Get data for last 7 days (timestamps in milliseconds)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    payload = {
        "startDate": int(start_date.timestamp() * 1000),  # Convert to milliseconds
        "endDate": int(end_date.timestamp() * 1000)
    }

    try:
        print("Making POST request to /teams/daily-usage-data...")
        print(f"Payload: {payload}")

        response = requests.post(
            "https://api.cursor.com/teams/daily-usage-data",
            auth=auth,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS! Retrieved Cursor data")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

            if isinstance(data, dict) and 'data' in data:
                records = data['data']
                print(f"📊 Found {len(records)} usage records")

                if records:
                    sample = records[0]
                    print(f"✓ Sample record:")
                    print(f"  Email: {sample.get('email', 'N/A')}")
                    print(f"  Total Lines Added: {sample.get('totalLinesAdded', 0):,}")
                    print(f"  Accepted Lines: {sample.get('acceptedLinesAdded', 0):,}")
                    print(f"  Total Accepts: {sample.get('totalAccepts', 0)}")
                    print(f"  Subscription Reqs: {sample.get('subscriptionIncludedReqs', 0)}")
                    print(f"  Usage-based Reqs: {sample.get('usageBasedReqs', 0)}")

                    # Show all users
                    users = {record.get('email') for record in records if record.get('email')}
                    print(f"✓ Users found: {len(users)}")
                    for user in sorted(users):
                        print(f"  - {user}")

            else:
                print(f"Response structure: {data}")

            return True

        elif response.status_code == 401:
            print("❌ Authentication failed - check API key permissions")

        elif response.status_code == 403:
            print("❌ Access forbidden - API key may not have admin permissions")

        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")

        return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def test_anthropic_api_corrected():
    """Test Anthropic API with corrected parameters."""
    print("\n🧪 TESTING ANTHROPIC API (CORRECTED)")
    print("-" * 40)

    api_key = os.getenv("ANTHROPIC_ADMIN_KEY_SECRET")
    if not api_key:
        print("❌ Anthropic API key not found")
        return False

    print(f"✓ API key loaded: {api_key[:20]}...")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    # Correct parameters from previous success
    params = {
        "starting_at": (date.today() - timedelta(days=7)).isoformat(),
        "ending_at": date.today().isoformat()
    }

    try:
        print("Testing usage endpoint...")
        print(f"Parameters: {params}")

        response = requests.get(
            "https://api.anthropic.com/v1/organizations/usage_report/messages",
            headers=headers,
            params=params,
            timeout=30
        )

        print(f"Usage response status: {response.status_code}")

        if response.status_code == 200:
            usage_data = response.json()
            print(f"✅ SUCCESS! Retrieved {len(usage_data.get('data', []))} usage records")

            if usage_data.get('data'):
                sample = usage_data['data'][0]
                print(f"✓ Sample usage record:")
                results = sample.get('results', [])
                if results:
                    result = results[0]
                    print(f"  Uncached Input Tokens: {result.get('uncached_input_tokens', 0):,}")
                    print(f"  Output Tokens: {result.get('output_tokens', 0):,}")
                    print(f"  Cache Read Tokens: {result.get('cache_read_input_tokens', 0):,}")

                    # Show date range
                    print(f"  Period: {sample.get('starting_at')} to {sample.get('ending_at')}")

        # Test cost endpoint
        print("\nTesting cost endpoint...")
        cost_response = requests.get(
            "https://api.anthropic.com/v1/organizations/cost_report",
            headers=headers,
            params=params,
            timeout=30
        )

        print(f"Cost response status: {cost_response.status_code}")

        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            print(f"✅ SUCCESS! Retrieved {len(cost_data.get('data', []))} cost records")

            if cost_data.get('data'):
                total_cost = 0
                for record in cost_data['data']:
                    results = record.get('results', [])
                    for result in results:
                        amount = float(result.get('amount', 0))
                        total_cost += amount

                print(f"✓ Total cost (7 days): ${total_cost/1000000:.2f}")  # Convert from micro-dollars

            return True

        return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def main():
    """Run corrected API tests."""
    print("🚀 AI USAGE ANALYTICS - CORRECTED API TESTING")
    print("=" * 60)

    cursor_success = test_cursor_api_corrected()
    anthropic_success = test_anthropic_api_corrected()

    print("\n" + "="*60)
    print("📊 CORRECTED TEST RESULTS")
    print("="*60)
    print(f"Cursor API: {'✅ WORKING' if cursor_success else '❌ STILL ISSUES'}")
    print(f"Anthropic API: {'✅ WORKING' if anthropic_success else '❌ STILL ISSUES'}")

    if cursor_success and anthropic_success:
        print("\n🎉 BOTH APIs WORKING!")
        print("✓ Ready for full pipeline testing")
        print("✓ Data transformation can proceed")

    elif anthropic_success:
        print("\n✅ Anthropic API working - can proceed with partial testing")
        print("❓ Cursor API needs further investigation")

    else:
        print("\n⚠️  API issues remain - need to resolve authentication/endpoints")

    return cursor_success, anthropic_success


if __name__ == "__main__":
    main()