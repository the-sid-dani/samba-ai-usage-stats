#!/usr/bin/env python3
"""Show sample Anthropic data structure and aggregation logic."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Mock config
class MockConfig:
    anthropic_api_key = "test-key"

import src.shared.config as config_module
config_module.config = MockConfig()

from src.ingestion.anthropic_client import AnthropicUsageData, AnthropicCostData
from datetime import date

def show_sample_data():
    """Show sample Anthropic data structure."""
    print("📊 Sample Anthropic Data Structure")
    print("=" * 50)

    # Sample usage data showing different scenarios
    sample_usage_data = [
        # Scenario 1: Sid using Claude Code
        AnthropicUsageData(
            api_key_id="apikey_01J9JbaiunVv4t2C3wCVVmkV",
            workspace_id="wrkspc_01WtfAtqQsV3zBDs9RYpNZdR",
            model="claude-3-5-sonnet-20241022",
            uncached_input_tokens=15000,
            cached_input_tokens=2000,
            cache_read_input_tokens=1500,
            output_tokens=8000,
            usage_date=date(2024, 12, 27),
            usage_hour=10,
            platform="claude_code",
            attribution_method="api_key_mapping",
            attribution_confidence=0.95,
            user_email="sid.dani@samba.tv"
        ),

        # Scenario 2: Sid using Claude API (same day, different platform)
        AnthropicUsageData(
            api_key_id="apikey_01Ap5QMqkPdxe7zmXYo2awnc",
            workspace_id=None,
            model="claude-3-5-sonnet-20241022",
            uncached_input_tokens=25000,
            cached_input_tokens=0,
            cache_read_input_tokens=0,
            output_tokens=12000,
            usage_date=date(2024, 12, 27),
            usage_hour=14,
            platform="claude_api",
            attribution_method="api_key_mapping",
            attribution_confidence=0.95,
            user_email=None  # API keys don't have user email attribution
        ),

        # Scenario 3: Max using Claude Code (same day, same platform as Sid but different user)
        AnthropicUsageData(
            api_key_id="apikey_01Eb6TPyqUneJQqKBfv7Gti6",
            workspace_id="wrkspc_01WtfAtqQsV3zBDs9RYpNZdR",
            model="claude-3-5-sonnet-20241022",
            uncached_input_tokens=8000,
            cached_input_tokens=1000,
            cache_read_input_tokens=500,
            output_tokens=4000,
            usage_date=date(2024, 12, 27),
            usage_hour=11,
            platform="claude_code",
            attribution_method="api_key_mapping",
            attribution_confidence=0.95,
            user_email="max.roycroft@samba.tv"
        ),

        # Scenario 4: Unknown API key with workspace (workspace-based attribution)
        AnthropicUsageData(
            api_key_id="apikey_unknown_new_user",
            workspace_id="wrkspc_01WtfAtqQsV3zBDs9RYpNZdR",
            model="claude-3-haiku-20240307",
            uncached_input_tokens=5000,
            cached_input_tokens=0,
            cache_read_input_tokens=0,
            output_tokens=2000,
            usage_date=date(2024, 12, 27),
            usage_hour=16,
            platform="claude_code",
            attribution_method="workspace_mapping",
            attribution_confidence=0.75,
            user_email=None  # Can't extract email from unknown key
        )
    ]

    print("🔍 Raw Usage Records (as returned by AnthropicClient):")
    print()

    for i, record in enumerate(sample_usage_data, 1):
        print(f"Record {i}:")
        print(f"  📅 Date: {record.usage_date}")
        print(f"  ⏰ Hour: {record.usage_hour}")
        print(f"  🔑 API Key: {record.api_key_id}")
        print(f"  🏢 Workspace: {record.workspace_id}")
        print(f"  🤖 Model: {record.model}")
        print(f"  🎯 Platform: {record.platform}")
        print(f"  👤 User Email: {record.user_email}")
        print(f"  📊 Tokens: Input={record.uncached_input_tokens}, Cached={record.cached_input_tokens}, Output={record.output_tokens}")
        print(f"  🎯 Attribution: {record.attribution_method} (confidence: {record.attribution_confidence})")
        print()

    print("=" * 50)
    print("📈 DATA AGGREGATION EXPLANATION")
    print("=" * 50)

    print("\n🔹 GRANULARITY LEVEL:")
    print("✅ Each record represents: API_KEY + MODEL + DATE + HOUR")
    print("✅ NOT aggregated by user - each API key is separate")
    print("✅ HOURLY granularity when available")
    print()

    print("🔹 USER WITH MULTIPLE PLATFORMS:")
    print("If a user has claude_code, claude_api, and claude_web usage on the same day:")
    print("  📊 They will have 3+ separate records (one per API key/platform)")
    print("  📊 Each record has different api_key_id")
    print("  📊 Platform field distinguishes the usage type")
    print("  📊 User attribution happens via:")
    print("    - claude_code: API key name pattern → user email")
    print("    - claude_api: Manual mapping needed (no auto-email extraction)")
    print("    - claude_web: Future implementation")
    print()

    print("🔹 AGGREGATION HAPPENS DOWNSTREAM:")
    print("✅ Raw data: One record per API key + model + date + hour")
    print("✅ BigQuery views: Can aggregate by user_email across platforms")
    print("✅ Dashboard: Shows both per-platform and per-user totals")
    print()

    # Show how the same user would appear across platforms
    print("🔹 EXAMPLE: Sid's usage on 2024-12-27:")

    daily_summary = {}
    for record in sample_usage_data:
        if record.user_email == "sid.dani@samba.tv" or record.api_key_id == "apikey_01Ap5QMqkPdxe7zmXYo2awnc":
            key = f"{record.platform}"
            if key not in daily_summary:
                daily_summary[key] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "records": 0,
                    "api_keys": set()
                }
            daily_summary[key]["input_tokens"] += record.uncached_input_tokens + record.cached_input_tokens
            daily_summary[key]["output_tokens"] += record.output_tokens
            daily_summary[key]["records"] += 1
            daily_summary[key]["api_keys"].add(record.api_key_id)

    for platform, data in daily_summary.items():
        print(f"  {platform}: {data['input_tokens']:,} input + {data['output_tokens']:,} output tokens")
        print(f"    ({data['records']} records from {len(data['api_keys'])} API keys)")

    print("\n🎯 TOTAL DAILY RECORDS:")
    print(f"✅ {len(sample_usage_data)} raw records on 2024-12-27")
    print("✅ Multiple users, multiple platforms, multiple hours")
    print("✅ Each record maintains full granularity for analysis")

if __name__ == "__main__":
    show_sample_data()