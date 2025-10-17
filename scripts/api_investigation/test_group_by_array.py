"""
Test Claude Admin API with CORRECT group_by array syntax.

The API told us: "Use `group_by[]` for array parameters"
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_ADMIN_KEY")
BASE_URL = "https://api.anthropic.com/v1/organizations"


def test_usage_report_grouped():
    """Test Usage Report with correct group_by[] syntax."""
    print("\n" + "="*80)
    print("TEST: Usage Report with group_by[] array syntax")
    print("="*80)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/usage_report/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    # Use correct array syntax
    params = {
        "starting_at": start_date,
        "ending_at": end_date,
        "group_by[]": ["api_key_id", "workspace_id", "model"]
    }

    print(f"Parameters: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"\nStatus: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS! API accepts group_by[] parameter")
            print("\nFull Response:")
            print(json.dumps(data, indent=2))

            # Analyze if metadata is populated
            if data.get('data') and len(data['data']) > 0:
                first_day = data['data'][0]
                if first_day.get('results') and len(first_day['results']) > 0:
                    print(f"\n📊 Found {len(first_day['results'])} result records")
                    print("\nChecking metadata in first 5 records:")

                    for i, result in enumerate(first_day['results'][:5]):
                        print(f"\nRecord {i+1}:")
                        print(f"  api_key_id: {result.get('api_key_id')}")
                        print(f"  workspace_id: {result.get('workspace_id')}")
                        print(f"  model: {result.get('model')}")
                        print(f"  tokens: {result.get('uncached_input_tokens', 0):,}")
                        print(f"  output: {result.get('output_tokens', 0):,}")

            return data
        else:
            print(f"\n❌ Error: {response.text}")

    except Exception as e:
        print(f"\n❌ Exception: {e}")

    return None


def test_cost_report_grouped():
    """Test Cost Report with correct group_by[] syntax."""
    print("\n" + "="*80)
    print("TEST: Cost Report with group_by[] array syntax")
    print("="*80)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/cost_report"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    params = {
        "starting_at": start_date,
        "ending_at": end_date,
        "group_by[]": ["workspace_id", "model", "api_key_id"]
    }

    print(f"Parameters: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"\nStatus: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS! API accepts group_by[] parameter")
            print("\nFull Response:")
            print(json.dumps(data, indent=2))

            # Analyze records
            if data.get('data') and len(data['data']) > 0:
                first_day = data['data'][0]
                if first_day.get('results'):
                    print(f"\n📊 Found {len(first_day['results'])} result records")
                    print("\nFirst 5 records with metadata:")

                    for i, result in enumerate(first_day['results'][:5]):
                        print(f"\nRecord {i+1}:")
                        print(f"  workspace_id: {result.get('workspace_id')}")
                        print(f"  model: {result.get('model')}")
                        print(f"  api_key_id: {result.get('api_key_id')}")
                        print(f"  amount: ${result.get('amount')}")

            return data
        else:
            print(f"\n❌ Error: {response.text}")

    except Exception as e:
        print(f"\n❌ Exception: {e}")

    return None


def main():
    print("\n" + "#"*80)
    print("# Testing group_by[] Array Syntax")
    print("#"*80)

    usage_data = test_usage_report_grouped()
    cost_data = test_cost_report_grouped()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if usage_data or cost_data:
        print("\n✅ If metadata is NOW populated:")
        print("   → We CAN get per-key breakdown")
        print("   → We CAN segment platforms")
        print("   → We CAN attribute to users")
    else:
        print("\n❌ If still null:")
        print("   → API doesn't support per-key data")
        print("   → Must use org-level aggregates")

    print("="*80 + "\n")


if __name__ == "__main__":
    main()
