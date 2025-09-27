"""Unit tests for data transformation engine."""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch

from src.processing.transformer import (
    DataValidator, CursorDataTransformer, DataTransformationPipeline,
    UsageFactRecord, ValidationResult
)
from src.ingestion.cursor_client import CursorUsageData


@pytest.fixture
def sample_cursor_data():
    """Sample Cursor usage data for testing."""
    return CursorUsageData(
        email="test@example.com",
        total_lines_added=1000,
        accepted_lines_added=800,
        total_accepts=25,
        subscription_included_reqs=50,
        usage_based_reqs=10,
        date=datetime(2022, 1, 1, 12, 0, 0)
    )


@pytest.fixture
def sample_usage_fact():
    """Sample usage fact record for testing."""
    return UsageFactRecord(
        usage_date=date(2022, 1, 1),
        platform="cursor",
        user_email="test@example.com",
        user_id=None,
        api_key_id=None,
        model=None,
        workspace_id=None,
        input_tokens=0,
        output_tokens=0,
        cached_input_tokens=0,
        cache_read_tokens=0,
        sessions=1,
        lines_of_code_added=1000,
        lines_of_code_accepted=800,
        acceptance_rate=0.8,
        total_accepts=25,
        subscription_requests=50,
        usage_based_requests=10,
        ingest_date=date.today(),
        request_id="test-request-id"
    )


class TestDataValidator:
    """Test cases for DataValidator."""

    def test_validate_cursor_data_valid(self, sample_cursor_data):
        """Test validation of valid Cursor data."""
        validator = DataValidator()
        result = validator.validate_cursor_data(sample_cursor_data)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_cursor_data_missing_email(self, sample_cursor_data):
        """Test validation with missing email."""
        validator = DataValidator()
        sample_cursor_data.email = ""

        result = validator.validate_cursor_data(sample_cursor_data)

        assert result.is_valid is False
        assert "Email is required" in str(result.errors)

    def test_validate_cursor_data_invalid_email(self, sample_cursor_data):
        """Test validation with invalid email format."""
        validator = DataValidator()
        sample_cursor_data.email = "invalid-email"

        result = validator.validate_cursor_data(sample_cursor_data)

        assert result.is_valid is False
        assert "Invalid email format" in str(result.errors)

    def test_validate_cursor_data_negative_values(self, sample_cursor_data):
        """Test validation with negative values."""
        validator = DataValidator()
        sample_cursor_data.total_lines_added = -100

        result = validator.validate_cursor_data(sample_cursor_data)

        assert result.is_valid is False
        assert "cannot be negative" in str(result.errors)

    def test_validate_cursor_data_accepted_greater_than_total(self, sample_cursor_data):
        """Test validation warning when accepted > total."""
        validator = DataValidator()
        sample_cursor_data.accepted_lines_added = 1200  # Greater than total (1000)

        result = validator.validate_cursor_data(sample_cursor_data)

        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) > 0
        assert "Accepted lines" in str(result.warnings)

    def test_validate_cursor_data_future_date(self, sample_cursor_data):
        """Test validation warning with future date."""
        validator = DataValidator()
        sample_cursor_data.date = datetime(2030, 1, 1)  # Future date

        result = validator.validate_cursor_data(sample_cursor_data)

        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) > 0
        assert "Future date" in str(result.warnings)

    def test_validate_usage_fact_valid(self, sample_usage_fact):
        """Test validation of valid usage fact."""
        validator = DataValidator()
        result = validator.validate_usage_fact(sample_usage_fact)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_usage_fact_missing_required_fields(self, sample_usage_fact):
        """Test validation with missing required fields."""
        validator = DataValidator()
        sample_usage_fact.user_email = ""
        sample_usage_fact.platform = ""

        result = validator.validate_usage_fact(sample_usage_fact)

        assert result.is_valid is False
        assert any("user_email is required" in error for error in result.errors)
        assert any("platform is required" in error for error in result.errors)

    def test_validate_usage_fact_invalid_platform(self, sample_usage_fact):
        """Test validation with invalid platform."""
        validator = DataValidator()
        sample_usage_fact.platform = "invalid_platform"

        result = validator.validate_usage_fact(sample_usage_fact)

        assert result.is_valid is False
        assert "Invalid platform" in str(result.errors)

    def test_validate_usage_fact_invalid_acceptance_rate(self, sample_usage_fact):
        """Test validation with invalid acceptance rate."""
        validator = DataValidator()
        sample_usage_fact.acceptance_rate = 1.5  # > 1.0

        result = validator.validate_usage_fact(sample_usage_fact)

        assert result.is_valid is False
        assert "acceptance_rate must be between 0.0 and 1.0" in str(result.errors)


