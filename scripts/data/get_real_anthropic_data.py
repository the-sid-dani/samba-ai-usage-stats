#!/usr/bin/env python3
"""Fetch real Anthropic API data to show actual structure."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import date, timedelta
import json

# Mock config for testing
class MockConfig:
    def __init__(self):
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')

import src.shared.config as config_module
config_module.config = MockConfig()

from src.ingestion.anthropic_client import AnthropicClient

def get_real_data():
    """Fetch real data from Anthropic API."""
    print("🔍 Fetching Real Anthropic API Data")
    print("=" * 50)

    try:
        client = AnthropicClient()

        # Get yesterday's data to see real usage
        end_date = date.today()
        start_date = end_date - timedelta(days=2)  # 2 days to get some data

        print(f"📅 Fetching data from {start_date} to {end_date}")

        # Get usage data
        usage_data = client.get_usage_data(start_date, end_date)

        if not usage_data:
            print("❌ No usage data found for the specified date range")
            return

        print(f"✅ Retrieved {len(usage_data)} usage records")

        # Show first few real records
        print("\n🎯 REAL ANTHROPIC DATA STRUCTURE:")
        print("=" * 40)

        # Group by platform to show examples
        platform_examples = {}

        for record in usage_data[:10]:  # Show up to 10 records
            platform = record.platform
            if platform not in platform_examples:
                platform_examples[platform] = []
            if len(platform_examples[platform]) < 2:  # Max 2 examples per platform
                platform_examples[platform].append(record)

        for platform, records in platform_examples.items():
            print(f"\n🔹 {platform.upper()} PLATFORM EXAMPLES:")
            print("-" * 30)

            for i, record in enumerate(records, 1):
                print(f"\nExample {i}:")
                print(f"  usage_date: {record.usage_date}")
                print(f"  usage_hour: {record.usage_hour}")
                print(f"  platform: {record.platform}")
                print(f"  api_key_id: {record.api_key_id}")
                print(f"  workspace_id: {record.workspace_id}")
                print(f"  model: {record.model}")
                print(f"  user_email: {record.user_email}")
                print(f"  uncached_input_tokens: {record.uncached_input_tokens:,}")
                print(f"  cached_input_tokens: {record.cached_input_tokens:,}")
                print(f"  cache_read_input_tokens: {record.cache_read_input_tokens:,}")
                print(f"  output_tokens: {record.output_tokens:,}")
                print(f"  attribution_method: {record.attribution_method}")
                print(f"  attribution_confidence: {record.attribution_confidence}")

                total_input = record.uncached_input_tokens + record.cached_input_tokens
                print(f"  📊 TOTALS: {total_input:,} input + {record.output_tokens:,} output = {total_input + record.output_tokens:,} total tokens")

        # Show aggregation summary
        print(f"\n📊 DAILY AGGREGATION SUMMARY:")
        print("=" * 30)

        daily_summary = {}
        for record in usage_data:
            key = (record.usage_date, record.platform, record.user_email or "unknown_user")
            if key not in daily_summary:
                daily_summary[key] = {
                    "records": 0,
                    "total_input": 0,
                    "total_output": 0,
                    "api_keys": set(),
                    "models": set()
                }

            daily_summary[key]["records"] += 1
            daily_summary[key]["total_input"] += record.uncached_input_tokens + record.cached_input_tokens
            daily_summary[key]["total_output"] += record.output_tokens
            daily_summary[key]["api_keys"].add(record.api_key_id)
            daily_summary[key]["models"].add(record.model)

        for (usage_date, platform, user_email), data in list(daily_summary.items())[:5]:
            print(f"\n{usage_date} | {platform} | {user_email}")
            print(f"  📈 {data['records']} records from {len(data['api_keys'])} API keys")
            print(f"  🔢 {data['total_input']:,} input + {data['total_output']:,} output tokens")
            print(f"  🤖 Models: {', '.join(data['models'])}")

        # Show how platform categorization is working
        print(f"\n🎯 PLATFORM CATEGORIZATION RESULTS:")
        print("=" * 35)

        platform_counts = {}
        attribution_methods = {}

        for record in usage_data:
            platform_counts[record.platform] = platform_counts.get(record.platform, 0) + 1
            attribution_methods[record.attribution_method] = attribution_methods.get(record.attribution_method, 0) + 1

        print("Platforms detected:")
        for platform, count in platform_counts.items():
            print(f"  {platform}: {count} records")

        print("\nAttribution methods used:")
        for method, count in attribution_methods.items():
            print(f"  {method}: {count} records")

        # Show user attribution success
        with_email = sum(1 for r in usage_data if r.user_email)
        print(f"\n✅ User Attribution: {with_email}/{len(usage_data)} records have user email")

        # Show workspace vs non-workspace breakdown
        with_workspace = sum(1 for r in usage_data if r.workspace_id)
        print(f"✅ Workspace Detection: {with_workspace}/{len(usage_data)} records have workspace_id")

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_real_data()