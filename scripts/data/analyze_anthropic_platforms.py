#!/usr/bin/env python3
"""
Analyze Anthropic data to identify platform distinctions.
Need to distinguish: Claude.AI, Claude Code, Claude API
"""

import requests
import json
from datetime import datetime, date, timedelta
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def analyze_anthropic_platforms():
    """Analyze Anthropic data structure to identify platform indicators."""
    print("🔍 ANALYZING ANTHROPIC PLATFORM DISTINCTIONS")
    print("=" * 60)

    api_key = get_secret("anthropic-api-key")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Get last 30 days where we found real data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    # Get usage data
    usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
    response = requests.get(usage_url, headers=headers, params=params, timeout=60)

    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        return

    data = response.json()
    daily_buckets = data.get('data', [])

    print(f"Found {len(daily_buckets)} daily buckets")

    # Find a bucket with actual usage data
    sample_record = None
    for bucket in daily_buckets:
        results = bucket.get('results', [])
        if results:
            sample_record = results[0]
            print(f"✅ Found sample usage record from {bucket.get('starting_at', 'unknown')}")
            break

    if sample_record:
        print("\n📋 SAMPLE RECORD ANALYSIS:")
        print("=" * 40)
        print(f"All fields in usage record:")
        for key, value in sample_record.items():
            print(f"  {key}: {value}")

        print(f"\n🔍 PLATFORM IDENTIFICATION FIELDS:")
        # Look for platform indicators
        platform_fields = [
            'api_key_id', 'workspace_id', 'model', 'user_agent',
            'source', 'client', 'application', 'platform', 'service'
        ]

        for field in platform_fields:
            if field in sample_record:
                print(f"  ✅ {field}: {sample_record[field]}")
            else:
                print(f"  ❌ {field}: Not found")

    # Also check cost data structure
    cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
    cost_response = requests.get(cost_url, headers=headers, params=params, timeout=60)

    if cost_response.status_code == 200:
        cost_data = cost_response.json()
        cost_buckets = cost_data.get('data', [])

        sample_cost = None
        for bucket in cost_buckets:
            results = bucket.get('results', [])
            if results:
                sample_cost = results[0]
                print(f"\n✅ Found sample cost record from {bucket.get('starting_at', 'unknown')}")
                break

        if sample_cost:
            print(f"\n💰 SAMPLE COST RECORD:")
            print("=" * 40)
            for key, value in sample_cost.items():
                print(f"  {key}: {value}")

    # Check if there are different API keys for different platforms
    print(f"\n🔑 API KEY ANALYSIS:")
    print("=" * 40)

    unique_api_keys = set()
    for bucket in daily_buckets:
        for record in bucket.get('results', []):
            api_key_id = record.get('api_key_id')
            if api_key_id:
                unique_api_keys.add(api_key_id)

    print(f"Unique API keys found: {len(unique_api_keys)}")
    for i, key_id in enumerate(sorted(unique_api_keys), 1):
        print(f"  {i}. {key_id}")

    print(f"\n🎯 PLATFORM DISTINCTION STRATEGY:")
    if len(unique_api_keys) > 1:
        print("✅ Multiple API keys found - can distinguish by api_key_id")
        print("💡 Strategy: Map each api_key_id to platform (Claude.AI, Claude Code, Claude API)")
    else:
        print("⚠️ Single API key - need to check other fields for platform identification")

    return {
        "api_keys": list(unique_api_keys),
        "sample_record": sample_record,
        "sample_cost": sample_cost
    }

if __name__ == "__main__":
    try:
        results = analyze_anthropic_platforms()

        print(f"\n🎉 PLATFORM ANALYSIS COMPLETE!")
        print(f"API keys to map: {len(results['api_keys'])}")

        if len(results['api_keys']) > 1:
            print("✅ Can distinguish platforms by API key mapping")
        else:
            print("⚠️ May need additional platform identification logic")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()