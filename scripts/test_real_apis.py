#!/usr/bin/env python3
"""Test real API connections with actual data."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime, date, timedelta
from shared.logging_setup import setup_logging
from shared.config import config
from ingestion.cursor_client import CursorClient, CursorAPIError
from ingestion.anthropic_client import AnthropicClient, AnthropicAPIError


def test_cursor_api():
    """Test Cursor API with real credentials."""
    print("\n" + "="*50)
    print("TESTING CURSOR API")
    print("="*50)

    try:
        # Check API key
        if not config.cursor_api_key:
            print("❌ Cursor API key not found in configuration")
            return False

        print(f"✓ Cursor API key loaded: {config.cursor_api_key[:12]}...")

        # Create client
        cursor_client = CursorClient()
        print("✓ Cursor client initialized")

        # Test health check
        print("\n1. Health Check...")
        if cursor_client.health_check():
            print("✓ Cursor API health check: PASSED")
        else:
            print("❌ Cursor API health check: FAILED")
            return False

        # Test recent data retrieval
        print("\n2. Testing Recent Data (7 days)...")
        recent_data = cursor_client.get_recent_usage(days=7)
        print(f"✓ Retrieved {len(recent_data)} records from last 7 days")

        if recent_data:
            # Show sample data
            sample = recent_data[0]
            print(f"✓ Sample record:")
            print(f"  Email: {sample.email}")
            print(f"  Total Lines Added: {sample.total_lines_added}")
            print(f"  Accepted Lines: {sample.accepted_lines_added}")
            print(f"  Acceptance Rate: {sample.accepted_lines_added/sample.total_lines_added:.1%}" if sample.total_lines_added > 0 else "  Acceptance Rate: N/A")
            print(f"  Date: {sample.date}")

            # Test data validation
            from processing.transformer import DataValidator
            validator = DataValidator()
            validation = validator.validate_cursor_data(sample)

            if validation.is_valid:
                print("✓ Data validation: PASSED")
            else:
                print(f"⚠️  Data validation issues: {validation.errors}")

        else:
            print("ℹ️  No recent data found (may be normal for new API keys)")

        return True

    except CursorAPIError as e:
        print(f"❌ Cursor API Error: {e}")
        if hasattr(e, 'status_code'):
            print(f"   Status Code: {e.status_code}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_anthropic_api():
    """Test Anthropic API with real credentials."""
    print("\n" + "="*50)
    print("TESTING ANTHROPIC API")
    print("="*50)

    try:
        # Check API key
        if not config.anthropic_api_key:
            print("❌ Anthropic API key not found in configuration")
            return False

        print(f"✓ Anthropic API key loaded: {config.anthropic_api_key[:15]}...")

        # Create client
        anthropic_client = AnthropicClient()
        print("✓ Anthropic client initialized")

        # Test health check
        print("\n1. Health Check...")
        if anthropic_client.health_check():
            print("✓ Anthropic API health check: PASSED")
        else:
            print("❌ Anthropic API health check: FAILED")
            return False

        # Test recent usage data
        print("\n2. Testing Recent Usage Data (7 days)...")
        recent_usage = anthropic_client.get_recent_usage(days=7)
        print(f"✓ Retrieved {len(recent_usage)} usage records from last 7 days")

        if recent_usage:
            # Show sample usage data
            sample = recent_usage[0]
            print(f"✓ Sample usage record:")
            print(f"  API Key ID: {sample.api_key_id}")
            print(f"  Model: {sample.model}")
            print(f"  Input Tokens: {sample.uncached_input_tokens + sample.cached_input_tokens}")
            print(f"  Output Tokens: {sample.output_tokens}")
            print(f"  Cache Read Tokens: {sample.cache_read_input_tokens}")
            print(f"  Usage Date: {sample.usage_date}")

        # Test recent cost data
        print("\n3. Testing Recent Cost Data (7 days)...")
        recent_costs = anthropic_client.get_recent_costs(days=7)
        print(f"✓ Retrieved {len(recent_costs)} cost records from last 7 days")

        if recent_costs:
            # Show sample cost data
            sample_cost = recent_costs[0]
            print(f"✓ Sample cost record:")
            print(f"  API Key ID: {sample_cost.api_key_id}")
            print(f"  Model: {sample_cost.model}")
            print(f"  Cost: ${sample_cost.cost_usd:.6f}")
            print(f"  Cost Type: {sample_cost.cost_type}")
            print(f"  Cost Date: {sample_cost.cost_date}")

            # Calculate total costs
            total_cost = sum(cost.cost_usd for cost in recent_costs)
            print(f"✓ Total cost (7 days): ${total_cost:.4f}")

        # Test supported models
        print("\n4. Testing Supported Models...")
        models = anthropic_client.get_supported_models()
        print(f"✓ Supported models: {', '.join(models[:3])}...")

        return True

    except AnthropicAPIError as e:
        print(f"❌ Anthropic API Error: {e}")
        if hasattr(e, 'status_code'):
            print(f"   Status Code: {e.status_code}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_transformation():
    """Test data transformation with real API data."""
    print("\n" + "="*50)
    print("TESTING DATA TRANSFORMATION")
    print("="*50)

    try:
        # Get real data from both APIs
        cursor_client = CursorClient()
        anthropic_client = AnthropicClient()

        print("1. Fetching real data...")
        cursor_data = cursor_client.get_recent_usage(days=3)
        anthropic_data = anthropic_client.get_recent_usage(days=3)

        print(f"✓ Cursor records: {len(cursor_data)}")
        print(f"✓ Anthropic records: {len(anthropic_data)}")

        # Test transformation
        print("\n2. Testing transformation...")
        from processing.multi_platform_transformer import MultiPlatformTransformer
        transformer = MultiPlatformTransformer()

        # Note: Without Google Sheets setup, Anthropic records won't have user attribution
        result = transformer.transform_all_usage_data(
            cursor_data=cursor_data,
            anthropic_data=anthropic_data,
            api_key_mappings=[]  # Empty for now
        )

        print(f"✓ Transformation successful: {result['success']}")
        print(f"✓ Input records: {result['transformation_stats']['total_input']}")
        print(f"✓ Output records: {result['transformation_stats']['total_output']}")

        # Show platform breakdown
        platform_counts = {}
        for record in result["usage_records"]:
            platform_counts[record.platform] = platform_counts.get(record.platform, 0) + 1

        print(f"✓ Platform distribution:")
        for platform, count in platform_counts.items():
            print(f"  {platform}: {count} records")

        # Show user emails found
        user_emails = {record.user_email for record in result["usage_records"] if record.user_email}
        print(f"✓ Users with direct attribution: {len(user_emails)}")
        for email in sorted(user_emails):
            print(f"  {email}")

        return True

    except Exception as e:
        print(f"❌ Transformation test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all real API tests."""
    logger = setup_logging()
    logger.info("Starting real API testing")

    print("🧪 AI USAGE ANALYTICS - REAL API TESTING")
    print("=" * 60)

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    test_results = []

    # Test Cursor API
    cursor_success = test_cursor_api()
    test_results.append(("Cursor API", cursor_success))

    # Test Anthropic API
    anthropic_success = test_anthropic_api()
    test_results.append(("Anthropic API", anthropic_success))

    # Test transformation (only if APIs work)
    if cursor_success or anthropic_success:
        transform_success = test_data_transformation()
        test_results.append(("Data Transformation", transform_success))

    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)

    all_passed = True
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 ALL API TESTS PASSED!")
        print("✓ Real data is flowing correctly from APIs")
        print("✓ Data transformation is working")
        print("✓ Ready for Google Sheets setup and full pipeline testing")
    else:
        print("⚠️  Some tests failed - check API keys and configurations")

    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test script failed: {e}")
        sys.exit(1)