"""Daily job orchestrator for multi-platform usage data pipeline."""

import time
import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from ..ingestion.cursor_client import CursorClient, CursorAPIError
from ..ingestion.anthropic_client import AnthropicClient, AnthropicAPIError
from ..ingestion.sheets_client import GoogleSheetsClient
from ..processing.multi_platform_transformer import MultiPlatformTransformer
from ..processing.attribution import UserAttributionEngine
from ..storage.bigquery_client import BigQuerySchemaManager
from ..shared.config import config
from ..shared.logging_setup import get_logger
from ..shared.monitoring import SystemMonitor
from ..shared.cloud_monitoring import get_cloud_monitoring
from ..shared.alert_manager import alert_manager


class ExecutionMode(Enum):
    """Pipeline execution modes."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    DRY_RUN = "dry_run"


@dataclass
class PipelineError:
    """Structured pipeline error information."""
    error_code: str
    message: str
    component: str
    exception: Optional[Exception] = None
    recoverable: bool = True


@dataclass
class PipelineMetrics:
    """Pipeline execution metrics."""
    request_id: str
    execution_mode: ExecutionMode
    start_time: float
    end_time: Optional[float] = None

    # Data ingestion metrics
    cursor_records: int = 0
    anthropic_usage_records: int = 0
    anthropic_cost_records: int = 0
    sheets_mappings: int = 0

    # Processing metrics
    transformation_success_rate: float = 0.0
    attribution_rate: float = 0.0

    # Storage metrics
    usage_records_inserted: int = 0
    cost_records_inserted: int = 0

    # Error tracking
    errors: List[PipelineError] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def total_processing_time(self) -> float:
        """Calculate total processing time in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def has_critical_errors(self) -> bool:
        """Check if pipeline has non-recoverable errors."""
        return any(not error.recoverable for error in self.errors)


