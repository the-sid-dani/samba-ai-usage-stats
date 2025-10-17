#!/usr/bin/env python3
"""Query real Anthropic data from BigQuery to show actual structure."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from google.cloud import bigquery
import json

# Mock config for platform detection
class MockConfig:
    anthropic_api_key = "test-key"

import src.shared.config as config_module
config_module.config = MockConfig()

from src.ingestion.anthropic_client import AnthropicClient

def query_real_data():
    """Query real Anthropic data from BigQuery."""
    print("🔍 REAL ANTHROPIC DATA FROM BIGQUERY")
    print("=" * 50)

    client = bigquery.Client(project='ai-workflows-459123')

    # Query raw Anthropic usage with date filter
    usage_query = """
    SELECT
      api_key_id,
      workspace_id,
      model,
      uncached_input_tokens,
      cached_input_tokens,
      cache_read_input_tokens,
      output_tokens,
      usage_date,
      usage_hour,
      raw_response
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
    LIMIT 5
    """

    print("📊 REAL USAGE DATA STRUCTURE:")
    print("-" * 30)

    try:
        usage_results = client.query(usage_query).result()

        # Set up platform detection
        mock_client = AnthropicClient.__new__(AnthropicClient)
        mock_client.logger = None

        api_mappings = mock_client._get_api_key_mappings()
        workspace_mappings = mock_client._get_workspace_mappings()

        for i, row in enumerate(usage_results, 1):
            print(f"\nRecord {i}:")
            print(f"  api_key_id: {row.api_key_id}")
            print(f"  workspace_id: {row.workspace_id}")
            print(f"  model: {row.model}")
            print(f"  usage_date: {row.usage_date}")
            print(f"  usage_hour: {row.usage_hour}")
            print(f"  uncached_input_tokens: {row.uncached_input_tokens:,}")
            print(f"  cached_input_tokens: {row.cached_input_tokens:,}")
            print(f"  cache_read_input_tokens: {row.cache_read_input_tokens:,}")
            print(f"  output_tokens: {row.output_tokens:,}")

            total_input = (row.uncached_input_tokens or 0) + (row.cached_input_tokens or 0)
            total_tokens = total_input + (row.output_tokens or 0)
            print(f"  📊 TOTALS: {total_input:,} input + {row.output_tokens or 0:,} output = {total_tokens:,} total")

            # Apply our new platform detection
            platform, method, confidence, email = mock_client._categorize_platform(
                row.api_key_id, row.workspace_id, api_mappings, workspace_mappings
            )

            print(f"  🎯 PLATFORM DETECTION:")
            print(f"    platform: {platform}")
            print(f"    attribution_method: {method}")
            print(f"    attribution_confidence: {confidence}")
            print(f"    user_email: {email}")

    except Exception as e:
        print(f"❌ Usage query error: {e}")

    # Also check cost data
    cost_query = """
    SELECT
      api_key_id,
      workspace_id,
      model,
      cost_usd,
      cost_type,
      cost_date,
      cost_hour
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_cost`
    WHERE ingest_date >= '2025-09-27'
    LIMIT 3
    """

    print("\n💰 REAL COST DATA STRUCTURE:")
    print("-" * 30)

    try:
        cost_results = client.query(cost_query).result()

        for i, row in enumerate(cost_results, 1):
            print(f"\nCost Record {i}:")
            print(f"  api_key_id: {row.api_key_id}")
            print(f"  workspace_id: {row.workspace_id}")
            print(f"  model: {row.model}")
            print(f"  cost_date: {row.cost_date}")
            print(f"  cost_hour: {row.cost_hour}")
            print(f"  cost_usd: ${row.cost_usd:.4f}")
            print(f"  cost_type: {row.cost_type}")

            # Apply platform detection to cost data too
            platform, method, confidence, email = mock_client._categorize_platform(
                row.api_key_id, row.workspace_id, api_mappings, workspace_mappings
            )

            print(f"  🎯 PLATFORM: {platform} ({method}, {confidence:.2f})")
            print(f"  👤 USER: {email}")

    except Exception as e:
        print(f"❌ Cost query error: {e}")

    print("\n🔍 PLATFORM MAPPING SUMMARY:")
    print("-" * 25)
    print(f"✅ API Key Mappings: {len(api_mappings)} keys loaded")
    print(f"✅ Workspace Mappings: {len(workspace_mappings)} workspaces loaded")

    # Show a few key mappings
    claude_code_keys = {k: v for k, v in api_mappings.items() if v.get('platform') == 'claude_code'}
    claude_api_keys = {k: v for k, v in api_mappings.items() if v.get('platform') == 'claude_api'}

    print(f"🔹 Claude Code keys: {len(claude_code_keys)}")
    print(f"🔹 Claude API keys: {len(claude_api_keys)}")

if __name__ == "__main__":
    query_real_data()