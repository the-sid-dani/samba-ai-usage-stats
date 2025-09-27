"""Data quality validation and monitoring for AI Usage Analytics Dashboard."""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import json
import statistics
from decimal import Decimal

from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from ..shared.logging_setup import get_logger, RequestContextLogger
from ..shared.cloud_monitoring import get_cloud_monitoring
from ..shared.error_tracker import error_tracker, ErrorCategory
from ..shared.config import config


class ValidationLevel(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a data quality issue."""
    level: ValidationLevel
    code: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class DataQualityReport:
    """Comprehensive data quality assessment report."""
    dataset: str
    evaluation_date: datetime
    total_records: int
    valid_records: int
    issues: List[ValidationIssue]
    metrics: Dict[str, float]
    passed: bool


class DataQualityValidator:
    """Comprehensive data quality validation framework."""

    def __init__(self):
        self.logger = get_logger("data_quality_validator")

    def validate_row_counts(
        self,
        raw_count: int,
        processed_count: int,
        expected_loss_rate: float = 0.05
    ) -> List[ValidationIssue]:
        """
        Validate row count consistency between raw and processed data.

        Args:
            raw_count: Number of raw records
            processed_count: Number of processed records
            expected_loss_rate: Expected maximum data loss rate

        Returns:
            List of validation issues
        """
        issues = []

        if raw_count == 0:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="EMPTY_DATASET",
                message="No raw records found",
                context={"raw_count": raw_count}
            ))
            return issues

        loss_rate = (raw_count - processed_count) / raw_count

        if loss_rate > expected_loss_rate:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="HIGH_DATA_LOSS",
                message=f"Data loss rate {loss_rate:.2%} exceeds threshold {expected_loss_rate:.2%}",
                context={
                    "raw_count": raw_count,
                    "processed_count": processed_count,
                    "loss_rate": loss_rate,
                    "threshold": expected_loss_rate
                }
            ))

        elif loss_rate > 0.01:  # 1% warning threshold
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="MODERATE_DATA_LOSS",
                message=f"Data loss rate {loss_rate:.2%} above normal",
                context={
                    "raw_count": raw_count,
                    "processed_count": processed_count,
                    "loss_rate": loss_rate
                }
            ))

        return issues

    def validate_cost_reconciliation(
        self,
        calculated_costs: List[Dict[str, Any]],
        expected_range: Tuple[float, float] = None
    ) -> List[ValidationIssue]:
        """
        Validate cost calculations against expected ranges.

        Args:
            calculated_costs: List of cost records
            expected_range: Expected (min, max) cost range per user per month

        Returns:
            List of validation issues
        """
        issues = []

        if not calculated_costs:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="NO_COST_DATA",
                message="No cost data available for validation"
            ))
            return issues

        total_cost = sum(record.get('cost_usd', 0) for record in calculated_costs)

        # Negative costs check
        negative_costs = [r for r in calculated_costs if r.get('cost_usd', 0) < 0]
        if negative_costs:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="NEGATIVE_COSTS",
                message=f"Found {len(negative_costs)} records with negative costs",
                context={"negative_records": len(negative_costs)}
            ))

        # Zero costs check (might indicate missing data)
        zero_costs = [r for r in calculated_costs if r.get('cost_usd', 0) == 0]
        if len(zero_costs) > len(calculated_costs) * 0.5:  # More than 50% zero costs
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="HIGH_ZERO_COSTS",
                message=f"{len(zero_costs)} records have zero costs (potential missing data)",
                context={"zero_cost_records": len(zero_costs)}
            ))

        # Expected range validation
        if expected_range:
            min_expected, max_expected = expected_range
            if total_cost < min_expected:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="COST_BELOW_EXPECTED",
                    message=f"Total cost ${total_cost:.2f} below expected minimum ${min_expected:.2f}",
                    context={"total_cost": total_cost, "expected_min": min_expected}
                ))
            elif total_cost > max_expected:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="COST_ABOVE_EXPECTED",
                    message=f"Total cost ${total_cost:.2f} above expected maximum ${max_expected:.2f}",
                    context={"total_cost": total_cost, "expected_max": max_expected}
                ))

        return issues

    def validate_schema_drift(
        self,
        current_schema: List[Dict[str, str]],
        expected_schema: List[Dict[str, str]]
    ) -> List[ValidationIssue]:
        """
        Detect schema changes that might indicate data quality issues.

        Args:
            current_schema: Current table schema
            expected_schema: Expected table schema

        Returns:
            List of validation issues
        """
        issues = []

        current_fields = {field['name']: field['type'] for field in current_schema}
        expected_fields = {field['name']: field['type'] for field in expected_schema}

        # Missing fields
        missing_fields = set(expected_fields.keys()) - set(current_fields.keys())
        if missing_fields:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MISSING_FIELDS",
                message=f"Missing required fields: {', '.join(missing_fields)}",
                context={"missing_fields": list(missing_fields)}
            ))

        # Extra fields
        extra_fields = set(current_fields.keys()) - set(expected_fields.keys())
        if extra_fields:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="EXTRA_FIELDS",
                message=f"Unexpected fields found: {', '.join(extra_fields)}",
                context={"extra_fields": list(extra_fields)}
            ))

        # Type mismatches
        for field_name in current_fields:
            if field_name in expected_fields:
                if current_fields[field_name] != expected_fields[field_name]:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="TYPE_MISMATCH",
                        message=f"Field {field_name} type mismatch: expected {expected_fields[field_name]}, got {current_fields[field_name]}",
                        field=field_name,
                        context={
                            "expected_type": expected_fields[field_name],
                            "actual_type": current_fields[field_name]
                        }
                    ))

        return issues

    def validate_data_freshness(
        self,
        last_update: datetime,
        max_age_hours: int = 25  # Allow for daily jobs to be slightly late
    ) -> List[ValidationIssue]:
        """
        Validate that data is fresh and up-to-date.

        Args:
            last_update: Timestamp of last data update
            max_age_hours: Maximum allowed age in hours

        Returns:
            List of validation issues
        """
        issues = []

        now = datetime.now()
        age_hours = (now - last_update).total_seconds() / 3600

        if age_hours > max_age_hours:
            level = ValidationLevel.CRITICAL if age_hours > max_age_hours * 2 else ValidationLevel.ERROR
            issues.append(ValidationIssue(
                level=level,
                code="STALE_DATA",
                message=f"Data is {age_hours:.1f} hours old (threshold: {max_age_hours}h)",
                context={
                    "age_hours": age_hours,
                    "threshold_hours": max_age_hours,
                    "last_update": last_update.isoformat()
                }
            ))

        return issues

    def validate_user_attribution(
        self,
        usage_records: List[Dict[str, Any]],
        min_attribution_rate: float = 0.95
    ) -> List[ValidationIssue]:
        """
        Validate that user attribution is working correctly.

        Args:
            usage_records: List of usage records
            min_attribution_rate: Minimum required attribution rate

        Returns:
            List of validation issues
        """
        issues = []

        if not usage_records:
            return issues

        # Count records with proper user attribution
        attributed_records = [
            r for r in usage_records
            if r.get('user_email') and '@' in r.get('user_email', '')
        ]

        attribution_rate = len(attributed_records) / len(usage_records)

        if attribution_rate < min_attribution_rate:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="LOW_USER_ATTRIBUTION",
                message=f"User attribution rate {attribution_rate:.2%} below threshold {min_attribution_rate:.2%}",
                context={
                    "attribution_rate": attribution_rate,
                    "threshold": min_attribution_rate,
                    "total_records": len(usage_records),
                    "attributed_records": len(attributed_records)
                }
            ))

        # Check for missing mapping alerts
        unmapped_api_keys = [
            r for r in usage_records
            if r.get('api_key_id') and not r.get('user_email')
        ]

        if unmapped_api_keys:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="UNMAPPED_API_KEYS",
                message=f"Found {len(unmapped_api_keys)} records with unmapped API keys",
                context={"unmapped_count": len(unmapped_api_keys)}
            ))

        return issues

    def generate_quality_report(
        self,
        dataset: str,
        validation_results: List[List[ValidationIssue]]
    ) -> DataQualityReport:
        """
        Generate comprehensive data quality report.

        Args:
            dataset: Name of the dataset being validated
            validation_results: List of validation issue lists from different checks

        Returns:
            DataQualityReport with consolidated results
        """
        # Flatten all issues
        all_issues = [issue for issues_list in validation_results for issue in issues_list]

        # Count issues by level
        error_count = len([i for i in all_issues if i.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL]])
        warning_count = len([i for i in all_issues if i.level == ValidationLevel.WARNING])

        # Calculate metrics
        metrics = {
            "total_issues": len(all_issues),
            "error_count": error_count,
            "warning_count": warning_count,
            "quality_score": max(0, 100 - (error_count * 10) - (warning_count * 2))  # Simple scoring
        }

        # Determine overall pass/fail status
        passed = error_count == 0

        report = DataQualityReport(
            dataset=dataset,
            evaluation_date=datetime.now(),
            total_records=0,  # Will be set by caller
            valid_records=0,  # Will be set by caller
            issues=all_issues,
            metrics=metrics,
            passed=passed
        )

        self.logger.info(
            f"Data quality report for {dataset}: "
            f"Score {metrics['quality_score']:.1f}/100, "
            f"{error_count} errors, {warning_count} warnings"
        )

        return report

    def validate_anomaly_detection(
        self,
        current_metrics: Dict[str, float],
        historical_metrics: List[Dict[str, float]],
        threshold_multiplier: float = 3.0
    ) -> List[ValidationIssue]:
        """
        Detect anomalies in current metrics compared to historical data.

        Args:
            current_metrics: Current period metrics
            historical_metrics: Historical metrics for comparison
            threshold_multiplier: Standard deviation multiplier for anomaly detection

        Returns:
            List of validation issues for detected anomalies
        """
        issues = []

        if len(historical_metrics) < 3:  # Need minimum history for meaningful comparison
            return issues

        for metric_name, current_value in current_metrics.items():
            # Calculate historical statistics
            historical_values = [h.get(metric_name, 0) for h in historical_metrics if metric_name in h]

            if not historical_values:
                continue

            mean_value = sum(historical_values) / len(historical_values)
            variance = sum((x - mean_value) ** 2 for x in historical_values) / len(historical_values)
            std_dev = variance ** 0.5

            # Check for anomalies
            if std_dev > 0:  # Avoid division by zero
                z_score = abs(current_value - mean_value) / std_dev

                if z_score > threshold_multiplier:
                    level = ValidationLevel.CRITICAL if z_score > threshold_multiplier * 2 else ValidationLevel.WARNING
                    issues.append(ValidationIssue(
                        level=level,
                        code="METRIC_ANOMALY",
                        message=f"Metric {metric_name} anomaly detected: {current_value:.2f} (historical mean: {mean_value:.2f})",
                        field=metric_name,
                        value=current_value,
                        context={
                            "z_score": z_score,
                            "threshold": threshold_multiplier,
                            "historical_mean": mean_value,
                            "historical_std": std_dev
                        }
                    ))

        return issues