class DailyJobOrchestrator:
    """Main orchestrator for daily data pipeline execution."""

    def __init__(self, execution_mode: ExecutionMode = ExecutionMode.PRODUCTION):
        self.execution_mode = execution_mode
        self.request_id = str(uuid.uuid4())
        self.logger = get_logger("daily_job_orchestrator")

        # Initialize components
        self.cursor_client = None
        self.anthropic_client = None
        self.sheets_client = None
        self.transformer = None
        self.attribution_engine = None
        self.storage_client = None
        self.monitor = SystemMonitor()

        # Configuration based on execution mode
        self.batch_size = 1000 if execution_mode == ExecutionMode.PRODUCTION else 100
        self.max_retries = 3
        self.backoff_base = 2

        self.logger.info(f"DailyJobOrchestrator initialized in {execution_mode.value} mode")

    def _initialize_clients(self) -> None:
        """Initialize all API clients and processing components."""
        try:
            self.logger.info("Initializing pipeline components")

            # Initialize API clients
            self.cursor_client = CursorClient()
            self.anthropic_client = AnthropicClient()
            self.sheets_client = GoogleSheetsClient()

            # Initialize processing components
            self.transformer = MultiPlatformTransformer()
            self.attribution_engine = UserAttributionEngine(self.sheets_client)

            # Initialize storage client
            if self.execution_mode != ExecutionMode.DRY_RUN:
                self.storage_client = BigQuerySchemaManager()

            self.logger.info("All pipeline components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline components: {e}")
            raise

    def _fetch_cursor_data(self, start_date: date, end_date: date, metrics: PipelineMetrics) -> List:
        """Fetch data from Cursor API with error handling."""
        try:
            self.logger.info(f"Fetching Cursor data from {start_date} to {end_date}")
            cursor_data = self.cursor_client.get_daily_usage_data(start_date, end_date)
            metrics.cursor_records = len(cursor_data)
            self.logger.info(f"Successfully fetched {len(cursor_data)} Cursor records")
            return cursor_data

        except CursorAPIError as e:
            error = PipelineError(
                error_code="CURSOR_API_ERROR",
                message=f"Failed to fetch Cursor data: {e}",
                component="cursor_client",
                exception=e,
                recoverable=True
            )
            metrics.errors.append(error)
            self.logger.error(f"Cursor API error: {e}")
            return []

        except Exception as e:
            error = PipelineError(
                error_code="CURSOR_UNEXPECTED_ERROR",
                message=f"Unexpected error fetching Cursor data: {e}",
                component="cursor_client",
                exception=e,
                recoverable=False
            )
            metrics.errors.append(error)
            self.logger.error(f"Unexpected Cursor error: {e}")
            return []

    def _fetch_anthropic_data(self, start_date: date, end_date: date, metrics: PipelineMetrics) -> Tuple[List, List]:
        """Fetch usage and cost data from Anthropic API with error handling."""
        usage_data = []
        cost_data = []

        try:
            self.logger.info(f"Fetching Anthropic usage data from {start_date} to {end_date}")
            usage_data = self.anthropic_client.get_usage_data(start_date, end_date)
            metrics.anthropic_usage_records = len(usage_data)
            self.logger.info(f"Successfully fetched {len(usage_data)} Anthropic usage records")

        except AnthropicAPIError as e:
            error = PipelineError(
                error_code="ANTHROPIC_USAGE_API_ERROR",
                message=f"Failed to fetch Anthropic usage data: {e}",
                component="anthropic_client",
                exception=e,
                recoverable=True
            )
            metrics.errors.append(error)
            self.logger.error(f"Anthropic usage API error: {e}")

        try:
            self.logger.info(f"Fetching Anthropic cost data from {start_date} to {end_date}")
            cost_data = self.anthropic_client.get_cost_data(start_date, end_date)
            metrics.anthropic_cost_records = len(cost_data)
            self.logger.info(f"Successfully fetched {len(cost_data)} Anthropic cost records")

        except AnthropicAPIError as e:
            error = PipelineError(
                error_code="ANTHROPIC_COST_API_ERROR",
                message=f"Failed to fetch Anthropic cost data: {e}",
                component="anthropic_client",
                exception=e,
                recoverable=True
            )
            metrics.errors.append(error)
            self.logger.error(f"Anthropic cost API error: {e}")

        except Exception as e:
            error = PipelineError(
                error_code="ANTHROPIC_UNEXPECTED_ERROR",
                message=f"Unexpected error fetching Anthropic data: {e}",
                component="anthropic_client",
                exception=e,
                recoverable=False
            )
            metrics.errors.append(error)
            self.logger.error(f"Unexpected Anthropic error: {e}")

        return usage_data, cost_data

    def _fetch_sheets_mappings(self, metrics: PipelineMetrics) -> List:
        """Fetch API key mappings from Google Sheets with error handling."""
        try:
            self.logger.info("Fetching API key mappings from Google Sheets")
            mappings = self.sheets_client.get_api_key_mappings()
            metrics.sheets_mappings = len(mappings)
            self.logger.info(f"Successfully fetched {len(mappings)} API key mappings")
            return mappings

        except Exception as e:
            error = PipelineError(
                error_code="SHEETS_ERROR",
                message=f"Failed to fetch Google Sheets mappings: {e}",
                component="sheets_client",
                exception=e,
                recoverable=False  # Mappings are critical for attribution
            )
            metrics.errors.append(error)
            self.logger.error(f"Google Sheets error: {e}")
            return []

    def _process_and_transform_data(self, cursor_data: List, anthropic_usage_data: List,
                                  anthropic_cost_data: List, api_mappings: List,
                                  metrics: PipelineMetrics) -> Tuple[List, List]:
        """Transform and attribute all data with error handling."""
        try:
            self.logger.info("Starting data transformation and attribution")

            # Transform usage data
            usage_result = self.transformer.transform_all_usage_data(
                cursor_data=cursor_data,
                anthropic_data=anthropic_usage_data,
                api_key_mappings=api_mappings
            )

            if not usage_result["success"]:
                error = PipelineError(
                    error_code="TRANSFORMATION_ERROR",
                    message="Usage data transformation failed",
                    component="transformer",
                    recoverable=True
                )
                metrics.errors.append(error)
                self.logger.error("Usage data transformation failed")

            # Transform cost data
            cost_records = self.transformer.create_cost_records(
                anthropic_cost_data,
                api_mappings
            )

            # Calculate metrics
            total_input = usage_result["transformation_stats"]["total_input"]
            total_output = len(usage_result["usage_records"])
            metrics.transformation_success_rate = total_output / total_input if total_input > 0 else 0.0

            # Calculate attribution rate (records with valid user attribution)
            attributed_records = sum(1 for record in usage_result["usage_records"] if record.user_email)
            metrics.attribution_rate = attributed_records / total_output if total_output > 0 else 0.0

            self.logger.info(
                f"Transformation complete: {total_output} usage records, {len(cost_records)} cost records. "
                f"Success rate: {metrics.transformation_success_rate:.2%}, "
                f"Attribution rate: {metrics.attribution_rate:.2%}"
            )

            return usage_result["usage_records"], cost_records

        except Exception as e:
            error = PipelineError(
                error_code="TRANSFORMATION_UNEXPECTED_ERROR",
                message=f"Unexpected error during transformation: {e}",
                component="transformer",
                exception=e,
                recoverable=False
            )
            metrics.errors.append(error)
            self.logger.error(f"Unexpected transformation error: {e}")
            return [], []

    def _insert_data_to_bigquery(self, usage_records: List, cost_records: List,
                                metrics: PipelineMetrics) -> None:
        """Insert data to BigQuery with batch optimization and error handling."""
        if self.execution_mode == ExecutionMode.DRY_RUN:
            self.logger.info(f"DRY RUN: Would insert {len(usage_records)} usage records and {len(cost_records)} cost records")
            metrics.usage_records_inserted = len(usage_records)
            metrics.cost_records_inserted = len(cost_records)
            return

        try:
            # Insert usage data in batches
            if usage_records:
                self.logger.info(f"Inserting {len(usage_records)} usage records to BigQuery")
                self.storage_client.insert_usage_data(usage_records, batch_size=self.batch_size)
                metrics.usage_records_inserted = len(usage_records)
                self.logger.info("Usage data insertion completed successfully")

            # Insert cost data in batches
            if cost_records:
                self.logger.info(f"Inserting {len(cost_records)} cost records to BigQuery")
                self.storage_client.insert_cost_data(cost_records, batch_size=self.batch_size)
                metrics.cost_records_inserted = len(cost_records)
                self.logger.info("Cost data insertion completed successfully")

        except Exception as e:
            error = PipelineError(
                error_code="BIGQUERY_INSERT_ERROR",
                message=f"Failed to insert data to BigQuery: {e}",
                component="storage_client",
                exception=e,
                recoverable=False
            )
            metrics.errors.append(error)
            self.logger.error(f"BigQuery insertion error: {e}")

    def _generate_metrics_summary(self, metrics: PipelineMetrics) -> Dict[str, Any]:
        """Generate comprehensive metrics summary for monitoring."""
        summary = {
            "request_id": metrics.request_id,
            "execution_mode": metrics.execution_mode.value,
            "processing_time_seconds": metrics.total_processing_time,
            "data_ingestion": {
                "cursor_records": metrics.cursor_records,
                "anthropic_usage_records": metrics.anthropic_usage_records,
                "anthropic_cost_records": metrics.anthropic_cost_records,
                "sheets_mappings": metrics.sheets_mappings
            },
            "processing_metrics": {
                "transformation_success_rate": metrics.transformation_success_rate,
                "attribution_rate": metrics.attribution_rate
            },
            "storage_metrics": {
                "usage_records_inserted": metrics.usage_records_inserted,
                "cost_records_inserted": metrics.cost_records_inserted
            },
            "error_summary": {
                "total_errors": len(metrics.errors),
                "critical_errors": sum(1 for e in metrics.errors if not e.recoverable),
                "error_components": list(set(e.component for e in metrics.errors))
            }
        }

        return summary

    def _record_cloud_monitoring_metrics(self, summary: Dict[str, Any], success: bool) -> None:
        """Record metrics to Google Cloud Monitoring."""
        try:
            # Record pipeline health (success rate as 100% or 0%)
            success_rate = 100.0 if success else 0.0
            monitoring_client = get_cloud_monitoring()
            monitoring_client.record_pipeline_health(success_rate, "daily_job")

            # Record processing time
            processing_time_ms = summary["processing_time_seconds"] * 1000
            monitoring_client.record_api_response_time("pipeline", processing_time_ms, "orchestrator")

            # Record records processed
            total_records = (
                summary["data_ingestion"]["cursor_records"] +
                summary["data_ingestion"]["anthropic_usage_records"] +
                summary["data_ingestion"]["anthropic_cost_records"]
            )
            monitoring_client.record_records_processed("all_platforms", total_records, "ingestion")

            # Record error rate
            total_operations = max(1, total_records)  # Avoid division by zero
            error_rate = (summary["error_summary"]["total_errors"] / total_operations) * 100
            monitoring_client.record_error_rate("pipeline", min(error_rate, 100.0), "general")

            # Record attribution completeness
            attribution_rate = summary["processing_metrics"]["attribution_rate"] * 100
            monitoring_client.record_attribution_completeness(attribution_rate, "all_platforms")

            self.logger.debug("Successfully recorded Cloud Monitoring metrics", extra={
                "success_rate": success_rate,
                "processing_time_ms": processing_time_ms,
                "total_records": total_records,
                "error_rate": error_rate,
                "attribution_rate": attribution_rate
            })

        except Exception as e:
            self.logger.error("Failed to record Cloud Monitoring metrics", extra={
                "error": str(e),
                "summary_keys": list(summary.keys()) if summary else None
            })
            raise

    def run_daily_job(self, target_date: Optional[date] = None,
                     date_range_days: int = 1) -> Dict[str, Any]:
        """
        Execute the complete daily data pipeline.

        Args:
            target_date: Specific date to process (defaults to yesterday)
            date_range_days: Number of days to process (default: 1)

        Returns:
            Dictionary with execution results and metrics
        """
        # Initialize metrics
        metrics = PipelineMetrics(
            request_id=self.request_id,
            execution_mode=self.execution_mode,
            start_time=time.time()
        )

        try:
            self.logger.info(f"Starting daily job execution (request_id: {self.request_id})")

            # Determine date range
            if target_date is None:
                end_date = date.today() - timedelta(days=1)  # Yesterday
            else:
                end_date = target_date

            start_date = end_date - timedelta(days=date_range_days - 1)

            if self.execution_mode == ExecutionMode.DEVELOPMENT:
                # Limit date range for development
                date_range_days = min(date_range_days, 3)
                start_date = end_date - timedelta(days=date_range_days - 1)

            self.logger.info(f"Processing date range: {start_date} to {end_date}")

            # Initialize all components
            self._initialize_clients()

            # Data ingestion phase
            self.logger.info("=== DATA INGESTION PHASE ===")
            cursor_data = self._fetch_cursor_data(start_date, end_date, metrics)
            anthropic_usage_data, anthropic_cost_data = self._fetch_anthropic_data(start_date, end_date, metrics)
            api_mappings = self._fetch_sheets_mappings(metrics)

            # Check for critical errors in ingestion
            if metrics.has_critical_errors:
                self.logger.error("Critical errors detected during ingestion. Aborting pipeline.")
                return self._finalize_execution(metrics, success=False)

            # Processing phase
            self.logger.info("=== DATA PROCESSING PHASE ===")
            usage_records, cost_records = self._process_and_transform_data(
                cursor_data, anthropic_usage_data, anthropic_cost_data, api_mappings, metrics
            )

            # Storage phase
            self.logger.info("=== DATA STORAGE PHASE ===")
            self._insert_data_to_bigquery(usage_records, cost_records, metrics)

            # Determine overall success
            success = not metrics.has_critical_errors and (metrics.usage_records_inserted > 0 or metrics.cost_records_inserted > 0)

            return self._finalize_execution(metrics, success=success)

        except Exception as e:
            self.logger.error(f"Unexpected error in pipeline execution: {e}")
            error = PipelineError(
                error_code="PIPELINE_UNEXPECTED_ERROR",
                message=f"Pipeline execution failed: {e}",
                component="orchestrator",
                exception=e,
                recoverable=False
            )
            metrics.errors.append(error)
            return self._finalize_execution(metrics, success=False)

    def _finalize_execution(self, metrics: PipelineMetrics, success: bool) -> Dict[str, Any]:
        """Finalize pipeline execution with metrics and monitoring."""
        metrics.end_time = time.time()

        # Generate comprehensive summary
        summary = self._generate_metrics_summary(metrics)
        summary["success"] = success

        # Log final results
        if success:
            self.logger.info(f"Pipeline execution completed successfully in {metrics.total_processing_time:.2f}s")
        else:
            self.logger.error(f"Pipeline execution failed after {metrics.total_processing_time:.2f}s")

        # Log detailed metrics
        self.logger.info(f"Final metrics: {summary}")

        # Report to monitoring system
        try:
            self.monitor.record_pipeline_metrics(summary)
        except Exception as e:
            self.logger.warning(f"Failed to record metrics to monitoring system: {e}")

        # Report to Cloud Monitoring
        try:
            self._record_cloud_monitoring_metrics(summary, success)
        except Exception as e:
            self.logger.warning(f"Failed to record Cloud Monitoring metrics: {e}")

        return summary

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all pipeline components."""
        self.logger.info("Performing pipeline health check")

        health_status = {
            "request_id": self.request_id,
            "overall_status": "healthy",
            "components": {},
            "timestamp": time.time()
        }

        try:
            # Initialize clients for health check
            self._initialize_clients()

            # Check individual components with improved error descriptions
            components = {
                "cursor_api": (self.cursor_client.health_check, "Cursor API connectivity"),
                "anthropic_api": (self.anthropic_client.health_check, "Anthropic API connectivity"),
                "sheets_api": (lambda: bool(self.sheets_client), "Google Sheets client initialization"),
                "bigquery": (self.storage_client.health_check if self.storage_client else lambda: True, "BigQuery connectivity")
            }

            for component_name, (health_func, description) in components.items():
                try:
                    is_healthy = health_func()
                    health_status["components"][component_name] = {
                        "status": "healthy" if is_healthy else "unhealthy",
                        "details": f"{description} - Connection successful" if is_healthy else f"{description} - Connection failed",
                        "checked_at": time.time()
                    }

                    if not is_healthy:
                        health_status["overall_status"] = "degraded"

                except Exception as e:
                    health_status["components"][component_name] = {
                        "status": "error",
                        "details": f"{description} - Error: {str(e)}",
                        "checked_at": time.time()
                    }
                    health_status["overall_status"] = "unhealthy"

        except Exception as e:
            health_status["overall_status"] = "error"
            health_status["error"] = f"Health check initialization failed: {str(e)}"

        self.logger.info(f"Health check completed: {health_status['overall_status']}")
        return health_status


def main():
    """Entry point for daily job execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Daily Usage Data Pipeline")
    parser.add_argument("--mode", choices=["development", "production", "dry_run"],
                       default="production", help="Execution mode")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=1, help="Number of days to process")
    parser.add_argument("--health-check", action="store_true", help="Run health check only")

    args = parser.parse_args()

    # Create orchestrator
    mode = ExecutionMode(args.mode)
    orchestrator = DailyJobOrchestrator(execution_mode=mode)

    if args.health_check:
        # Run health check
        result = orchestrator.health_check()
        print(f"Health check result: {result}")
        return

    # Parse target date
    target_date = None
    if args.date:
        from datetime import datetime
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    # Run daily job
    result = orchestrator.run_daily_job(target_date=target_date, date_range_days=args.days)

    # Print summary
    print(f"Pipeline execution {'succeeded' if result['success'] else 'failed'}")
    print(f"Processing time: {result['processing_time_seconds']:.2f}s")
    print(f"Records processed: {result['storage_metrics']['usage_records_inserted']} usage, {result['storage_metrics']['cost_records_inserted']} cost")

    if result['error_summary']['total_errors'] > 0:
        print(f"Errors encountered: {result['error_summary']['total_errors']} total, {result['error_summary']['critical_errors']} critical")


if __name__ == "__main__":
    main()