#!/usr/bin/env python3
"""Test script for multi-platform pipeline integration."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime, date
from processing.multi_platform_transformer import MultiPlatformTransformer
from ingestion.cursor_client import CursorUsageData
from ingestion.anthropic_client import AnthropicUsageData
from ingestion.sheets_client import APIKeyMapping
from processing.attribution import UserAttributionEngine
from shared.logging_setup import setup_logging


def test_pipeline_integration():
    """Test complete multi-platform pipeline integration."""
    logger = setup_logging()
    logger.info("Testing multi-platform pipeline integration")

    # Create test data
    cursor_data = [
        CursorUsageData(
            email="john.doe@company.com",
            total_lines_added=1500,
            accepted_lines_added=1200,
            total_accepts=45,
            subscription_included_reqs=100,
            usage_based_reqs=25,
            date=datetime(2022, 1, 1)
        ),
        CursorUsageData(
            email="jane.smith@company.com",
            total_lines_added=800,
            accepted_lines_added=600,
            total_accepts=22,
            subscription_included_reqs=50,
            usage_based_reqs=10,
            date=datetime(2022, 1, 1)
        )
    ]

    anthropic_data = [
        AnthropicUsageData(
            api_key_id="key_prod_123",
            workspace_id="ws_456",
            model="claude-3-sonnet-20240229",
            uncached_input_tokens=2000,
            cached_input_tokens=300,
            cache_read_input_tokens=200,
            output_tokens=1000,
            usage_date=date(2022, 1, 1),
            usage_hour=12
        )
    ]

    api_mappings = [
        APIKeyMapping(
            api_key_name="key_prod_123",
            user_email="sarah.wilson@company.com",
            description="Production Claude API key",
            platform="anthropic"
        )
    ]

    print("\n" + "="*50)
    print("MULTI-PLATFORM PIPELINE INTEGRATION TEST")
    print("="*50)

    # Test 1: Multi-platform transformation
    print("\n1. Testing Multi-Platform Transformation...")
    transformer = MultiPlatformTransformer()

    result = transformer.transform_all_usage_data(
        cursor_data=cursor_data,
        anthropic_data=anthropic_data,
        api_key_mappings=api_mappings
    )

    print(f"✓ Input Records: {result['transformation_stats']['total_input']}")
    print(f"✓ Output Records: {result['transformation_stats']['total_output']}")
    print(f"✓ Processing Time: {result['processing_time_seconds']:.2f}s")

    # Test 2: User Attribution
    print("\n2. Testing User Attribution...")
    unique_users = {record.user_email for record in result["usage_records"]}
    print(f"✓ Unique Users: {len(unique_users)}")
    print(f"✓ Users: {', '.join(sorted(unique_users))}")

    # Test 3: Platform Distribution
    print("\n3. Testing Platform Distribution...")
    platform_counts = {}
    for record in result["usage_records"]:
        platform_counts[record.platform] = platform_counts.get(record.platform, 0) + 1

    for platform, count in platform_counts.items():
        print(f"✓ {platform}: {count} records")

    # Test 4: Data Quality Validation
    print("\n4. Testing Data Quality...")
    validation_result = transformer.validate_multi_platform_data(
        cursor_data=cursor_data,
        anthropic_data=anthropic_data,
        api_key_mappings=api_mappings
    )

    print(f"✓ Overall Status: {validation_result['overall_status']}")
    print(f"✓ Cursor Valid: {validation_result['cursor_validation']['valid']}")
    print(f"✓ Anthropic Valid: {validation_result['anthropic_validation']['valid']}")
    print(f"✓ Attribution Coverage: {validation_result['mapping_validation']['coverage']:.1%}")

    # Test 5: BigQuery Row Format
    print("\n5. Testing BigQuery Integration...")
    bigquery_rows = transformer.create_bigquery_rows(result["usage_records"])
    print(f"✓ BigQuery Rows: {len(bigquery_rows)}")

    # Sample row validation
    if bigquery_rows:
        sample_row = bigquery_rows[0]
        required_fields = ["usage_date", "platform", "user_email", "ingest_date"]
        missing_fields = [field for field in required_fields if field not in sample_row]

        if missing_fields:
            print(f"✗ Missing fields: {missing_fields}")
        else:
            print("✓ All required fields present in BigQuery rows")

    # Test 6: Transformation Summary
    print("\n6. Transformation Summary:")
    summary = transformer.generate_transformation_summary(result)
    print(summary)

    print("\n" + "="*50)
    print("INTEGRATION TEST RESULTS")
    print("="*50)

    success_criteria = [
        ("Multi-platform processing", result["success"]),
        ("Data transformation", len(result["usage_records"]) > 0),
        ("User attribution", len(unique_users) >= 2),
        ("Platform coverage", len(platform_counts) >= 2),
        ("Data quality", validation_result["overall_status"] != "critical"),
        ("BigQuery format", len(bigquery_rows) > 0)
    ]

    all_passed = True
    for criteria, passed in success_criteria:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} {criteria}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("Multi-platform pipeline is ready for Phase 3")
        return True
    else:
        print("❌ Some integration tests failed")
        print("Please review the issues above")
        return False


if __name__ == "__main__":
    try:
        success = test_pipeline_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)