#!/usr/bin/env python3
"""Simple test script for real API connections."""

import os
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_cursor_api():
    """Test Cursor API connection."""
    print("\n🧪 TESTING CURSOR API")
    print("-" * 30)

    api_key = os.getenv("CURSOR_API_KEY_SECRET")
    if not api_key:
        print("❌ Cursor API key not found")
        return False

    print(f"✓ API key loaded: {api_key[:12]}...")

    # Test API call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Try different endpoints and parameters
    endpoints_to_try = [
        "/teams/daily-usage-data",
        "/teams/usage",
        "/admin/usage",
        "/usage"
    ]

    for endpoint in endpoints_to_try:
        try:
            print(f"Trying endpoint: {endpoint}")
            response = requests.get(
                f"https://api.cursor.com{endpoint}",
                headers=headers,
                timeout=30
            )
            print(f"Response status: {response.status_code}")

            if response.status_code != 404:
                print(f"Response: {response.text[:200]}...")
                if response.status_code == 200:
                    return True

        except Exception as e:
            print(f"Request failed: {e}")
            continue

        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text[:500]}...")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS! Retrieved {len(data.get('data', []))} records")

            if data.get('data'):
                sample = data['data'][0]
                print(f"Sample record:")
                print(f"  Email: {sample.get('email', 'N/A')}")
                print(f"  Total Lines Added: {sample.get('totalLinesAdded', 0)}")
                print(f"  Accepted Lines: {sample.get('acceptedLinesAdded', 0)}")

            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def test_anthropic_api():
    """Test Anthropic API connection."""
    print("\n🧪 TESTING ANTHROPIC API")
    print("-" * 30)

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

    # Test usage endpoint with different parameter formats
    params_formats = [
        {
            "starting_at": (date.today() - timedelta(days=3)).isoformat(),
            "ending_at": date.today().isoformat()
        },
        {
            "start_date": (date.today() - timedelta(days=3)).isoformat(),
            "end_date": date.today().isoformat()
        },
        {
            "from": (date.today() - timedelta(days=3)).isoformat(),
            "to": date.today().isoformat()
        }
    ]

    try:
        for i, params in enumerate(params_formats):
            print(f"Testing usage endpoint (format {i+1})...")
            print(f"Parameters: {params}")

            response = requests.get(
                "https://api.anthropic.com/v1/organizations/usage_report/messages",
                headers=headers,
                params=params,
                timeout=30
            )

            print(f"Usage response status: {response.status_code}")
            print(f"Usage response: {response.text[:300]}...")

            if response.status_code == 200:
                break
            elif response.status_code != 400:
                print(f"Unexpected status: {response.status_code}")
                break

        if response.status_code == 200:
            usage_data = response.json()
            print(f"✅ SUCCESS! Retrieved {len(usage_data.get('data', []))} usage records")

            if usage_data.get('data'):
                sample = usage_data['data'][0]
                print(f"Sample usage record:")
                print(f"  API Key ID: {sample.get('api_key_id', 'N/A')}")
                print(f"  Model: {sample.get('model', 'N/A')}")
                print(f"  Input Tokens: {sample.get('uncached_input_tokens', 0)}")
                print(f"  Output Tokens: {sample.get('output_tokens', 0)}")

        # Test cost endpoint
        print("\nTesting cost endpoint...")
        cost_response = requests.get(
            "https://api.anthropic.com/v1/organizations/cost_report",
            headers=headers,
            params=params,
            timeout=30
        )

        print(f"Cost response status: {cost_response.status_code}")
        print(f"Cost response: {cost_response.text[:300]}...")

        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            print(f"✅ SUCCESS! Retrieved {len(cost_data.get('data', []))} cost records")

            if cost_data.get('data'):
                sample_cost = cost_data['data'][0]
                print(f"Sample cost record:")
                print(f"  API Key ID: {sample_cost.get('api_key_id', 'N/A')}")
                print(f"  Model: {sample_cost.get('model', 'N/A')}")
                if 'cost_breakdown' in sample_cost:
                    breakdown = sample_cost['cost_breakdown']
                    total = sum(breakdown.values())
                    print(f"  Total Cost: ${total:.6f}")

        return response.status_code == 200 and cost_response.status_code == 200

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def main():
    """Run all API tests."""
    print("🚀 AI USAGE ANALYTICS - REAL API TESTING")
    print("=" * 60)

    # Test results
    cursor_success = test_cursor_api()
    anthropic_success = test_anthropic_api()

    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)

    results = [
        ("Cursor API", cursor_success),
        ("Anthropic API", anthropic_success)
    ]

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 ALL API CONNECTIONS WORKING!")
        print("✓ Real data is available from both platforms")
        print("✓ Ready for Google Sheets setup")
        print("✓ Can proceed with full pipeline testing")
    else:
        print("⚠️  API connection issues detected")
        print("Please check:")
        print("- API keys are correct and active")
        print("- API endpoints are accessible")
        print("- Account has proper permissions")

    return all_passed


if __name__ == "__main__":
    main()