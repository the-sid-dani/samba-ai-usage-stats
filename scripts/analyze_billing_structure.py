#!/usr/bin/env python3
"""
Analyze the billing structure by comparing Cursor usage with invoices.
"""

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import requests

# Read API keys
with open('/tmp/cursor_key.txt', 'r') as f:
    CURSOR_KEY = f.read().strip()

with open('/tmp/anthropic_key.txt', 'r') as f:
    ANTHROPIC_KEY = f.read().strip()

def get_cursor_usage_by_month():
    """Get Cursor usage metrics for each month."""
    print("📊 FETCHING CURSOR USAGE DATA BY MONTH")
    print("="*60)

    auth = (CURSOR_KEY, "")
    headers = {"Content-Type": "application/json"}

    monthly_usage = {}

    # Get last 6 months of data
    for i in range(6):
        month_end = date.today() - relativedelta(months=i)
        month_start = month_end - relativedelta(months=1)

        if month_end > date.today():
            month_end = date.today()

        month_label = month_end.strftime('%b %Y')

        payload = {
            "startDate": int(datetime.combine(month_start, datetime.min.time()).timestamp() * 1000),
            "endDate": int(datetime.combine(month_end, datetime.min.time()).timestamp() * 1000)
        }

        response = requests.post(
            "https://api.cursor.com/teams/daily-usage-data",
            auth=auth,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            records = data.get('data', [])

            total_usage_reqs = sum(r.get('usageBasedReqs', 0) for r in records)
            total_subscription_reqs = sum(r.get('subscriptionIncludedReqs', 0) for r in records)
            total_api_key_reqs = sum(r.get('apiKeyReqs', 0) for r in records)

            monthly_usage[month_label] = {
                'usage_based': total_usage_reqs,
                'subscription': total_subscription_reqs,
                'api_key': total_api_key_reqs,
                'total': total_usage_reqs + total_subscription_reqs + total_api_key_reqs
            }

            print(f"\n{month_label}:")
            print(f"  Subscription requests: {total_subscription_reqs:,}")
            print(f"  Usage-based requests: {total_usage_reqs:,}")
            print(f"  API key requests: {total_api_key_reqs:,}")

    return monthly_usage

def analyze_billing_structure():
    """Analyze how billing works between Cursor and Anthropic."""
    print("\n" + "="*70)
    print("📊 BILLING STRUCTURE ANALYSIS")
    print("="*70)

    # Known costs from invoices
    known_costs = {
        'Jul 2025': 2694.31,
        'Aug 2025': 827.15,
        'Sep 2025': 1089.33
    }

    print("\n1️⃣ CURSOR SUBSCRIPTION:")
    print("   - Fixed: $50/month")
    print("   - Includes: Some number of API requests")
    print("   - Additional: Usage-based requests cost extra")

    print("\n2️⃣ ANTHROPIC BILLING (from your invoice):")
    for month, cost in known_costs.items():
        print(f"   - {month}: ${cost:,.2f}")

    print("\n3️⃣ WHAT THE INVOICE SHOWS:")
    print("   Your Anthropic invoice lists:")
    print("   • 'Cursor Usage for September 2025' - $1,000.01")
    print("   • 'Cursor Usage for August 2025' - $827.15")
    print("   • Plus various token-based usage lines")

    print("\n4️⃣ BILLING FLOW POSSIBILITIES:")
    print("\n   Option A: Pass-through billing")
    print("   ├─ You pay Cursor $50/month (subscription)")
    print("   ├─ Cursor uses Anthropic's API on your behalf")
    print("   └─ Anthropic bills YOU directly for Cursor's usage")

    print("\n   Option B: Reseller model")
    print("   ├─ You pay Cursor $50/month (subscription)")
    print("   ├─ Cursor pays Anthropic for API usage")
    print("   └─ Cursor bills YOU for overage (usage-based requests)")

    print("\n5️⃣ EVIDENCE POINTS TO OPTION A:")
    print("   • Invoice shows 'Cursor Usage' on Anthropic's billing page")
    print("   • You're being billed directly by Anthropic")
    print("   • Cursor API doesn't return cost data (they don't handle billing)")

    print("\n6️⃣ COST BREAKDOWN:")
    print("   Fixed costs:")
    print("   • Cursor subscription: $50/month")
    print("   • Claude.ai subscription: $40/month")
    print("\n   Variable costs (via Anthropic):")
    print("   • Direct Claude API usage: $X")
    print("   • Cursor's API usage: $Y")
    print("   • Total shown on Anthropic invoice: $X + $Y")

def main():
    # Get Cursor usage data
    cursor_usage = get_cursor_usage_by_month()

    # Analyze billing structure
    analyze_billing_structure()

    print("\n" + "="*70)
    print("💡 KEY FINDING:")
    print("="*70)
    print("\nCursor is using YOUR Anthropic API account for their requests.")
    print("This is why you see 'Cursor Usage' on your Anthropic invoice.")
    print("\nYour total AI costs are:")
    print("1. Fixed: $90/month (Cursor + Claude.ai subscriptions)")
    print("2. Variable: Everything on the Anthropic invoice")
    print("   (includes both your direct usage AND Cursor's usage)")

if __name__ == "__main__":
    main()