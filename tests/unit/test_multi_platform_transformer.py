"""Unit tests for multi-platform transformer."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date

from src.processing.multi_platform_transformer import MultiPlatformTransformer
from src.ingestion.cursor_client import CursorUsageData
from src.ingestion.anthropic_client import AnthropicUsageData, AnthropicCostData
from src.ingestion.sheets_client import APIKeyMapping
from src.processing.transformer import UsageFactRecord


@pytest.fixture
def multi_transformer():
    """Create MultiPlatformTransformer instance."""
    return MultiPlatformTransformer()


@pytest.fixture
def sample_cursor_data():
    """Sample Cursor usage data."""
    return [
        CursorUsageData(
            email="user1@company.com",
            total_lines_added=1000,
            accepted_lines_added=800,
            total_accepts=25,
            subscription_included_reqs=50,
            usage_based_reqs=10,
            date=datetime(2022, 1, 1)
        ),
        CursorUsageData(
            email="user2@company.com",
            total_lines_added=500,
            accepted_lines_added=400,
            total_accepts=15,
            subscription_included_reqs=30,
            usage_based_reqs=5,
            date=datetime(2022, 1, 1)
        )
    ]


@pytest.fixture
def sample_anthropic_data():
    """Sample Anthropic usage data."""
    return [
        AnthropicUsageData(
            api_key_id="key_123",
            workspace_id="ws_456",
            model="claude-3-sonnet-20240229",
            uncached_input_tokens=1000,
            cached_input_tokens=200,
            cache_read_input_tokens=150,
            output_tokens=500,
            usage_date=date(2022, 1, 1),
            usage_hour=12
        ),
        AnthropicUsageData(
            api_key_id="key_789",
            workspace_id="ws_456",
            model="claude-3-haiku-20240307",
            uncached_input_tokens=800,
            cached_input_tokens=100,
            cache_read_input_tokens=50,
            output_tokens=300,
            usage_date=date(2022, 1, 1),
            usage_hour=14
        )
    ]


@pytest.fixture
def sample_anthropic_cost_data():
    """Sample Anthropic cost data."""
    return [
        AnthropicCostData(
            api_key_id="key_123",
            workspace_id="ws_456",
            model="claude-3-sonnet-20240229",
            cost_usd=0.015,
            cost_type="input_tokens",
            cost_date=date(2022, 1, 1),
            cost_hour=12
        ),
        AnthropicCostData(
            api_key_id="key_123",
            workspace_id="ws_456",
            model="claude-3-sonnet-20240229",
            cost_usd=0.075,
            cost_type="output_tokens",
            cost_date=date(2022, 1, 1),
            cost_hour=12
        )
    ]


@pytest.fixture
def sample_api_key_mappings():
    """Sample API key mappings."""
    return [
        APIKeyMapping(
            api_key_name="key_123",
            user_email="john.doe@company.com",
            description="Production Claude API key",
            platform="anthropic"
        ),
        APIKeyMapping(
            api_key_name="key_789",
            user_email="jane.smith@company.com",
            description="Development Claude API key",
            platform="anthropic"
        )
    ]


class TestMultiPlatformTransformer:
    """Test cases for MultiPlatformTransformer."""

    def test_transform_all_usage_data_cursor_only(
        self,
        multi_transformer,
        sample_cursor_data
    ):
        """Test transformation with Cursor data only."""
        result = multi_transformer.transform_all_usage_data(
            cursor_data=sample_cursor_data,
            ingest_date=date(2022, 1, 2)
        )

        assert result["success"] is True
        assert len(result["usage_records"]) == 2
        assert result["transformation_stats"]["cursor"]["input"] == 2
        assert result["transformation_stats"]["cursor"]["output"] == 2
        assert result["transformation_stats"]["anthropic"]["input"] == 0
        assert result["transformation_stats"]["total_output"] == 2

        # Check that records have correct platform
        for record in result["usage_records"]:
            assert record.platform == "cursor"
            assert record.user_email in ["user1@company.com", "user2@company.com"]

    def test_transform_all_usage_data_anthropic_only(
        self,
        multi_transformer,
        sample_anthropic_data,
        sample_api_key_mappings
    ):
        """Test transformation with Anthropic data only."""
        result = multi_transformer.transform_all_usage_data(
            anthropic_data=sample_anthropic_data,
            api_key_mappings=sample_api_key_mappings,
            ingest_date=date(2022, 1, 2)
        )

        assert result["success"] is True
        assert len(result["usage_records"]) == 2
        assert result["transformation_stats"]["cursor"]["input"] == 0
        assert result["transformation_stats"]["anthropic"]["input"] == 2
        assert result["transformation_stats"]["anthropic"]["output"] == 2
        assert result["transformation_stats"]["total_output"] == 2

        # Check user attribution
        record_emails = {record.user_email for record in result["usage_records"]}
        assert "john.doe@company.com" in record_emails
        assert "jane.smith@company.com" in record_emails

    def test_transform_all_usage_data_multi_platform(
        self,
        multi_transformer,
        sample_cursor_data,
        sample_anthropic_data,
        sample_api_key_mappings
    ):
        """Test transformation with both platforms."""
        result = multi_transformer.transform_all_usage_data(
            cursor_data=sample_cursor_data,
            anthropic_data=sample_anthropic_data,
            api_key_mappings=sample_api_key_mappings,
            ingest_date=date(2022, 1, 2)
        )

        assert result["success"] is True
        assert len(result["usage_records"]) == 4  # 2 Cursor + 2 Anthropic
        assert result["transformation_stats"]["total_input"] == 4
        assert result["transformation_stats"]["total_output"] == 4

        # Check platform distribution
        platforms = {record.platform for record in result["usage_records"]}
        assert "cursor" in platforms
        assert "anthropic_api" in platforms

    def test_transform_all_usage_data_empty_input(self, multi_transformer):
        """Test transformation with no input data."""
        result = multi_transformer.transform_all_usage_data()

        assert result["success"] is True
        assert len(result["usage_records"]) == 0
        assert result["transformation_stats"]["total_input"] == 0
        assert result["transformation_stats"]["total_output"] == 0

    def test_apply_cursor_attribution(self, multi_transformer):
        """Test Cursor user attribution (email normalization)."""
        records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="cursor",
                user_email="  USER@EXAMPLE.COM  ",
                user_id=None,
                api_key_id=None,
                model=None,
                workspace_id=None,
                input_tokens=0,
                output_tokens=0,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=100,
                lines_of_code_accepted=80,
                acceptance_rate=0.8,
                total_accepts=5,
                subscription_requests=10,
                usage_based_requests=2,
                ingest_date=date.today(),
                request_id="test"
            )
        ]

        result = multi_transformer._apply_cursor_attribution(records)

        assert len(result) == 1
        assert result[0].user_email == "user@example.com"  # Normalized

    def test_apply_anthropic_attribution_success(
        self,
        multi_transformer,
        sample_api_key_mappings
    ):
        """Test successful Anthropic user attribution."""
        api_key_lookup = {
            mapping.api_key_name: mapping
            for mapping in sample_api_key_mappings
        }

        records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="anthropic_api",
                user_email="",
                user_id=None,
                api_key_id="key_123",
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=1000,
                output_tokens=500,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=0,
                lines_of_code_accepted=0,
                acceptance_rate=None,
                total_accepts=0,
                subscription_requests=1,
                usage_based_requests=0,
                ingest_date=date.today(),
                request_id="test"
            )
        ]

        result = multi_transformer._apply_anthropic_attribution(records, api_key_lookup)

        assert len(result) == 1
        assert result[0].user_email == "john.doe@company.com"
        assert result[0].platform == "anthropic"

    def test_apply_anthropic_attribution_unmapped_key(
        self,
        multi_transformer,
        sample_api_key_mappings
    ):
        """Test Anthropic attribution with unmapped API key."""
        api_key_lookup = {
            mapping.api_key_name: mapping
            for mapping in sample_api_key_mappings
        }

        records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="anthropic_api",
                user_email="",
                user_id=None,
                api_key_id="unmapped_key",  # Not in mappings
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=1000,
                output_tokens=500,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=0,
                lines_of_code_accepted=0,
                acceptance_rate=None,
                total_accepts=0,
                subscription_requests=1,
                usage_based_requests=0,
                ingest_date=date.today(),
                request_id="test"
            )
        ]

        result = multi_transformer._apply_anthropic_attribution(records, api_key_lookup)

        assert len(result) == 1
        assert result[0].user_email == ""  # Should remain empty
        assert result[0].api_key_id == "unmapped_key"

    def test_create_cost_records(
        self,
        multi_transformer,
        sample_anthropic_cost_data,
        sample_api_key_mappings
    ):
        """Test cost record creation with user attribution."""
        result = multi_transformer.create_cost_records(
            sample_anthropic_cost_data,
            sample_api_key_mappings,
            date(2022, 1, 2)
        )

        assert len(result) == 2  # Two cost records

        # Check user attribution
        for record in result:
            assert record["user_email"] == "john.doe@company.com"
            assert record["platform"] == "anthropic"
            assert record["api_key_id"] == "key_123"

    def test_validate_multi_platform_data_excellent(
        self,
        multi_transformer,
        sample_cursor_data,
        sample_anthropic_data,
        sample_api_key_mappings
    ):
        """Test validation with excellent data quality."""
        result = multi_transformer.validate_multi_platform_data(
            sample_cursor_data,
            sample_anthropic_data,
            sample_api_key_mappings
        )

        assert result["overall_status"] == "excellent"
        assert result["cursor_validation"]["valid"] == 2
        assert result["cursor_validation"]["invalid"] == 0
        assert result["anthropic_validation"]["valid"] == 2
        assert result["anthropic_validation"]["invalid"] == 0
        assert result["mapping_validation"]["coverage"] == 1.0

    def test_validate_multi_platform_data_poor_mapping(
        self,
        multi_transformer,
        sample_anthropic_data
    ):
        """Test validation with poor API key mapping coverage."""
        # No mappings provided
        result = multi_transformer.validate_multi_platform_data(
            anthropic_data=sample_anthropic_data,
            api_key_mappings=[]
        )

        assert result["overall_status"] == "needs_attention"
        assert result["mapping_validation"]["coverage"] == 0.0
        assert len(result["mapping_validation"]["issues"]) > 0

    def test_create_bigquery_rows(self, multi_transformer):
        """Test BigQuery row creation."""
        usage_records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="cursor",
                user_email="user@example.com",
                user_id=None,
                api_key_id=None,
                model=None,
                workspace_id=None,
                input_tokens=0,
                output_tokens=0,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=100,
                lines_of_code_accepted=80,
                acceptance_rate=0.8,
                total_accepts=5,
                subscription_requests=10,
                usage_based_requests=2,
                ingest_date=date.today(),
                request_id="test"
            )
        ]

        rows = multi_transformer.create_bigquery_rows(usage_records)

        assert len(rows) == 1
        assert rows[0]["platform"] == "cursor"
        assert rows[0]["user_email"] == "user@example.com"
        assert rows[0]["lines_of_code_added"] == 100

    def test_generate_transformation_summary(self, multi_transformer):
        """Test transformation summary generation."""
        transformation_result = {
            "transformation_stats": {
                "cursor": {"input": 2, "output": 2, "errors": []},
                "anthropic": {"input": 3, "output": 2, "errors": ["One error"]},
                "total_input": 5,
                "total_output": 4
            },
            "processing_time_seconds": 1.23,
            "ingest_date": "2022-01-01"
        }

        summary = multi_transformer.generate_transformation_summary(transformation_result)

        assert "Multi-Platform Data Transformation Summary" in summary
        assert "Processing Time: 1.23s" in summary
        assert "Cursor Platform:" in summary
        assert "Anthropic Platform:" in summary
        assert "Total Input: 5" in summary
        assert "Total Output: 4" in summary
        assert "Success Rate: 80.0%" in summary


    def test_anthropic_attribution_with_empty_lookup(self, multi_transformer):
        """Test Anthropic attribution with empty API key lookup."""
        records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="anthropic_api",
                user_email="",
                user_id=None,
                api_key_id="key_123",
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=1000,
                output_tokens=500,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=0,
                lines_of_code_accepted=0,
                acceptance_rate=None,
                total_accepts=0,
                subscription_requests=1,
                usage_based_requests=0,
                ingest_date=date.today(),
                request_id="test"
            )
        ]

        result = multi_transformer._apply_anthropic_attribution(records, {})

        assert len(result) == 1
        assert result[0].user_email == ""  # Should remain empty
        assert result[0].api_key_id == "key_123"