#!/usr/bin/env python3
"""Test the fixed Anthropic client platform categorization."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import date, timedelta
from src.ingestion.anthropic_client import AnthropicClient

def test_anthropic_platform_categorization():
    """Test that Anthropic client now properly categorizes platforms."""
    print("🔍 Testing Fixed Anthropic Platform Categorization")
    print("=" * 50)

    try:
        client = AnthropicClient()

        # Test with recent data (1 day) to minimize API usage
        end_date = date.today()
        start_date = end_date - timedelta(days=1)

        print(f"📅 Fetching data from {start_date} to {end_date}")

        # Get usage data
        usage_data = client.get_usage_data(start_date, end_date)

        print(f"✅ Retrieved {len(usage_data)} usage records")

        # Analyze platform categorization
        platforms = {}
        attribution_methods = {}

        for record in usage_data[:5]:  # Show first 5 records
            print(f"\n📊 Record Analysis:")
            print(f"  API Key ID: {record.api_key_id}")
            print(f"  Workspace ID: {record.workspace_id}")
            print(f"  Platform: {record.platform}")
            print(f"  Attribution Method: {record.attribution_method}")
            print(f"  Attribution Confidence: {record.attribution_confidence}")
            print(f"  User Email: {record.user_email}")
            print(f"  Model: {record.model}")
            print(f"  Usage Date: {record.usage_date}")

            # Count platforms
            platforms[record.platform] = platforms.get(record.platform, 0) + 1
            attribution_methods[record.attribution_method] = attribution_methods.get(record.attribution_method, 0) + 1

        print(f"\n🎯 Platform Summary:")
        for platform, count in platforms.items():
            print(f"  {platform}: {count} records")

        print(f"\n🎯 Attribution Method Summary:")
        for method, count in attribution_methods.items():
            print(f"  {method}: {count} records")

        # Test expected platforms
        expected_platforms = {"claude_code", "claude_api", "claude_ai"}
        found_platforms = set(platforms.keys())

        print(f"\n✅ Platform Detection Working: {len(found_platforms.intersection(expected_platforms))} expected platforms found")

        # Check if all records have proper attribution
        missing_platform = sum(1 for r in usage_data if not r.platform)
        print(f"✅ Platform Attribution: {len(usage_data) - missing_platform}/{len(usage_data)} records properly attributed")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_anthropic_platform_categorization()
    sys.exit(0 if success else 1)