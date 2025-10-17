#!/usr/bin/env python3
"""
Simple test of Cursor API to understand what we get back.
"""

import requests
from datetime import datetime, date, timedelta
import json

# Read API key
with open('/tmp/cursor_key.txt', 'r') as f:
    API_KEY = f.read().strip()

print("🔍 TESTING CURSOR API - SIMPLE TEST")
print("="*60)
print(f"API Key: {API_KEY[:20]}...")

# Test with last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# Cursor expects milliseconds
payload = {
    "startDate": int(start_date.timestamp() * 1000),
    "endDate": int(end_date.timestamp() * 1000)
}

print(f"\nDate range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"Payload: {payload}")

# Try Basic auth (API key as username, empty password)
auth = (API_KEY, "")
headers = {"Content-Type": "application/json"}

print("\n📡 Making request to Cursor API...")

response = requests.post(
    "https://api.cursor.com/teams/daily-usage-data",
    auth=auth,
    headers=headers,
    json=payload,
    timeout=30
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print("✅ Success!")

    # Analyze response
    if isinstance(data, dict) and 'data' in data:
        records = data['data']
        print(f"\n📊 Found {len(records)} records")

        # Analyze fields available
        if records:
            first_record = records[0]
            print(f"\n📋 Available fields in Cursor response:")
            for key in first_record.keys():
                value = first_record[key]
                if key == 'email':
                    print(f"  - {key}: [REDACTED]")
                else:
                    print(f"  - {key}: {value}")

            # Check for cost-related fields
            print(f"\n💰 Cost-related fields:")
            cost_keywords = ['cost', 'price', 'amount', 'charge', 'fee', 'billing', 'payment', 'invoice']
            found_cost_fields = []
            for key in first_record.keys():
                for keyword in cost_keywords:
                    if keyword in key.lower():
                        found_cost_fields.append(key)
                        break

            if found_cost_fields:
                print(f"  Found: {', '.join(found_cost_fields)}")
            else:
                print(f"  NONE FOUND - Cursor API only provides usage metrics")

            # Calculate totals
            total_usage_reqs = sum(r.get('usageBasedReqs', 0) for r in records)
            total_subscription_reqs = sum(r.get('subscriptionIncludedReqs', 0) for r in records)

            print(f"\n📈 30-Day Totals:")
            print(f"  Usage-based requests: {total_usage_reqs:,}")
            print(f"  Subscription requests: {total_subscription_reqs:,}")

            print(f"\n⚠️ IMPORTANT:")
            print(f"  Cursor API provides USAGE data, not COST data")
            print(f"  'usageBasedReqs' = requests beyond subscription limit")
            print(f"  These likely incur additional charges billed separately")
    else:
        print(f"Unexpected response: {data}")
else:
    print(f"❌ Error: {response.status_code}")
    print(f"Response: {response.text}")