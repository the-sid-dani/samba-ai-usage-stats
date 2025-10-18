"""
Test Claude Admin API endpoints to verify available data.

This script will test:
1. /v1/organizations/usage_report/claude_code - Claude Code usage metrics
2. /v1/organizations/cost_report - All Claude costs (claude.ai + Claude Code + API)

Purpose: Verify actual API response structure before building data models.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_ADMIN_KEY")
BASE_URL = "https://api.anthropic.com/v1/organizations"

def test_claude_code_endpoint():
    """Test Claude Code usage report endpoint."""
    print("\n" + "="*80)
    print("TESTING: Claude Code Usage Report (/usage_report/claude_code)")
    print("="*80)

    # Calculate date range (last 7 days)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/usage_report/claude_code"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    params = {
        "starting_at": start_date,
        "ending_at": end_date
    }

    print(f"\nRequest URL: {url}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"\nSending request...")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS - API Response Structure:")
            print(json.dumps(data, indent=2)[:2000])  # First 2000 chars

            # Analyze structure
            if "data" in data and len(data["data"]) > 0:
                print("\n📊 Sample Record Fields:")
                sample = data["data"][0]
                for key in sample.keys():
                    print(f"  - {key}: {type(sample[key]).__name__}")

                print(f"\n📈 Total Records: {len(data['data'])}")
                print(f"Has More Pages: {data.get('has_more', 'N/A')}")
            else:
                print("\n⚠️  No data records found in response")

            return data
        else:
            print(f"\n❌ ERROR - Status {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        return None


def test_cost_report_endpoint():
    """Test Claude Cost Report endpoint."""
    print("\n" + "="*80)
    print("TESTING: Claude Cost Report (/cost_report)")
    print("="*80)

    # Calculate date range (last 30 days for cost data)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/cost_report"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    params = {
        "starting_at": start_date,
        "ending_at": end_date
    }

    print(f"\nRequest URL: {url}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"\nSending request...")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS - API Response Structure:")
            print(json.dumps(data, indent=2)[:2000])  # First 2000 chars

            # Analyze structure
            if "data" in data and len(data["data"]) > 0:
                print("\n📊 Sample Record Fields:")
                sample_day = data["data"][0]
                print(f"Date Range Fields: {sample_day.keys()}")

                if "results" in sample_day and len(sample_day["results"]) > 0:
                    sample_result = sample_day["results"][0]
                    print(f"\n  Result Record Fields:")
                    for key in sample_result.keys():
                        value = sample_result[key]
                        print(f"    - {key}: {type(value).__name__} = {value}")

                print(f"\n📈 Total Date Buckets: {len(data['data'])}")

                # Check for platform identification fields
                print("\n🔍 Platform Identification Analysis:")
                all_workspaces = set()
                all_descriptions = set()

                for day_data in data["data"]:
                    for result in day_data.get("results", []):
                        if "workspace_id" in result:
                            all_workspaces.add(result["workspace_id"])
                        if "description" in result:
                            all_descriptions.add(result["description"])

                print(f"  Unique workspace_ids: {all_workspaces}")
                print(f"  Unique descriptions: {list(all_descriptions)[:10]}")  # First 10

            else:
                print("\n⚠️  No data records found in response")

            return data
        else:
            print(f"\n❌ ERROR - Status {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        return None


def main():
    """Run all Claude Admin API tests."""
    print("\n" + "#"*80)
    print("# Claude Admin API Investigation")
    print("#"*80)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_ADMIN_KEY not found in environment")
        return

    print(f"\n✅ API Key loaded: {ANTHROPIC_API_KEY[:20]}...")

    # Test Claude Code endpoint
    claude_code_data = test_claude_code_endpoint()

    # Test Cost Report endpoint
    cost_report_data = test_cost_report_endpoint()

    # Summary
    print("\n" + "="*80)
    print("INVESTIGATION SUMMARY")
    print("="*80)

    print("\n✅ Claude Code Endpoint:")
    if claude_code_data:
        print("  - Status: SUCCESS")
        print(f"  - Records: {len(claude_code_data.get('data', []))}")
    else:
        print("  - Status: FAILED")

    print("\n✅ Cost Report Endpoint:")
    if cost_report_data:
        print("  - Status: SUCCESS")
        print(f"  - Date Buckets: {len(cost_report_data.get('data', []))}")
    else:
        print("  - Status: FAILED")

    print("\n" + "="*80)
    print("\n💡 Next Steps:")
    print("1. Review the actual field names from responses above")
    print("2. Identify how to segment claude.ai vs Claude Code vs API costs")
    print("3. Document verified schema in /docs/api-reference/verified-schemas.md")
    print("4. Update PRD with accurate data architecture")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
