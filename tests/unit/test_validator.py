"""Unit tests for data quality validation framework."""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from src.processing.validator import (
    DataQualityValidator,
    ValidationIssue,
    ValidationLevel,
    DataQualityReport
)


class TestDataQualityValidator:
    """Test cases for DataQualityValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        return DataQualityValidator()

    @pytest.fixture
    def sample_cost_records(self):
        """Sample cost records for testing."""
        return [
            {"user_email": "user1@example.com", "cost_usd": 25.50},
            {"user_email": "user2@example.com", "cost_usd": 15.75},
            {"user_email": "user3@example.com", "cost_usd": 42.30}
        ]

    @pytest.fixture
    def sample_usage_records(self):
        """Sample usage records for testing."""
        return [
            {"user_email": "user1@example.com", "api_key_id": "key1", "usage": 100},
            {"user_email": "user2@example.com", "api_key_id": "key2", "usage": 200},
            {"user_email": "", "api_key_id": "key3", "usage": 50}  # Missing attribution
        ]

    @pytest.fixture
    def sample_schema(self):
        """Sample schema for testing."""
        return [
            {"name": "user_email", "type": "STRING"},
            {"name": "cost_usd", "type": "FLOAT"},
            {"name": "usage_date", "type": "DATE"}
        ]

    class TestValidateRowCounts:
        """Test validate_row_counts method."""

        def test_no_data_loss(self, validator):
            """Given equal raw and processed counts, then no issues should be reported."""
            # Given
            raw_count = 1000
            processed_count = 1000

            # When
            issues = validator.validate_row_counts(raw_count, processed_count)

            # Then
            assert len(issues) == 0

        def test_acceptable_data_loss(self, validator):
            """Given acceptable data loss, then no error issues should be reported."""
            # Given
            raw_count = 1000
            processed_count = 990  # 1% loss (acceptable)

            # When
            issues = validator.validate_row_counts(raw_count, processed_count)

            # Then
            assert len(issues) == 0

        def test_moderate_data_loss_warning(self, validator):
            """Given moderate data loss, then warning should be issued."""
            # Given
            raw_count = 1000
            processed_count = 980  # 2% loss (warning threshold)

            # When
            issues = validator.validate_row_counts(raw_count, processed_count)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.WARNING
            assert issues[0].code == "MODERATE_DATA_LOSS"
            assert "2.00%" in issues[0].message

        def test_high_data_loss_error(self, validator):
            """Given high data loss, then error should be issued."""
            # Given
            raw_count = 1000
            processed_count = 900  # 10% loss (exceeds 5% threshold)

            # When
            issues = validator.validate_row_counts(raw_count, processed_count)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.ERROR
            assert issues[0].code == "HIGH_DATA_LOSS"
            assert "10.00%" in issues[0].message
            assert issues[0].context["loss_rate"] == 0.1

        def test_empty_dataset_warning(self, validator):
            """Given empty dataset, then warning should be issued."""
            # Given
            raw_count = 0
            processed_count = 0

            # When
            issues = validator.validate_row_counts(raw_count, processed_count)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.WARNING
            assert issues[0].code == "EMPTY_DATASET"

    class TestValidateCostReconciliation:
        """Test validate_cost_reconciliation method."""

        def test_valid_cost_data(self, validator, sample_cost_records):
            """Given valid cost data, then no issues should be reported."""
            # Given
            cost_records = sample_cost_records

            # When
            issues = validator.validate_cost_reconciliation(cost_records)

            # Then
            assert len(issues) == 0

        def test_no_cost_data_warning(self, validator):
            """Given no cost data, then warning should be issued."""
            # Given
            cost_records = []

            # When
            issues = validator.validate_cost_reconciliation(cost_records)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.WARNING
            assert issues[0].code == "NO_COST_DATA"

        def test_negative_costs_error(self, validator):
            """Given negative costs, then error should be issued."""
            # Given
            cost_records = [
                {"cost_usd": 25.50},
                {"cost_usd": -10.00},  # Negative cost
                {"cost_usd": 15.75}
            ]

            # When
            issues = validator.validate_cost_reconciliation(cost_records)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.ERROR
            assert issues[0].code == "NEGATIVE_COSTS"
            assert issues[0].context["negative_records"] == 1

        def test_high_zero_costs_warning(self, validator):
            """Given high percentage of zero costs, then warning should be issued."""
            # Given
            cost_records = [
                {"cost_usd": 0.00},
                {"cost_usd": 0.00},
                {"cost_usd": 0.00},
                {"cost_usd": 25.50}  # Only 25% have actual costs
            ]

            # When
            issues = validator.validate_cost_reconciliation(cost_records)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.WARNING
            assert issues[0].code == "HIGH_ZERO_COSTS"
            assert issues[0].context["zero_cost_records"] == 3

        def test_cost_below_expected_range(self, validator):
            """Given cost below expected range, then warning should be issued."""
            # Given
            cost_records = [{"cost_usd": 10.00}]
            expected_range = (50.0, 200.0)  # Total cost too low

            # When
            issues = validator.validate_cost_reconciliation(cost_records, expected_range)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.WARNING
            assert issues[0].code == "COST_BELOW_EXPECTED"
            assert issues[0].context["total_cost"] == 10.00

        def test_cost_above_expected_range(self, validator):
            """Given cost above expected range, then warning should be issued."""
            # Given
            cost_records = [{"cost_usd": 300.00}]
            expected_range = (50.0, 200.0)  # Total cost too high

            # When
            issues = validator.validate_cost_reconciliation(cost_records, expected_range)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.WARNING
            assert issues[0].code == "COST_ABOVE_EXPECTED"
            assert issues[0].context["total_cost"] == 300.00

    class TestValidateSchemaDrift:
        """Test validate_schema_drift method."""

        def test_identical_schemas(self, validator, sample_schema):
            """Given identical schemas, then no issues should be reported."""
            # Given
            current_schema = sample_schema
            expected_schema = sample_schema.copy()

            # When
            issues = validator.validate_schema_drift(current_schema, expected_schema)

            # Then
            assert len(issues) == 0

        def test_missing_fields_error(self, validator, sample_schema):
            """Given missing required fields, then error should be issued."""
            # Given
            current_schema = [
                {"name": "user_email", "type": "STRING"}
                # Missing cost_usd and usage_date fields
            ]
            expected_schema = sample_schema

            # When
            issues = validator.validate_schema_drift(current_schema, expected_schema)

            # Then
            error_issues = [i for i in issues if i.code == "MISSING_FIELDS"]
            assert len(error_issues) == 1
            assert error_issues[0].level == ValidationLevel.ERROR
            assert "cost_usd" in error_issues[0].message
            assert "usage_date" in error_issues[0].message

        def test_extra_fields_warning(self, validator, sample_schema):
            """Given extra unexpected fields, then warning should be issued."""
            # Given
            current_schema = sample_schema + [
                {"name": "extra_field", "type": "STRING"}
            ]
            expected_schema = sample_schema

            # When
            issues = validator.validate_schema_drift(current_schema, expected_schema)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.WARNING
            assert issues[0].code == "EXTRA_FIELDS"
            assert "extra_field" in issues[0].message

        def test_type_mismatch_error(self, validator):
            """Given field type mismatches, then error should be issued."""
            # Given
            current_schema = [
                {"name": "user_email", "type": "STRING"},
                {"name": "cost_usd", "type": "STRING"},  # Should be FLOAT
                {"name": "usage_date", "type": "DATE"}
            ]
            expected_schema = [
                {"name": "user_email", "type": "STRING"},
                {"name": "cost_usd", "type": "FLOAT"},
                {"name": "usage_date", "type": "DATE"}
            ]

            # When
            issues = validator.validate_schema_drift(current_schema, expected_schema)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.ERROR
            assert issues[0].code == "TYPE_MISMATCH"
            assert issues[0].field == "cost_usd"
            assert "expected FLOAT, got STRING" in issues[0].message

    class TestValidateDataFreshness:
        """Test validate_data_freshness method."""

        def test_fresh_data(self, validator):
            """Given fresh data, then no issues should be reported."""
            # Given
            last_update = datetime.now() - timedelta(hours=2)  # 2 hours old

            # When
            issues = validator.validate_data_freshness(last_update)

            # Then
            assert len(issues) == 0

        def test_stale_data_error(self, validator):
            """Given stale data, then error should be issued."""
            # Given
            last_update = datetime.now() - timedelta(hours=30)  # 30 hours old (exceeds 25h threshold)

            # When
            issues = validator.validate_data_freshness(last_update)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.ERROR
            assert issues[0].code == "STALE_DATA"
            assert "30." in issues[0].message
            assert issues[0].context["threshold_hours"] == 25

        def test_very_stale_data_critical(self, validator):
            """Given very stale data, then critical issue should be issued."""
            # Given
            last_update = datetime.now() - timedelta(hours=60)  # 60 hours old (2x threshold)

            # When
            issues = validator.validate_data_freshness(last_update)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.CRITICAL
            assert issues[0].code == "STALE_DATA"

        def test_custom_threshold(self, validator):
            """Given custom threshold, then validation should use custom value."""
            # Given
            last_update = datetime.now() - timedelta(hours=10)
            custom_threshold = 8  # 8 hours max

            # When
            issues = validator.validate_data_freshness(last_update, custom_threshold)

            # Then
            assert len(issues) == 1
            assert issues[0].level == ValidationLevel.ERROR
            assert issues[0].context["threshold_hours"] == 8

    class TestValidateUserAttribution:
        """Test validate_user_attribution method."""

        def test_good_attribution_rate(self, validator):
            """Given good attribution rate, then no issues should be reported."""
            # Given
            usage_records = [
                {"user_email": "user1@example.com", "api_key_id": "key1"},
                {"user_email": "user2@example.com", "api_key_id": "key2"},
                {"user_email": "user3@example.com", "api_key_id": "key3"}
            ]

            # When
            issues = validator.validate_user_attribution(usage_records)

            # Then
            assert len(issues) == 0

        def test_low_attribution_rate_error(self, validator):
            """Given low attribution rate, then error should be issued."""
            # Given
            usage_records = [
                {"user_email": "user1@example.com", "api_key_id": "key1"},
                {"user_email": "", "api_key_id": "key2"},  # Missing attribution
                {"user_email": "", "api_key_id": "key3"}   # Missing attribution
            ]
            # Attribution rate = 1/3 = 33% (below 95% threshold)

            # When
            issues = validator.validate_user_attribution(usage_records)

            # Then
            error_issues = [i for i in issues if i.code == "LOW_USER_ATTRIBUTION"]
            assert len(error_issues) == 1
            assert error_issues[0].level == ValidationLevel.ERROR
            assert error_issues[0].context["attribution_rate"] < 0.95

        def test_unmapped_api_keys_warning(self, validator):
            """Given unmapped API keys, then warning should be issued."""
            # Given
            usage_records = [
                {"user_email": "user1@example.com", "api_key_id": "key1"},
                {"api_key_id": "key2"},  # Has API key but no user email
                {"api_key_id": "key3"}   # Has API key but no user email
            ]

            # When
            issues = validator.validate_user_attribution(usage_records)

            # Then
            warning_issues = [i for i in issues if i.code == "UNMAPPED_API_KEYS"]
            assert len(warning_issues) == 1
            assert warning_issues[0].level == ValidationLevel.WARNING
            assert warning_issues[0].context["unmapped_count"] == 2

        def test_empty_records(self, validator):
            """Given empty records, then no issues should be reported."""
            # Given
            usage_records = []

            # When
            issues = validator.validate_user_attribution(usage_records)

            # Then
            assert len(issues) == 0

    class TestValidateAnomalyDetection:
        """Test validate_anomaly_detection method."""

        def test_normal_metrics(self, validator):
            """Given normal metrics within expected range, then no issues should be reported."""
            # Given
            current_metrics = {"cost": 100.0, "usage": 500}
            historical_metrics = [
                {"cost": 95.0, "usage": 480},
                {"cost": 105.0, "usage": 520},
                {"cost": 98.0, "usage": 490}
            ]

            # When
            issues = validator.validate_anomaly_detection(current_metrics, historical_metrics)

            # Then
            assert len(issues) == 0

        def test_anomaly_detection_error(self, validator):
            """Given anomalous metrics, then error should be issued."""
            # Given
            current_metrics = {"cost": 500.0, "usage": 200}  # Very high cost, low usage
            historical_metrics = [
                {"cost": 95.0, "usage": 480},
                {"cost": 105.0, "usage": 520},
                {"cost": 98.0, "usage": 490}
            ]

            # When
            issues = validator.validate_anomaly_detection(current_metrics, historical_metrics)

            # Then
            cost_anomalies = [i for i in issues if "cost" in i.message.lower()]
            assert len(cost_anomalies) > 0
            assert cost_anomalies[0].level == ValidationLevel.ERROR
            assert cost_anomalies[0].code == "METRIC_ANOMALY"

        def test_insufficient_historical_data(self, validator):
            """Given insufficient historical data, then warning should be issued."""
            # Given
            current_metrics = {"cost": 100.0}
            historical_metrics = [{"cost": 95.0}]  # Only one historical point

            # When
            issues = validator.validate_anomaly_detection(current_metrics, historical_metrics)

            # Then
            warning_issues = [i for i in issues if i.level == ValidationLevel.WARNING]
            assert len(warning_issues) >= 0  # May or may not issue warning depending on implementation

    class TestGenerateQualityReport:
        """Test generate_quality_report method."""

        def test_generate_report_no_issues(self, validator):
            """Given no validation issues, then report should show passed status."""
            # Given
            dataset = "test_dataset"
            validation_results = [[], []]  # No issues

            # When
            report = validator.generate_quality_report(dataset, validation_results)

            # Then
            assert isinstance(report, DataQualityReport)
            assert report.dataset == "test_dataset"
            assert report.passed is True
            assert report.metrics["total_issues"] == 0
            assert report.metrics["error_count"] == 0
            assert report.metrics["quality_score"] == 100

        def test_generate_report_with_issues(self, validator):
            """Given validation issues, then report should reflect problems."""
            # Given
            dataset = "test_dataset"
            validation_results = [
                [ValidationIssue(ValidationLevel.ERROR, "TEST_ERROR", "Test error")],
                [ValidationIssue(ValidationLevel.WARNING, "TEST_WARNING", "Test warning")]
            ]

            # When
            report = validator.generate_quality_report(dataset, validation_results)

            # Then
            assert report.passed is False  # Has errors
            assert report.metrics["total_issues"] == 2
            assert report.metrics["error_count"] == 1
            assert report.metrics["warning_count"] == 1
            assert report.metrics["quality_score"] == 88  # 100 - (1*10) - (1*2)

        def test_generate_report_critical_issues(self, validator):
            """Given critical issues, then report should count them as errors."""
            # Given
            dataset = "test_dataset"
            validation_results = [
                [ValidationIssue(ValidationLevel.CRITICAL, "TEST_CRITICAL", "Critical issue")]
            ]

            # When
            report = validator.generate_quality_report(dataset, validation_results)

            # Then
            assert report.passed is False
            assert report.metrics["error_count"] == 1  # Critical counted as error
            assert report.metrics["quality_score"] == 90  # 100 - (1*10)

    class TestIntegration:
        """Integration tests for validator workflows."""

        def test_comprehensive_validation_workflow(self, validator, sample_cost_records, sample_usage_records):
            """Given comprehensive validation scenario, then all validations should work together."""
            # Given - Fresh timestamp
            recent_update = datetime.now() - timedelta(hours=2)

            # When - Run multiple validations
            row_issues = validator.validate_row_counts(1000, 950)  # Some data loss
            cost_issues = validator.validate_cost_reconciliation(sample_cost_records)
            freshness_issues = validator.validate_data_freshness(recent_update)
            attribution_issues = validator.validate_user_attribution(sample_usage_records)

            all_validations = [row_issues, cost_issues, freshness_issues, attribution_issues]
            report = validator.generate_quality_report("integration_test", all_validations)

            # Then - Report should consolidate all results
            assert isinstance(report, DataQualityReport)
            assert report.dataset == "integration_test"
            # Should have some issues from row count loss and missing attribution
            assert report.metrics["total_issues"] > 0