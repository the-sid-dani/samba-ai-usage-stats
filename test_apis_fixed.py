#!/usr/bin/env python3
"""Test real API connections with correct parameters."""

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

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Try different endpoint variations
    endpoints = [
        "/admin/teams/usage",
        "/teams/usage",
        "/admin/usage",
        "/usage",
        "/teams/daily-usage-data"
    ]

    for endpoint in endpoints:
        try:
            print(f"Trying: https://api.cursor.com{endpoint}")
            response = requests.get(
                f"https://api.cursor.com{endpoint}",
                headers=headers,
                timeout=30
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS! Data: {data}")
                return True
            elif response.status_code != 404:
                print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"Error: {e}")

    print("❌ All Cursor endpoints returned 404 or errors")
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

    # Try different parameter formats for usage endpoint
    param_formats = [
        {
            "starting_at": (date.today() - timedelta(days=7)).isoformat(),
            "ending_at": date.today().isoformat()
        },
        {
            "start_date": (date.today() - timedelta(days=7)).isoformat(),
            "end_date": date.today().isoformat()
        }
    ]

    print("Testing usage endpoint...")
    for i, params in enumerate(param_formats):
        try:
            print(f"Format {i+1}: {params}")
            response = requests.get(
                "https://api.anthropic.com/v1/organizations/usage_report/messages",
                headers=headers,
                params=params,
                timeout=30
            )

            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300]}")

            if response.status_code == 200:
                usage_data = response.json()
                print(f"✅ SUCCESS! Usage records: {len(usage_data.get('data', []))}")
                break

        except Exception as e:
            print(f"Error: {e}")

    # Try cost endpoint
    print("\nTesting cost endpoint...")
    for i, params in enumerate(param_formats):
        try:
            print(f"Format {i+1}: {params}")
            response = requests.get(
                "https://api.anthropic.com/v1/organizations/cost_report",
                headers=headers,
                params=params,
                timeout=30
            )

            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300]}")

            if response.status_code == 200:
                cost_data = response.json()
                print(f"✅ SUCCESS! Cost records: {len(cost_data.get('data', []))}")
                return True

        except Exception as e:
            print(f"Error: {e}")

    return False


def main():
    """Run API tests."""
    print("🚀 AI USAGE ANALYTICS - API ENDPOINT TESTING")
    print("=" * 60)

    cursor_success = test_cursor_api()
    anthropic_success = test_anthropic_api()

    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)
    print(f"Cursor API: {'✅ WORKING' if cursor_success else '❌ ISSUES'}")
    print(f"Anthropic API: {'✅ WORKING' if anthropic_success else '❌ ISSUES'}")

    if not cursor_success:
        print("\n💡 Cursor API Notes:")
        print("- The endpoint might be different")
        print("- May need specific team ID or different authentication")
        print("- Check Cursor documentation for correct admin endpoints")

    if not anthropic_success:
        print("\n💡 Anthropic API Notes:")
        print("- Admin API endpoints may require organization membership")
        print("- Check if API key has admin permissions")
        print("- Verify endpoint paths in Anthropic admin documentation")

    return cursor_success or anthropic_success


if __name__ == "__main__":
    main()