class TestCursorDataTransformer:
    """Test cases for CursorDataTransformer."""

    def test_calculate_acceptance_rate_normal(self):
        """Test normal acceptance rate calculation."""
        transformer = CursorDataTransformer()
        rate = transformer.calculate_acceptance_rate(80, 100)
        assert rate == 0.8

    def test_calculate_acceptance_rate_zero_total(self):
        """Test acceptance rate calculation with zero total."""
        transformer = CursorDataTransformer()
        rate = transformer.calculate_acceptance_rate(0, 0)
        assert rate is None

    def test_calculate_acceptance_rate_rounding(self):
        """Test acceptance rate rounding."""
        transformer = CursorDataTransformer()
        rate = transformer.calculate_acceptance_rate(1, 3)
        assert rate == 0.3333  # Rounded to 4 decimal places

    def test_transform_cursor_data_single_record(self, sample_cursor_data):
        """Test transforming single Cursor record."""
        transformer = CursorDataTransformer()
        ingest_date = date(2022, 1, 2)

        result = transformer.transform_cursor_data([sample_cursor_data], ingest_date)

        assert len(result) == 1
        record = result[0]
        assert record.platform == "cursor"
        assert record.user_email == "test@example.com"
        assert record.usage_date == date(2022, 1, 1)
        assert record.lines_of_code_added == 1000
        assert record.lines_of_code_accepted == 800
        assert record.acceptance_rate == 0.8
        assert record.ingest_date == ingest_date

    def test_transform_cursor_data_multiple_records(self, sample_cursor_data):
        """Test transforming multiple Cursor records."""
        transformer = CursorDataTransformer()

        # Create multiple records
        data2 = CursorUsageData(
            email="user2@example.com",
            total_lines_added=500,
            accepted_lines_added=400,
            total_accepts=15,
            subscription_included_reqs=30,
            usage_based_reqs=5,
            date=datetime(2022, 1, 2)
        )

        result = transformer.transform_cursor_data([sample_cursor_data, data2])

        assert len(result) == 2
        assert result[0].user_email == "test@example.com"
        assert result[1].user_email == "user2@example.com"

    def test_transform_cursor_data_invalid_record(self):
        """Test transforming with invalid record."""
        transformer = CursorDataTransformer()

        invalid_data = CursorUsageData(
            email="",  # Invalid: empty email
            total_lines_added=100,
            accepted_lines_added=80,
            total_accepts=5,
            subscription_included_reqs=10,
            usage_based_reqs=2,
            date=datetime(2022, 1, 1)
        )

        result = transformer.transform_cursor_data([invalid_data])

        assert len(result) == 0  # Invalid record should be filtered out

    def test_transform_cursor_data_email_normalization(self, sample_cursor_data):
        """Test email normalization (lowercase, strip)."""
        transformer = CursorDataTransformer()
        sample_cursor_data.email = "  TEST@EXAMPLE.COM  "

        result = transformer.transform_cursor_data([sample_cursor_data])

        assert len(result) == 1
        assert result[0].user_email == "test@example.com"

    def test_to_bigquery_rows(self, sample_usage_fact):
        """Test conversion to BigQuery row format."""
        transformer = CursorDataTransformer()
        rows = transformer.to_bigquery_rows([sample_usage_fact])

        assert len(rows) == 1
        row = rows[0]

        # Check required fields
        assert row["usage_date"] == "2022-01-01"
        assert row["platform"] == "cursor"
        assert row["user_email"] == "test@example.com"
        assert row["lines_of_code_added"] == 1000
        assert row["lines_of_code_accepted"] == 800
        assert row["acceptance_rate"] == 0.8

        # Check null fields
        assert row["user_id"] is None
        assert row["api_key_id"] is None
        assert row["model"] is None

    def test_to_bigquery_rows_empty_list(self):
        """Test BigQuery conversion with empty list."""
        transformer = CursorDataTransformer()
        rows = transformer.to_bigquery_rows([])
        assert len(rows) == 0


class TestDataTransformationPipeline:
    """Test cases for DataTransformationPipeline."""

    def test_process_cursor_data_success(self, sample_cursor_data):
        """Test successful Cursor data processing."""
        pipeline = DataTransformationPipeline()
        result = pipeline.process_cursor_data([sample_cursor_data])

        assert result["success"] is True
        assert result["platform"] == "cursor"
        assert result["input_record_count"] == 1
        assert result["output_record_count"] == 1
        assert len(result["bigquery_rows"]) == 1
        assert "processing_time_seconds" in result
        assert "start_time" in result
        assert "end_time" in result

    def test_process_cursor_data_empty_input(self):
        """Test processing with empty input."""
        pipeline = DataTransformationPipeline()
        result = pipeline.process_cursor_data([])

        assert result["success"] is True
        assert result["input_record_count"] == 0
        assert result["output_record_count"] == 0
        assert len(result["bigquery_rows"]) == 0

    def test_process_cursor_data_with_invalid_records(self):
        """Test processing with mix of valid and invalid records."""
        pipeline = DataTransformationPipeline()

        valid_data = CursorUsageData(
            email="valid@example.com",
            total_lines_added=100,
            accepted_lines_added=80,
            total_accepts=5,
            subscription_included_reqs=10,
            usage_based_reqs=2,
            date=datetime(2022, 1, 1)
        )

        invalid_data = CursorUsageData(
            email="",  # Invalid
            total_lines_added=100,
            accepted_lines_added=80,
            total_accepts=5,
            subscription_included_reqs=10,
            usage_based_reqs=2,
            date=datetime(2022, 1, 1)
        )

        result = pipeline.process_cursor_data([valid_data, invalid_data])

        assert result["success"] is True
        assert result["input_record_count"] == 2
        assert result["output_record_count"] == 1  # Only valid record processed
        assert len(result["bigquery_rows"]) == 1


class TestUsageFactRecord:
    """Test cases for UsageFactRecord dataclass."""

    def test_usage_fact_record_creation(self):
        """Test UsageFactRecord creation."""
        record = UsageFactRecord(
            usage_date=date(2022, 1, 1),
            platform="cursor",
            user_email="test@example.com",
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
            request_id="test-id"
        )

        assert record.platform == "cursor"
        assert record.user_email == "test@example.com"
        assert record.lines_of_code_added == 100
        assert record.acceptance_rate == 0.8


class TestValidationResult:
    """Test cases for ValidationResult dataclass."""

    def test_validation_result_valid(self):
        """Test ValidationResult for valid data."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validation_result_invalid(self):
        """Test ValidationResult for invalid data."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1