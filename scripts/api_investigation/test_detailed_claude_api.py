"""
Test Claude Admin API with different parameters to find per-key data.

We need to investigate:
1. Can we filter by workspace_id?
2. Can we filter by api_key_id?
3. Are there other endpoints that provide per-key breakdown?
4. Do query parameters change what metadata is returned?
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_ADMIN_KEY")
BASE_URL = "https://api.anthropic.com/v1/organizations"
ORG_ID = "1233d3ee-9900-424a-a31a-fb8b8dcd0be3"

def test_cost_report_with_workspace():
    """Test if filtering by workspace_id provides better metadata."""
    print("\n" + "="*80)
    print("TEST 1: Cost Report with workspace_id parameter")
    print("="*80)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/cost_report"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # Try with workspace_id parameter
    params = {
        "starting_at": start_date,
        "ending_at": end_date,
        "workspace_id": "Claude Code"  # Test with workspace name
    }

    print(f"Testing with workspace_id='Claude Code'")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS with workspace filter")
            print(json.dumps(data, indent=2)[:1000])
            return data
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    return None


def test_usage_report_with_breakdown():
    """Test if we can get per-key breakdown in usage report."""
    print("\n" + "="*80)
    print("TEST 2: Usage Report with breakdown parameters")
    print("="*80)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/usage_report/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # Try with group_by parameter
    params = {
        "starting_at": start_date,
        "ending_at": end_date,
        "group_by": "api_key_id"  # Try to group by key
    }

    print(f"Testing with group_by='api_key_id'")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS with grouping")
            print(json.dumps(data, indent=2)[:2000])

            # Check if api_key_id is now populated
            if data.get('data') and data['data'][0].get('results'):
                sample = data['data'][0]['results'][0]
                print(f"\napi_key_id value: {sample.get('api_key_id')}")
                print(f"workspace_id value: {sample.get('workspace_id')}")
                print(f"model value: {sample.get('model')}")

            return data
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    return None


def test_cost_report_with_breakdown():
    """Test if we can get per-key breakdown in cost report."""
    print("\n" + "="*80)
    print("TEST 3: Cost Report with breakdown parameters")
    print("="*80)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/cost_report"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # Try with group_by parameter
    params = {
        "starting_at": start_date,
        "ending_at": end_date,
        "group_by": ["workspace_id", "model", "api_key_id"]
    }

    print(f"Testing with group_by=['workspace_id', 'model', 'api_key_id']")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS with grouping")
            print(json.dumps(data, indent=2)[:2000])

            # Check if metadata is now populated
            if data.get('data') and data['data'][0].get('results'):
                results = data['data'][0]['results']
                print(f"\nNumber of result records: {len(results)}")

                if len(results) > 0:
                    sample = results[0]
                    print(f"\nFirst record metadata:")
                    print(f"  workspace_id: {sample.get('workspace_id')}")
                    print(f"  model: {sample.get('model')}")
                    print(f"  api_key_id: {sample.get('api_key_id')}")
                    print(f"  cost_type: {sample.get('cost_type')}")

            return data
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    return None


def test_organization_members():
    """Check if there's an endpoint to get workspace/key details."""
    print("\n" + "="*80)
    print("TEST 4: Try to get organization/workspace structure")
    print("="*80)

    # Try different potential endpoints
    test_endpoints = [
        "/workspaces",
        "/api_keys",
        "/members",
        f"/{ORG_ID}/workspaces",
        f"/{ORG_ID}/api_keys"
    ]

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    for endpoint in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"\nTrying: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")

            if response.status_code == 200:
                print(f"  ✅ SUCCESS! Found working endpoint!")
                data = response.json()
                print(json.dumps(data, indent=2)[:500])
            elif response.status_code != 404:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")


def main():
    print("\n" + "#"*80)
    print("# DETAILED Claude Admin API Investigation")
    print("# Goal: Find per-key or per-workspace data")
    print("#"*80)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_ADMIN_KEY not found")
        return

    print(f"\n✅ API Key: {ANTHROPIC_API_KEY[:20]}...")
    print(f"✅ Org ID: {ORG_ID}")

    # Run all tests
    test_cost_report_with_workspace()
    test_usage_report_with_breakdown()
    test_cost_report_with_breakdown()
    test_organization_members()

    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)
    print("\n💡 Review results above to determine if:")
    print("  1. We can filter by workspace_id or api_key_id")
    print("  2. group_by parameter populates metadata fields")
    print("  3. Alternative endpoints exist for per-key data")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
