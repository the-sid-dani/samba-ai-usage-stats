"""
Test Cursor Admin API to verify available usage and finance data.

This script will test:
1. /teams/daily-usage-data - Team usage metrics AND cost/finance data

Purpose: Verify actual API response structure before building data models.
Reference: /docs/api-reference/cursor-api-specs.md
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CURSOR_API_KEY = os.getenv("CURSOR_ADMIN_API_KEY")
BASE_URL = "https://api.cursor.com"


def test_daily_usage_endpoint():
    """Test Cursor daily usage data endpoint for BOTH usage and finance data."""
    print("\n" + "="*80)
    print("TESTING: Cursor Daily Usage Data (/teams/daily-usage-data)")
    print("="*80)

    # Calculate date range (last 7 days - within 90 day limit)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Convert to milliseconds (JavaScript timestamp format)
    start_timestamp = int(start_date.timestamp() * 1000)
    end_timestamp = int(end_date.timestamp() * 1000)

    url = f"{BASE_URL}/teams/daily-usage-data"
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "startDate": start_timestamp,
        "endDate": end_timestamp
    }

    print(f"\nRequest URL: {url}")
    print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Timestamps: {start_timestamp} to {end_timestamp}")
    print(f"\nPayload: {json.dumps(payload, indent=2)}")
    print(f"\nAuthentication: Basic auth with API key as username")
    print(f"\nSending request...")

    try:
        # Use Basic auth with API key as username, empty password
        response = requests.post(
            url,
            auth=(CURSOR_API_KEY, ""),
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS - API Response Structure:")
            print(json.dumps(data, indent=2)[:3000])  # First 3000 chars

            # Analyze structure
            if "data" in data and len(data["data"]) > 0:
                print("\n📊 Sample Record Analysis:")
                sample = data["data"][0]

                print(f"\nAll Fields in First Record:")
                for key, value in sample.items():
                    value_type = type(value).__name__
                    value_preview = str(value)[:50] if value is not None else "null"
                    print(f"  - {key}: {value_type} = {value_preview}")

                print(f"\n📈 Total Records: {len(data['data'])}")

                # Check for finance/expense fields
                print("\n💰 Finance/Expense Fields Analysis:")
                finance_fields = [
                    "subscriptionIncludedReqs",
                    "usageBasedReqs",
                    "apiKeyReqs",
                    "estimatedCost",
                    "cost",
                    "price",
                    "billing"
                ]

                for field in finance_fields:
                    if field in sample:
                        print(f"  ✅ {field}: {sample[field]}")
                    else:
                        print(f"  ❌ {field}: NOT FOUND")

                # Check all unique fields across all records
                all_fields = set()
                for record in data["data"]:
                    all_fields.update(record.keys())

                print(f"\n🔍 All Unique Fields Across {len(data['data'])} Records:")
                for field in sorted(all_fields):
                    print(f"  - {field}")

            else:
                print("\n⚠️  No data records found in response")

            return data
        else:
            print(f"\n❌ ERROR - Status {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"Response Body: {response.text}")
            return None

    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run Cursor Admin API test."""
    print("\n" + "#"*80)
    print("# Cursor Admin API Investigation")
    print("#"*80)

    if not CURSOR_API_KEY:
        print("\n❌ ERROR: CURSOR_ADMIN_API_KEY not found in environment")
        return

    print(f"\n✅ API Key loaded: {CURSOR_API_KEY[:20]}...")

    # Test daily usage endpoint
    usage_data = test_daily_usage_endpoint()

    # Summary
    print("\n" + "="*80)
    print("INVESTIGATION SUMMARY")
    print("="*80)

    print("\n✅ Cursor Daily Usage Endpoint:")
    if usage_data:
        print("  - Status: SUCCESS")
        print(f"  - Records: {len(usage_data.get('data', []))}")

        # Check if finance data is available
        if usage_data.get('data'):
            sample = usage_data['data'][0]
            finance_fields_found = []
            for field in ["subscriptionIncludedReqs", "usageBasedReqs", "apiKeyReqs"]:
                if field in sample:
                    finance_fields_found.append(field)

            if finance_fields_found:
                print(f"  - Finance Fields Found: {', '.join(finance_fields_found)}")
            else:
                print("  - Finance Fields: ⚠️  NOT FOUND - may need separate endpoint")
    else:
        print("  - Status: FAILED")

    print("\n" + "="*80)
    print("\n💡 Next Steps:")
    print("1. Review the actual field names from response above")
    print("2. Identify which fields contain cost/finance data")
    print("3. Determine if we need additional endpoints for finance data")
    print("4. Document verified schema in /docs/api-reference/verified-schemas.md")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
