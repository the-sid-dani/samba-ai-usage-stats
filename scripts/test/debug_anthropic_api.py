#!/usr/bin/env python3
"""Debug Anthropic API to understand the data structure and volume."""

import requests
import json
from datetime import datetime, timedelta
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def debug_anthropic_api():
    """Debug Anthropic API responses in detail."""
    print("🔍 Debugging Anthropic API Responses")
    print("=" * 50)

    try:
        # Get API key
        api_key = get_secret("anthropic-api-key")
        print(f"✅ API Key: {api_key[:15]}...")

        # Headers
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Test different date ranges
        date_ranges = [
            ("Last 1 day", 1),
            ("Last 7 days", 7),
            ("Last 30 days", 30)
        ]

        for range_name, days_back in date_ranges:
            print(f"\n📅 Testing {range_name} ({days_back} days)")
            print("-" * 30)

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)

            params = {
                "starting_at": start_date.strftime("%Y-%m-%d"),
                "ending_at": end_date.strftime("%Y-%m-%d")
            }

            print(f"Date range: {start_date} to {end_date}")

            # Test usage endpoint
            usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
            print(f"Testing: {usage_url}")

            response = requests.get(usage_url, headers=headers, params=params, timeout=30)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {list(data.keys())}")

                usage_records = data.get('data', [])
                print(f"Usage records: {len(usage_records)}")

                if usage_records:
                    sample = usage_records[0]
                    print(f"Sample record keys: {list(sample.keys())}")
                    print(f"Sample data: {json.dumps(sample, indent=2)[:300]}...")

                # Check pagination
                has_more = data.get('has_more', False)
                next_page = data.get('next_page')
                print(f"Has more pages: {has_more}")
                if next_page:
                    print(f"Next page token: {next_page[:50]}...")

            else:
                print(f"Error: {response.text[:200]}")

            # Test cost endpoint
            cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
            print(f"Testing: {cost_url}")

            cost_response = requests.get(cost_url, headers=headers, params=params, timeout=30)
            print(f"Status: {cost_response.status_code}")

            if cost_response.status_code == 200:
                cost_data = cost_response.json()
                print(f"Cost response keys: {list(cost_data.keys())}")

                cost_records = cost_data.get('data', [])
                print(f"Cost records: {len(cost_records)}")

                if cost_records:
                    sample = cost_records[0]
                    print(f"Sample cost keys: {list(sample.keys())}")
                    print(f"Sample cost: {json.dumps(sample, indent=2)[:300]}...")

            else:
                print(f"Cost error: {cost_response.text[:200]}")

        # Test organization info
        print(f"\n🏢 Testing Organization Info")
        print("-" * 30)

        org_url = "https://api.anthropic.com/v1/organization"
        org_response = requests.get(org_url, headers=headers, timeout=30)
        print(f"Organization status: {org_response.status_code}")

        if org_response.status_code == 200:
            org_data = org_response.json()
            print(f"Organization: {org_data.get('name', 'unknown')}")
            print(f"Organization ID: {org_data.get('id', 'unknown')}")
        else:
            print(f"Organization error: {org_response.text[:200]}")

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_anthropic_api()