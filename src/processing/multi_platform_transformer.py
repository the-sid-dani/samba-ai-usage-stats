"""Multi-platform data transformation engine for unified analytics."""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
import uuid

from ..ingestion.cursor_client import CursorUsageData
from ..ingestion.anthropic_client import AnthropicUsageData, AnthropicCostData
from ..ingestion.sheets_client import APIKeyMapping
from ..shared.logging_setup import get_logger
from .transformer import UsageFactRecord, ValidationResult, DataValidator
from .anthropic_transformer import AnthropicDataTransformer


class MultiPlatformTransformer:
    """Unified transformer for all AI platform data."""

    def __init__(self):
        self.logger = get_logger("multi_platform_transformer")
        self.validator = DataValidator()
        self.anthropic_transformer = AnthropicDataTransformer()

    def transform_all_usage_data(
        self,
        cursor_data: List[CursorUsageData] = None,
        anthropic_data: List[AnthropicUsageData] = None,
        api_key_mappings: List[APIKeyMapping] = None,
        ingest_date: date = None
    ) -> Dict[str, Any]:
        """
        Transform usage data from all platforms into unified format.

        Args:
            cursor_data: List of Cursor usage data
            anthropic_data: List of Anthropic usage data
            api_key_mappings: List of API key to user mappings
            ingest_date: Date of data ingestion

        Returns:
            Dictionary with transformed data and metadata
        """
        if ingest_date is None:
            ingest_date = date.today()

        start_time = datetime.now()
        all_usage_records = []
        transformation_stats = {
            "cursor": {"input": 0, "output": 0, "errors": []},
            "anthropic": {"input": 0, "output": 0, "errors": []},
            "total_input": 0,
            "total_output": 0
        }

        self.logger.info("Starting multi-platform data transformation")

        # Create API key mapping lookup
        api_key_lookup = {}
        if api_key_mappings:
            api_key_lookup = {
                mapping.api_key_name: mapping
                for mapping in api_key_mappings
            }
            self.logger.info(f"Loaded {len(api_key_lookup)} API key mappings")

        # Transform Cursor data
        if cursor_data:
            self.logger.info(f"Transforming {len(cursor_data)} Cursor records")
            transformation_stats["cursor"]["input"] = len(cursor_data)

            try:
                cursor_records = self._transform_cursor_data(cursor_data, ingest_date)
                # Apply user attribution to Cursor data (direct email mapping)
                cursor_records = self._apply_cursor_attribution(cursor_records)
                all_usage_records.extend(cursor_records)
                transformation_stats["cursor"]["output"] = len(cursor_records)
            except Exception as e:
                error_msg = f"Cursor transformation failed: {e}"
                self.logger.error(error_msg)
                transformation_stats["cursor"]["errors"].append(error_msg)

        # Transform Anthropic data
        if anthropic_data:
            self.logger.info(f"Transforming {len(anthropic_data)} Anthropic records")
            transformation_stats["anthropic"]["input"] = len(anthropic_data)

            try:
                # Apply user attribution first, then transform
                anthropic_records = self._transform_anthropic_with_attribution(
                    anthropic_data, api_key_lookup, ingest_date
                )
                all_usage_records.extend(anthropic_records)
                transformation_stats["anthropic"]["output"] = len(anthropic_records)
            except Exception as e:
                error_msg = f"Anthropic transformation failed: {e}"
                self.logger.error(error_msg)
                transformation_stats["anthropic"]["errors"].append(error_msg)

        # Calculate totals
        transformation_stats["total_input"] = (
            transformation_stats["cursor"]["input"] +
            transformation_stats["anthropic"]["input"]
        )
        transformation_stats["total_output"] = len(all_usage_records)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        result = {
            "usage_records": all_usage_records,
            "transformation_stats": transformation_stats,
            "processing_time_seconds": processing_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "ingest_date": ingest_date.isoformat(),
            "success": True
        }

        self.logger.info(
            f"Multi-platform transformation completed: "
            f"{transformation_stats['total_input']} → {transformation_stats['total_output']} records "
            f"in {processing_time:.2f}s"
        )

        return result

    def _transform_cursor_data(
        self,
        cursor_data: List[CursorUsageData],
        ingest_date: date
    ) -> List[UsageFactRecord]:
        """Transform Cursor data using existing transformer logic."""
        from .transformer import CursorDataTransformer

        cursor_transformer = CursorDataTransformer()
        return cursor_transformer.transform_cursor_data(cursor_data, ingest_date)

    def _apply_cursor_attribution(
        self,
        records: List[UsageFactRecord]
    ) -> List[UsageFactRecord]:
        """Apply user attribution for Cursor records (direct email mapping)."""
        # Cursor records already have user_email populated from the API
        # Just normalize the email addresses
        for record in records:
            if record.user_email:
                record.user_email = record.user_email.lower().strip()

        return records

    def _apply_anthropic_attribution(
        self,
        records: List[UsageFactRecord],
        api_key_lookup: Dict[str, APIKeyMapping]
    ) -> List[UsageFactRecord]:
        """Apply user attribution for Anthropic records via API key mapping."""
        attributed_count = 0
        unmapped_keys = set()

        for record in records:
            if record.api_key_id and record.api_key_id in api_key_lookup:
                mapping = api_key_lookup[record.api_key_id]
                record.user_email = mapping.user_email
                record.platform = mapping.platform  # Use platform from mapping
                attributed_count += 1
            else:
                if record.api_key_id:
                    unmapped_keys.add(record.api_key_id)

        if unmapped_keys:
            self.logger.warning(
                f"Found {len(unmapped_keys)} unmapped API keys: {list(unmapped_keys)[:5]}..."
            )

        self.logger.info(
            f"Applied user attribution to {attributed_count}/{len(records)} Anthropic records"
        )

        return records

    def _transform_anthropic_with_attribution(
        self,
        anthropic_data: List[AnthropicUsageData],
        api_key_lookup: Dict[str, APIKeyMapping],
        ingest_date: date
    ) -> List[UsageFactRecord]:
        """Transform Anthropic data with immediate user attribution."""
        from .transformer import UsageFactRecord

        request_id = str(uuid.uuid4())
        transformed_records = []

        for data in anthropic_data:
            # Get user email from API key mapping
            user_email = ""
            platform = "anthropic_api"

            if data.api_key_id and data.api_key_id in api_key_lookup:
                mapping = api_key_lookup[data.api_key_id]
                user_email = mapping.user_email
                # Map generic "anthropic" to specific platform
                if mapping.platform == "anthropic":
                    platform = "anthropic_api"
                else:
                    platform = mapping.platform

            # Skip records without user attribution
            if not user_email:
                self.logger.warning(f"Skipping Anthropic record with unmapped API key: {data.api_key_id}")
                continue

            # Create fact record with attribution
            fact_record = UsageFactRecord(
                usage_date=data.usage_date,
                platform=platform,
                user_email=user_email,
                user_id=None,
                api_key_id=data.api_key_id,
                model=data.model,
                workspace_id=data.workspace_id,
                input_tokens=data.uncached_input_tokens + data.cached_input_tokens,
                output_tokens=data.output_tokens,
                cached_input_tokens=data.cached_input_tokens,
                cache_read_tokens=data.cache_read_input_tokens,
                sessions=1,
                lines_of_code_added=0,
                lines_of_code_accepted=0,
                acceptance_rate=None,
                total_accepts=0,
                subscription_requests=1 if data.uncached_input_tokens + data.output_tokens > 0 else 0,
                usage_based_requests=0,
                ingest_date=ingest_date,
                request_id=request_id
            )

            # Validate the record
            validation = self.validator.validate_usage_fact(fact_record)
            if validation.is_valid:
                transformed_records.append(fact_record)
            else:
                self.logger.error(f"Validation failed for {data.api_key_id}: {validation.errors}")

        return transformed_records

    def create_bigquery_rows(
        self,
        usage_records: List[UsageFactRecord]
    ) -> List[Dict[str, Any]]:
        """Convert usage records to BigQuery row format."""
        from .transformer import CursorDataTransformer

        transformer = CursorDataTransformer()
        return transformer.to_bigquery_rows(usage_records)

    def create_cost_records(
        self,
        anthropic_cost_data: List[AnthropicCostData],
        api_key_mappings: List[APIKeyMapping] = None,
        ingest_date: date = None
    ) -> List[Dict[str, Any]]:
        """
        Transform cost data into BigQuery format with user attribution.

        Args:
            anthropic_cost_data: List of Anthropic cost data
            api_key_mappings: List of API key mappings for attribution
            ingest_date: Date of data ingestion

        Returns:
            List of cost records ready for BigQuery insertion
        """
        if ingest_date is None:
            ingest_date = date.today()

        # Create API key lookup
        api_key_lookup = {}
        if api_key_mappings:
            api_key_lookup = {
                mapping.api_key_name: mapping
                for mapping in api_key_mappings
            }

        # Transform cost data
        cost_records = self.anthropic_transformer.create_cost_fact_records(
            anthropic_cost_data, ingest_date
        )

        # Apply user attribution
        attributed_count = 0
        for record in cost_records:
            api_key_id = record.get("api_key_id")
            if api_key_id and api_key_id in api_key_lookup:
                mapping = api_key_lookup[api_key_id]
                record["user_email"] = mapping.user_email
                record["platform"] = mapping.platform
                attributed_count += 1

        self.logger.info(
            f"Applied user attribution to {attributed_count}/{len(cost_records)} cost records"
        )

        return cost_records

    def validate_multi_platform_data(
        self,
        cursor_data: List[CursorUsageData] = None,
        anthropic_data: List[AnthropicUsageData] = None,
        api_key_mappings: List[APIKeyMapping] = None
    ) -> Dict[str, Any]:
        """
        Validate multi-platform data quality and consistency.

        Args:
            cursor_data: Cursor usage data to validate
            anthropic_data: Anthropic usage data to validate
            api_key_mappings: API key mappings to validate

        Returns:
            Validation report with issues and recommendations
        """
        validation_report = {
            "cursor_validation": {"valid": 0, "invalid": 0, "issues": []},
            "anthropic_validation": {"valid": 0, "invalid": 0, "issues": []},
            "mapping_validation": {"coverage": 0.0, "issues": []},
            "overall_status": "unknown"
        }

        # Validate Cursor data
        if cursor_data:
            for data in cursor_data:
                from .transformer import DataValidator
                validator = DataValidator()
                result = validator.validate_cursor_data(data)
                if result.is_valid:
                    validation_report["cursor_validation"]["valid"] += 1
                else:
                    validation_report["cursor_validation"]["invalid"] += 1
                    validation_report["cursor_validation"]["issues"].extend(result.errors)

        # Validate Anthropic data
        if anthropic_data:
            for data in anthropic_data:
                result = self.anthropic_transformer.validate_anthropic_usage_data(data)
                if result.is_valid:
                    validation_report["anthropic_validation"]["valid"] += 1
                else:
                    validation_report["anthropic_validation"]["invalid"] += 1
                    validation_report["anthropic_validation"]["issues"].extend(result.errors)

        # Validate API key mapping coverage
        if anthropic_data:
            api_keys_in_data = {data.api_key_id for data in anthropic_data if data.api_key_id}
            mapped_keys = {mapping.api_key_name for mapping in api_key_mappings} if api_key_mappings else set()

            if api_keys_in_data:
                coverage = len(api_keys_in_data & mapped_keys) / len(api_keys_in_data)
                validation_report["mapping_validation"]["coverage"] = coverage

                unmapped_keys = api_keys_in_data - mapped_keys
                if unmapped_keys:
                    validation_report["mapping_validation"]["issues"].append(
                        f"Unmapped API keys: {list(unmapped_keys)[:5]}..."
                    )

                if coverage < 0.8:
                    validation_report["mapping_validation"]["issues"].append(
                        f"Low mapping coverage: {coverage:.1%}"
                    )

        # Determine overall status
        total_invalid = (
            validation_report["cursor_validation"]["invalid"] +
            validation_report["anthropic_validation"]["invalid"]
        )
        mapping_coverage = validation_report["mapping_validation"]["coverage"]

        if total_invalid == 0 and mapping_coverage >= 0.95:
            validation_report["overall_status"] = "excellent"
        elif total_invalid == 0 and mapping_coverage >= 0.8:
            validation_report["overall_status"] = "good"
        elif total_invalid < 10 and mapping_coverage >= 0.7:
            validation_report["overall_status"] = "acceptable"
        else:
            validation_report["overall_status"] = "needs_attention"

        return validation_report

    def generate_transformation_summary(
        self,
        transformation_result: Dict[str, Any]
    ) -> str:
        """Generate human-readable transformation summary."""
        stats = transformation_result.get("transformation_stats", {})

        summary = []
        summary.append("Multi-Platform Data Transformation Summary")
        summary.append("=" * 50)
        summary.append(f"Processing Time: {transformation_result.get('processing_time_seconds', 0):.2f}s")
        summary.append(f"Ingest Date: {transformation_result.get('ingest_date')}")
        summary.append("")

        # Platform breakdown
        for platform in ["cursor", "anthropic"]:
            if platform in stats:
                platform_stats = stats[platform]
                summary.append(f"{platform.title()} Platform:")
                summary.append(f"  Input Records: {platform_stats['input']}")
                summary.append(f"  Output Records: {platform_stats['output']}")

                if platform_stats['errors']:
                    summary.append(f"  Errors: {len(platform_stats['errors'])}")
                    for error in platform_stats['errors'][:3]:
                        summary.append(f"    - {error}")
                else:
                    summary.append("  Errors: None")
                summary.append("")

        # Totals
        summary.append("Overall Totals:")
        summary.append(f"  Total Input: {stats.get('total_input', 0)}")
        summary.append(f"  Total Output: {stats.get('total_output', 0)}")

        success_rate = (stats.get('total_output', 0) / stats.get('total_input', 1)) * 100
        summary.append(f"  Success Rate: {success_rate:.1f}%")

        return "\n".join(summary)