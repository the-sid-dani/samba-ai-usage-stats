"""
Test cost_report endpoint WITH group_by parameter to get breakdown
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_ADMIN_KEY")
BASE_URL = "https://api.anthropic.com/v1/organizations"

def test_cost_report_grouped():
    """Test cost_report WITH group_by to get breakdown by model/workspace"""
    print("\n" + "="*80)
    print("TEST: Cost Report WITH group_by parameter")
    print("="*80)

    end_date = "2025-10-19"
    start_date = "2025-10-03"

    url = f"{BASE_URL}/cost_report"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # Test WITH group_by parameter
    params = {
        "starting_at": start_date,
        "ending_at": end_date,
        "group_by[]": ["workspace_id", "model", "cost_type", "token_type"]
    }

    print(f"Date Range: {start_date} to {end_date}")
    print(f"Parameters: {params}")
    print()

    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        print(f"Status: {response.status_code}\n")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS with group_by\n")

            # Show structure
            print("Response Structure:")
            print(json.dumps(data, indent=2)[:3000])
            print("\n...")

            # Analyze first day's results
            if data.get('data') and len(data['data']) > 0:
                first_day = data['data'][0]
                print(f"\n📊 First Day Analysis:")
                print(f"Date: {first_day['starting_at']} to {first_day['ending_at']}")
                print(f"Number of result records: {len(first_day.get('results', []))}")

                if first_day.get('results'):
                    print(f"\n🔍 First Result Record:")
                    first_result = first_day['results'][0]
                    for key, value in first_result.items():
                        print(f"  {key}: {value}")

                    # Sum up total for first day
                    day_total = sum(float(r.get('amount', 0)) for r in first_day['results'])
                    print(f"\n💰 First Day Total: ${day_total:.2f}")

                    # Show breakdown by model
                    models = {}
                    for r in first_day['results']:
                        model = r.get('model', 'unknown')
                        amount = float(r.get('amount', 0))
                        models[model] = models.get(model, 0) + amount

                    print(f"\n📈 Breakdown by Model:")
                    for model, amount in sorted(models.items(), key=lambda x: x[1], reverse=True)[:10]:
                        print(f"  {model}: ${amount:.2f}")

            # Calculate total across all days
            print(f"\n💵 TOTAL COST ACROSS ALL DAYS:")
            total = 0
            days_with_data = 0
            for day in data.get('data', []):
                day_sum = sum(float(r.get('amount', 0)) for r in day.get('results', []))
                if day_sum > 0:
                    days_with_data += 1
                    print(f"  {day['starting_at'][:10]}: ${day_sum:.2f}")
                total += day_sum

            print(f"\n🎯 GRAND TOTAL: ${total:.2f}")
            print(f"📅 Days with data: {days_with_data}")

            return data
        else:
            print(f"❌ FAILED")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    return None


def test_cost_report_ungrouped():
    """Test cost_report WITHOUT group_by (what we're currently doing)"""
    print("\n" + "="*80)
    print("TEST: Cost Report WITHOUT group_by (current broken approach)")
    print("="*80)

    end_date = "2025-10-19"
    start_date = "2025-10-03"

    url = f"{BASE_URL}/cost_report"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # Test WITHOUT group_by parameter (bad)
    params = {
        "starting_at": start_date,
        "ending_at": end_date
    }

    print(f"Date Range: {start_date} to {end_date}")
    print(f"Parameters: {params}")
    print()

    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        print(f"Status: {response.status_code}\n")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS (but wrong data)\n")

            # Calculate total
            print(f"💵 TOTAL FROM UNGROUPED API:")
            total = 0
            for day in data.get('data', []):
                day_sum = sum(float(r.get('amount', 0)) for r in day.get('results', []))
                if day_sum > 0:
                    print(f"  {day['starting_at'][:10]}: ${day_sum:.2f}")
                total += day_sum

            print(f"\n🎯 UNGROUPED TOTAL: ${total:.2f}")
            print(f"⚠️  This is aggregated at org-level without breakdown!")

            return data
        else:
            print(f"❌ FAILED")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    return None


def main():
    print("\n" + "#"*80)
    print("# Cost Report: Grouped vs Ungrouped Comparison")
    print("#"*80)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_ADMIN_KEY not found")
        return

    print(f"\n✅ API Key loaded: {ANTHROPIC_API_KEY[:20]}...\n")

    # Test both approaches
    grouped_data = test_cost_report_grouped()
    ungrouped_data = test_cost_report_ungrouped()

    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    print("\n💡 KEY FINDING:")
    print("  - WITHOUT group_by: Returns high-level aggregates (possibly ALL org usage)")
    print("  - WITH group_by: Returns detailed breakdown we can actually use")
    print("\n⚠️  THE FUNDAMENTAL MISTAKE:")
    print("  Our ingestion is likely NOT using group_by[], so we're getting")
    print("  organization-wide aggregates that may include ALL workspaces,")
    print("  including test/dev/staging environments!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
