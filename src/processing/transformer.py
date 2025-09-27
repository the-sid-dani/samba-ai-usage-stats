"""Data transformation engine for normalizing API responses into BigQuery format."""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid

from ..ingestion.cursor_client import CursorUsageData
from ..shared.logging_setup import get_logger


@dataclass
class UsageFactRecord:
    """Normalized usage fact record for BigQuery."""
    usage_date: date
    platform: str
    user_email: str
    user_id: Optional[str]
    api_key_id: Optional[str]
    model: Optional[str]
    workspace_id: Optional[str]

    # Normalized usage metrics
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    cache_read_tokens: int

    # Platform-specific metrics
    sessions: int
    lines_of_code_added: int
    lines_of_code_accepted: int
    acceptance_rate: Optional[float]
    total_accepts: int

    # Request tracking
    subscription_requests: int
    usage_based_requests: int

    # Metadata
    ingest_date: date
    request_id: str


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class DataValidator:
    """Validates data quality and consistency."""

    def __init__(self):
        self.logger = get_logger("data_validator")

    def validate_cursor_data(self, data: CursorUsageData) -> ValidationResult:
        """
        Validate Cursor usage data.

        Args:
            data: CursorUsageData object to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []

        # Required field validation
        if not data.email or not data.email.strip():
            errors.append("Email is required and cannot be empty")

        if not isinstance(data.date, datetime):
            errors.append("Date must be a datetime object")

        # Email format validation (basic)
        if data.email and "@" not in data.email:
            errors.append(f"Invalid email format: {data.email}")

        # Numeric field validation
        numeric_fields = [
            ("total_lines_added", data.total_lines_added),
            ("accepted_lines_added", data.accepted_lines_added),
            ("total_accepts", data.total_accepts),
            ("subscription_included_reqs", data.subscription_included_reqs),
            ("usage_based_reqs", data.usage_based_reqs)
        ]

        for field_name, value in numeric_fields:
            if value < 0:
                errors.append(f"{field_name} cannot be negative: {value}")

        # Business logic validation
        if data.accepted_lines_added > data.total_lines_added:
            warnings.append(
                f"Accepted lines ({data.accepted_lines_added}) > "
                f"total lines ({data.total_lines_added}) for {data.email}"
            )

        # Date validation
        if data.date and data.date > datetime.now():
            warnings.append(f"Future date detected: {data.date}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_usage_fact(self, record: UsageFactRecord) -> ValidationResult:
        """
        Validate normalized usage fact record.

        Args:
            record: UsageFactRecord to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []

        # Required fields
        if not record.user_email:
            errors.append("user_email is required")

        if not record.platform:
            errors.append("platform is required")

        if not isinstance(record.usage_date, date):
            errors.append("usage_date must be a date object")

        # Platform validation
        valid_platforms = ["cursor", "anthropic_api", "anthropic_code", "anthropic_web"]
        if record.platform not in valid_platforms:
            errors.append(f"Invalid platform: {record.platform}")

        # Numeric validation
        numeric_fields = [
            "input_tokens", "output_tokens", "cached_input_tokens", "cache_read_tokens",
            "sessions", "lines_of_code_added", "lines_of_code_accepted", "total_accepts",
            "subscription_requests", "usage_based_requests"
        ]

        for field_name in numeric_fields:
            value = getattr(record, field_name)
            if value < 0:
                errors.append(f"{field_name} cannot be negative: {value}")

        # Acceptance rate validation
        if record.acceptance_rate is not None:
            if not (0.0 <= record.acceptance_rate <= 1.0):
                errors.append(f"acceptance_rate must be between 0.0 and 1.0: {record.acceptance_rate}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class CursorDataTransformer:
    """Transforms Cursor API data into normalized fact records."""

    def __init__(self):
        self.logger = get_logger("cursor_transformer")
        self.validator = DataValidator()

    def calculate_acceptance_rate(self, accepted: int, total: int) -> Optional[float]:
        """
        Calculate acceptance rate with safe division.

        Args:
            accepted: Number of accepted lines
            total: Total number of lines

        Returns:
            Acceptance rate as float or None if total is 0
        """
        if total == 0:
            return None
        return round(accepted / total, 4)

    def transform_cursor_data(
        self,
        cursor_data: List[CursorUsageData],
        ingest_date: date = None
    ) -> List[UsageFactRecord]:
        """
        Transform Cursor usage data into normalized fact records.

        Args:
            cursor_data: List of CursorUsageData objects
            ingest_date: Date of data ingestion (defaults to today)

        Returns:
            List of UsageFactRecord objects
        """
        if ingest_date is None:
            ingest_date = date.today()

        request_id = str(uuid.uuid4())
        transformed_records = []
        validation_errors = []

        self.logger.info(f"Transforming {len(cursor_data)} Cursor records")

        for data in cursor_data:
            # Validate input data
            validation = self.validator.validate_cursor_data(data)

            if not validation.is_valid:
                self.logger.error(f"Validation failed for {data.email}: {validation.errors}")
                validation_errors.extend(validation.errors)
                continue

            # Log warnings
            for warning in validation.warnings:
                self.logger.warning(warning)

            # Transform to normalized record
            try:
                fact_record = UsageFactRecord(
                    usage_date=data.date.date() if isinstance(data.date, datetime) else data.date,
                    platform="cursor",
                    user_email=data.email.strip().lower(),
                    user_id=None,  # Will be resolved in attribution step
                    api_key_id=None,  # Cursor uses direct email attribution
                    model=None,  # Cursor doesn't specify model
                    workspace_id=None,  # Cursor doesn't provide workspace ID

                    # Token metrics (Cursor doesn't provide token counts)
                    input_tokens=0,
                    output_tokens=0,
                    cached_input_tokens=0,
                    cache_read_tokens=0,

                    # Cursor-specific metrics
                    sessions=1,  # Assume 1 session per daily record
                    lines_of_code_added=data.total_lines_added,
                    lines_of_code_accepted=data.accepted_lines_added,
                    acceptance_rate=self.calculate_acceptance_rate(
                        data.accepted_lines_added,
                        data.total_lines_added
                    ),
                    total_accepts=data.total_accepts,

                    # Request tracking
                    subscription_requests=data.subscription_included_reqs,
                    usage_based_requests=data.usage_based_reqs,

                    # Metadata
                    ingest_date=ingest_date,
                    request_id=request_id
                )

                # Validate transformed record
                fact_validation = self.validator.validate_usage_fact(fact_record)
                if fact_validation.is_valid:
                    transformed_records.append(fact_record)
                else:
                    self.logger.error(f"Fact validation failed: {fact_validation.errors}")
                    validation_errors.extend(fact_validation.errors)

            except Exception as e:
                self.logger.error(f"Transformation error for {data.email}: {e}")
                validation_errors.append(f"Transformation error: {str(e)}")

        self.logger.info(
            f"Successfully transformed {len(transformed_records)} records, "
            f"{len(validation_errors)} errors"
        )

        if validation_errors:
            self.logger.warning(f"Total validation errors: {len(validation_errors)}")

        return transformed_records

    def to_bigquery_rows(self, fact_records: List[UsageFactRecord]) -> List[Dict[str, Any]]:
        """
        Convert fact records to BigQuery row format.

        Args:
            fact_records: List of UsageFactRecord objects

        Returns:
            List of dictionaries ready for BigQuery insertion
        """
        rows = []

        for record in fact_records:
            row = {
                "usage_date": record.usage_date.isoformat(),
                "platform": record.platform,
                "user_email": record.user_email,
                "user_id": record.user_id,
                "api_key_id": record.api_key_id,
                "model": record.model,
                "workspace_id": record.workspace_id,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "cached_input_tokens": record.cached_input_tokens,
                "cache_read_tokens": record.cache_read_tokens,
                "sessions": record.sessions,
                "lines_of_code_added": record.lines_of_code_added,
                "lines_of_code_accepted": record.lines_of_code_accepted,
                "acceptance_rate": record.acceptance_rate,
                "total_accepts": record.total_accepts,
                "subscription_requests": record.subscription_requests,
                "usage_based_requests": record.usage_based_requests,
                "ingest_date": record.ingest_date.isoformat(),
                "request_id": record.request_id
            }
            rows.append(row)

        self.logger.info(f"Converted {len(rows)} records to BigQuery format")
        return rows


class DataTransformationPipeline:
    """Orchestrates the complete data transformation pipeline."""

    def __init__(self):
        self.logger = get_logger("transformation_pipeline")
        self.cursor_transformer = CursorDataTransformer()

    def process_cursor_data(
        self,
        cursor_data: List[CursorUsageData]
    ) -> Dict[str, Any]:
        """
        Process Cursor data through the complete transformation pipeline.

        Args:
            cursor_data: Raw Cursor usage data

        Returns:
            Dictionary with transformed data and metadata
        """
        start_time = datetime.now()

        self.logger.info(f"Starting transformation pipeline for {len(cursor_data)} Cursor records")

        # Transform data
        fact_records = self.cursor_transformer.transform_cursor_data(cursor_data)

        # Convert to BigQuery format
        bigquery_rows = self.cursor_transformer.to_bigquery_rows(fact_records)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        result = {
            "platform": "cursor",
            "input_record_count": len(cursor_data),
            "output_record_count": len(fact_records),
            "bigquery_rows": bigquery_rows,
            "processing_time_seconds": processing_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "success": True
        }

        self.logger.info(
            f"Transformation pipeline completed: {len(cursor_data)} → {len(fact_records)} records "
            f"in {processing_time:.2f}s"
        )

        return result