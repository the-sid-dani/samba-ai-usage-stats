"""Data transformation for Anthropic API responses."""

from datetime import datetime, date
from typing import List, Optional
import uuid

from ..ingestion.anthropic_client import AnthropicUsageData, AnthropicCostData
from ..shared.logging_setup import get_logger
from .transformer import UsageFactRecord, ValidationResult, DataValidator


class AnthropicDataTransformer:
    """Transforms Anthropic API data into normalized fact records."""

    def __init__(self):
        self.logger = get_logger("anthropic_transformer")
        self.validator = DataValidator()

    def validate_anthropic_usage_data(self, data: AnthropicUsageData) -> ValidationResult:
        """
        Validate Anthropic usage data.

        Args:
            data: AnthropicUsageData object to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []

        # Required field validation
        if not data.api_key_id or not data.api_key_id.strip():
            errors.append("API key ID is required and cannot be empty")

        if not data.model or not data.model.strip():
            errors.append("Model is required and cannot be empty")

        if not isinstance(data.usage_date, date):
            errors.append("Usage date must be a date object")

        # Numeric field validation
        numeric_fields = [
            ("uncached_input_tokens", data.uncached_input_tokens),
            ("cached_input_tokens", data.cached_input_tokens),
            ("cache_read_input_tokens", data.cache_read_input_tokens),
            ("output_tokens", data.output_tokens)
        ]

        for field_name, value in numeric_fields:
            if value < 0:
                errors.append(f"{field_name} cannot be negative: {value}")

        # Business logic validation
        total_input = data.uncached_input_tokens + data.cached_input_tokens
        if total_input == 0 and data.output_tokens == 0:
            warnings.append(f"Zero token usage for API key {data.api_key_id} on {data.usage_date}")

        # Date validation
        if data.usage_date and data.usage_date > date.today():
            warnings.append(f"Future date detected: {data.usage_date}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def transform_anthropic_usage_data(
        self,
        anthropic_data: List[AnthropicUsageData],
        ingest_date: date = None
    ) -> List[UsageFactRecord]:
        """
        Transform Anthropic usage data into normalized fact records.

        Args:
            anthropic_data: List of AnthropicUsageData objects
            ingest_date: Date of data ingestion (defaults to today)

        Returns:
            List of UsageFactRecord objects
        """
        if ingest_date is None:
            ingest_date = date.today()

        request_id = str(uuid.uuid4())
        transformed_records = []
        validation_errors = []

        self.logger.info(f"Transforming {len(anthropic_data)} Anthropic usage records")

        for data in anthropic_data:
            # Validate input data
            validation = self.validate_anthropic_usage_data(data)

            if not validation.is_valid:
                self.logger.error(f"Validation failed for {data.api_key_id}: {validation.errors}")
                validation_errors.extend(validation.errors)
                continue

            # Log warnings
            for warning in validation.warnings:
                self.logger.warning(warning)

            # Transform to normalized record
            try:
                # Determine platform based on usage context
                platform = self._determine_platform(data.model)

                fact_record = UsageFactRecord(
                    usage_date=data.usage_date,
                    platform=platform,
                    user_email="",  # Will be resolved in attribution step via API key mapping
                    user_id=None,
                    api_key_id=data.api_key_id,
                    model=data.model,
                    workspace_id=data.workspace_id,

                    # Token metrics (Anthropic provides detailed token counts)
                    input_tokens=data.uncached_input_tokens + data.cached_input_tokens,
                    output_tokens=data.output_tokens,
                    cached_input_tokens=data.cached_input_tokens,
                    cache_read_tokens=data.cache_read_input_tokens,

                    # Platform-specific metrics (not applicable to Anthropic)
                    sessions=1,  # Assume 1 session per usage record
                    lines_of_code_added=0,
                    lines_of_code_accepted=0,
                    acceptance_rate=None,
                    total_accepts=0,

                    # Request tracking (inferred from token usage)
                    subscription_requests=1 if data.uncached_input_tokens + data.output_tokens > 0 else 0,
                    usage_based_requests=0,  # Determined by cost analysis

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
                self.logger.error(f"Transformation error for {data.api_key_id}: {e}")
                validation_errors.append(f"Transformation error: {str(e)}")

        self.logger.info(
            f"Successfully transformed {len(transformed_records)} Anthropic usage records, "
            f"{len(validation_errors)} errors"
        )

        return transformed_records

    def _determine_platform(self, model: str) -> str:
        """
        Determine platform based on model usage context.

        Args:
            model: Model name from API

        Returns:
            Platform identifier
        """
        # This is a simplified mapping - in practice, you might need additional context
        # to determine if usage was from Claude.ai, Claude Code, or direct API

        # For now, assume all is anthropic_api - this could be enhanced with additional
        # metadata from the API or usage patterns analysis
        return "anthropic_api"

    def create_cost_fact_records(
        self,
        cost_data: List[AnthropicCostData],
        ingest_date: date = None
    ) -> List[dict]:
        """
        Transform Anthropic cost data into cost fact records for BigQuery.

        Args:
            cost_data: List of AnthropicCostData objects
            ingest_date: Date of data ingestion (defaults to today)

        Returns:
            List of cost fact records as dictionaries
        """
        if ingest_date is None:
            ingest_date = date.today()

        request_id = str(uuid.uuid4())
        cost_records = []

        self.logger.info(f"Transforming {len(cost_data)} Anthropic cost records")

        for data in cost_data:
            # Basic validation
            if data.cost_usd <= 0:
                continue  # Skip zero or negative costs

            cost_record = {
                "cost_date": data.cost_date.isoformat(),
                "platform": self._determine_platform(data.model),
                "user_email": "",  # Will be resolved via API key mapping
                "user_id": None,
                "api_key_id": data.api_key_id,
                "model": data.model,
                "workspace_id": data.workspace_id,
                "cost_usd": data.cost_usd,
                "cost_type": data.cost_type,
                "volume_units": 0,  # Would need to correlate with usage data
                "unit_type": "tokens",
                "ingest_date": ingest_date.isoformat(),
                "request_id": request_id
            }
            cost_records.append(cost_record)

        self.logger.info(f"Successfully transformed {len(cost_records)} cost records")
        return cost_records