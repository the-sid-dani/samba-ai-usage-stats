#!/usr/bin/env python3
"""Test what real Claude data we currently have in BigQuery."""

import os
from google.cloud import bigquery

def test_claude_data_structure():
    """Check what Claude data we actually have."""
    print("🔍 Testing Real Claude Data in BigQuery")
    print("=" * 50)

    try:
        client = bigquery.Client(project="ai-workflows-459123")

        # Test Claude usage data
        print("\n📊 Testing raw_anthropic_usage table...")
        usage_query = """
        SELECT *
        FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
        LIMIT 1
        """

        usage_result = client.query(usage_query).result()
        if usage_result.total_rows > 0:
            for row in usage_result:
                print(f"✅ Usage record found!")
                print(f"📊 Available fields: {list(row.keys())}")
                print(f"🔑 API Key: {row.get('api_key_id', 'N/A')[:20]}...")
                print(f"🏢 Workspace: {row.get('workspace_id', 'N/A')}")
                print(f"🧠 Model: {row.get('model', 'N/A')}")
                print(f"📈 Input tokens: {row.get('uncached_input_tokens', 0)}")
                print(f"📈 Output tokens: {row.get('output_tokens', 0)}")
                break
        else:
            print("❌ No usage records found")

        # Test Claude cost data
        print("\n💰 Testing raw_anthropic_cost table...")
        cost_query = """
        SELECT *
        FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_cost`
        LIMIT 1
        """

        cost_result = client.query(cost_query).result()
        if cost_result.total_rows > 0:
            for row in cost_result:
                print(f"✅ Cost record found!")
                print(f"💰 Available fields: {list(row.keys())}")
                print(f"🔑 API Key: {row.get('api_key_id', 'N/A')[:20]}...")
                print(f"🏢 Workspace: {row.get('workspace_id', 'N/A')}")
                print(f"💵 Cost: ${row.get('cost_usd', 0)}")
                print(f"📋 Cost type: {row.get('cost_type', 'N/A')}")
                break
        else:
            print("❌ No cost records found")

        # Test actual record counts
        print("\n📊 Record Counts:")
        count_query = """
        SELECT
          'usage' as table_type,
          COUNT(*) as record_count,
          COUNT(DISTINCT api_key_id) as unique_api_keys,
          MIN(usage_date) as earliest_date,
          MAX(usage_date) as latest_date
        FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`

        UNION ALL

        SELECT
          'cost' as table_type,
          COUNT(*) as record_count,
          COUNT(DISTINCT api_key_id) as unique_api_keys,
          MIN(cost_date) as earliest_date,
          MAX(cost_date) as latest_date
        FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_cost`
        """

        count_result = client.query(count_query).result()
        for row in count_result:
            print(f"📊 {row['table_type']}: {row['record_count']} records, {row['unique_api_keys']} API keys")
            print(f"   Date range: {row['earliest_date']} to {row['latest_date']}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_claude_data_structure()