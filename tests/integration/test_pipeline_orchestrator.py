"""Integration tests for pipeline orchestrator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
from dataclasses import asdict

from src.orchestration.daily_job import (
    DailyJobOrchestrator, ExecutionMode, PipelineError, PipelineMetrics
)
from src.ingestion.cursor_client import CursorUsageData
from src.ingestion.anthropic_client import AnthropicUsageData, AnthropicCostData
from src.ingestion.sheets_client import APIKeyMapping


@pytest.fixture
def mock_api_responses():
    """Mock API responses for integration testing."""
    return {
        "cursor_data": [
            CursorUsageData(
                email="user1@company.com",
                total_lines_added=1000,
                accepted_lines_added=800,
                total_accepts=25,
                subscription_included_reqs=50,
                usage_based_reqs=10,
                date=date(2022, 1, 1)
            ),
            CursorUsageData(
                email="user2@company.com",
                total_lines_added=500,
                accepted_lines_added=400,
                total_accepts=15,
                subscription_included_reqs=30,
                usage_based_reqs=5,
                date=date(2022, 1, 1)
            )
        ],
        "anthropic_usage_data": [
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
            )
        ],
        "anthropic_cost_data": [
            AnthropicCostData(
                api_key_id="key_123",
                workspace_id="ws_456",
                model="claude-3-sonnet-20240229",
                cost_usd=15.75,
                cost_type="total_cost",
                cost_date=date(2022, 1, 1),
                cost_hour=12
            )
        ],
        "api_mappings": [
            APIKeyMapping(
                api_key_name="key_123",
                user_email="user3@company.com",
                description="Test API key",
                platform="anthropic"
            )
        ]
    }


class TestDailyJobOrchestrator:
    """Test cases for DailyJobOrchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization in different modes."""
        # Test production mode
        orchestrator = DailyJobOrchestrator(ExecutionMode.PRODUCTION)
        assert orchestrator.execution_mode == ExecutionMode.PRODUCTION
        assert orchestrator.batch_size == 1000
        assert orchestrator.request_id is not None

        # Test development mode
        dev_orchestrator = DailyJobOrchestrator(ExecutionMode.DEVELOPMENT)
        assert dev_orchestrator.execution_mode == ExecutionMode.DEVELOPMENT
        assert dev_orchestrator.batch_size == 100

        # Test dry run mode
        dry_orchestrator = DailyJobOrchestrator(ExecutionMode.DRY_RUN)
        assert dry_orchestrator.execution_mode == ExecutionMode.DRY_RUN

    @patch('src.orchestration.daily_job.CursorClient')
    @patch('src.orchestration.daily_job.AnthropicClient')
    @patch('src.orchestration.daily_job.GoogleSheetsClient')
    @patch('src.orchestration.daily_job.MultiPlatformTransformer')
    @patch('src.orchestration.daily_job.UserAttributionEngine')
    @patch('src.orchestration.daily_job.BigQuerySchemaManager')
    @patch('src.orchestration.daily_job.SystemMonitor')
    def test_component_initialization(self, mock_monitor, mock_bq, mock_attribution,
                                    mock_transformer, mock_sheets, mock_anthropic, mock_cursor):
        """Test initialization of all pipeline components."""
        orchestrator = DailyJobOrchestrator(ExecutionMode.PRODUCTION)
        orchestrator._initialize_clients()

        # Verify all components were initialized
        mock_cursor.assert_called_once()
        mock_anthropic.assert_called_once()
        mock_sheets.assert_called_once()
        mock_transformer.assert_called_once()
        mock_attribution.assert_called_once()
        mock_bq.assert_called_once()

    @patch('src.orchestration.daily_job.CursorClient')
    def test_fetch_cursor_data_success(self, mock_cursor_class, mock_api_responses):
        """Test successful Cursor data fetching."""
        # Setup mock
        mock_cursor = Mock()
        mock_cursor.get_daily_usage_data.return_value = mock_api_responses["cursor_data"]
        mock_cursor_class.return_value = mock_cursor

        orchestrator = DailyJobOrchestrator(ExecutionMode.DEVELOPMENT)
        orchestrator.cursor_client = mock_cursor
        metrics = PipelineMetrics("test-id", ExecutionMode.DEVELOPMENT, 0.0)

        # Execute
        result = orchestrator._fetch_cursor_data(date(2022, 1, 1), date(2022, 1, 2), metrics)

        # Verify
        assert len(result) == 2
        assert metrics.cursor_records == 2
        assert len(metrics.errors) == 0

    @patch('src.orchestration.daily_job.CursorClient')
    def test_fetch_cursor_data_error_handling(self, mock_cursor_class):
        """Test Cursor API error handling."""
        from src.ingestion.cursor_client import CursorAPIError

        # Setup mock to raise error
        mock_cursor = Mock()
        mock_cursor.get_daily_usage_data.side_effect = CursorAPIError("API Error")
        mock_cursor_class.return_value = mock_cursor

        orchestrator = DailyJobOrchestrator(ExecutionMode.DEVELOPMENT)
        orchestrator.cursor_client = mock_cursor
        metrics = PipelineMetrics("test-id", ExecutionMode.DEVELOPMENT, 0.0)

        # Execute
        result = orchestrator._fetch_cursor_data(date(2022, 1, 1), date(2022, 1, 2), metrics)

        # Verify error handling
        assert result == []
        assert metrics.cursor_records == 0
        assert len(metrics.errors) == 1
        assert metrics.errors[0].error_code == "CURSOR_API_ERROR"
        assert metrics.errors[0].recoverable is True

    @patch('src.orchestration.daily_job.AnthropicClient')
    def test_fetch_anthropic_data_success(self, mock_anthropic_class, mock_api_responses):
        """Test successful Anthropic data fetching."""
        # Setup mock
        mock_anthropic = Mock()
        mock_anthropic.get_usage_data.return_value = mock_api_responses["anthropic_usage_data"]
        mock_anthropic.get_cost_data.return_value = mock_api_responses["anthropic_cost_data"]
        mock_anthropic_class.return_value = mock_anthropic

        orchestrator = DailyJobOrchestrator(ExecutionMode.DEVELOPMENT)
        orchestrator.anthropic_client = mock_anthropic
        metrics = PipelineMetrics("test-id", ExecutionMode.DEVELOPMENT, 0.0)

        # Execute
        usage_data, cost_data = orchestrator._fetch_anthropic_data(date(2022, 1, 1), date(2022, 1, 2), metrics)

        # Verify
        assert len(usage_data) == 1
        assert len(cost_data) == 1
        assert metrics.anthropic_usage_records == 1
        assert metrics.anthropic_cost_records == 1
        assert len(metrics.errors) == 0

    @patch('src.orchestration.daily_job.GoogleSheetsClient')
    def test_fetch_sheets_mappings_success(self, mock_sheets_class, mock_api_responses):
        """Test successful Google Sheets mappings fetching."""
        # Setup mock
        mock_sheets = Mock()
        mock_sheets.get_api_key_mappings.return_value = mock_api_responses["api_mappings"]
        mock_sheets_class.return_value = mock_sheets

        orchestrator = DailyJobOrchestrator(ExecutionMode.DEVELOPMENT)
        orchestrator.sheets_client = mock_sheets
        metrics = PipelineMetrics("test-id", ExecutionMode.DEVELOPMENT, 0.0)

        # Execute
        result = orchestrator._fetch_sheets_mappings(metrics)

        # Verify
        assert len(result) == 1
        assert metrics.sheets_mappings == 1
        assert len(metrics.errors) == 0

    @patch('src.orchestration.daily_job.MultiPlatformTransformer')
    def test_process_and_transform_data_success(self, mock_transformer_class, mock_api_responses):
        """Test successful data transformation and attribution."""
        # Setup mock transformer
        mock_transformer = Mock()
        mock_transformer.transform_all_usage_data.return_value = {
            "success": True,
            "usage_records": [Mock(user_email="user1@company.com"), Mock(user_email="user2@company.com")],
            "transformation_stats": {"total_input": 3, "total_output": 2}
        }
        mock_transformer.create_cost_records.return_value = [Mock()]
        mock_transformer_class.return_value = mock_transformer

        orchestrator = DailyJobOrchestrator(ExecutionMode.DEVELOPMENT)
        orchestrator.transformer = mock_transformer
        metrics = PipelineMetrics("test-id", ExecutionMode.DEVELOPMENT, 0.0)

        # Execute
        usage_records, cost_records = orchestrator._process_and_transform_data(
            mock_api_responses["cursor_data"],
            mock_api_responses["anthropic_usage_data"],
            mock_api_responses["anthropic_cost_data"],
            mock_api_responses["api_mappings"],
            metrics
        )

        # Verify
        assert len(usage_records) == 2
        assert len(cost_records) == 1
        assert metrics.transformation_success_rate == 2/3  # 2 output / 3 input
        assert metrics.attribution_rate == 1.0  # All records have user_email
        assert len(metrics.errors) == 0

    def test_insert_data_dry_run_mode(self, mock_api_responses):
        """Test data insertion in dry run mode."""
        orchestrator = DailyJobOrchestrator(ExecutionMode.DRY_RUN)
        metrics = PipelineMetrics("test-id", ExecutionMode.DRY_RUN, 0.0)

        # Execute
        usage_records = [Mock(), Mock()]
        cost_records = [Mock()]
        orchestrator._insert_data_to_bigquery(usage_records, cost_records, metrics)

        # Verify dry run behavior
        assert metrics.usage_records_inserted == 2
        assert metrics.cost_records_inserted == 1
        assert len(metrics.errors) == 0

    @patch('src.orchestration.daily_job.BigQuerySchemaManager')
    def test_insert_data_production_mode(self, mock_bq_class):
        """Test data insertion in production mode."""
        # Setup mock
        mock_bq = Mock()
        mock_bq_class.return_value = mock_bq

        orchestrator = DailyJobOrchestrator(ExecutionMode.PRODUCTION)
        orchestrator.storage_client = mock_bq
        metrics = PipelineMetrics("test-id", ExecutionMode.PRODUCTION, 0.0)

        # Execute
        usage_records = [Mock(), Mock()]
        cost_records = [Mock()]
        orchestrator._insert_data_to_bigquery(usage_records, cost_records, metrics)

        # Verify BigQuery calls
        mock_bq.insert_usage_data.assert_called_once_with(usage_records, batch_size=1000)
        mock_bq.insert_cost_data.assert_called_once_with(cost_records, batch_size=1000)
        assert metrics.usage_records_inserted == 2
        assert metrics.cost_records_inserted == 1

    def test_pipeline_metrics_calculations(self):
        """Test pipeline metrics calculations."""
        import time

        metrics = PipelineMetrics("test-id", ExecutionMode.DEVELOPMENT, time.time())

        # Add some errors
        metrics.errors.append(PipelineError("TEST_ERROR", "Test", "component", recoverable=True))
        metrics.errors.append(PipelineError("CRITICAL_ERROR", "Critical", "component", recoverable=False))

        # Test calculations
        assert metrics.has_critical_errors is True
        assert metrics.total_processing_time > 0

        # Test with only recoverable errors
        metrics_recoverable = PipelineMetrics("test-id-2", ExecutionMode.DEVELOPMENT, time.time())
        metrics_recoverable.errors.append(PipelineError("MINOR_ERROR", "Minor", "component", recoverable=True))
        assert metrics_recoverable.has_critical_errors is False

    @patch('src.orchestration.daily_job.CursorClient')
    @patch('src.orchestration.daily_job.AnthropicClient')
    @patch('src.orchestration.daily_job.GoogleSheetsClient')
    @patch('src.orchestration.daily_job.MultiPlatformTransformer')
    @patch('src.orchestration.daily_job.UserAttributionEngine')
    @patch('src.orchestration.daily_job.SystemMonitor')
    def test_end_to_end_pipeline_success(self, mock_monitor, mock_attribution, mock_transformer,
                                       mock_sheets, mock_anthropic, mock_cursor, mock_api_responses):
        """Test complete end-to-end pipeline execution."""
        # Setup all mocks
        mock_cursor_client = Mock()
        mock_cursor_client.get_daily_usage_data.return_value = mock_api_responses["cursor_data"]
        mock_cursor.return_value = mock_cursor_client

        mock_anthropic_client = Mock()
        mock_anthropic_client.get_usage_data.return_value = mock_api_responses["anthropic_usage_data"]
        mock_anthropic_client.get_cost_data.return_value = mock_api_responses["anthropic_cost_data"]
        mock_anthropic.return_value = mock_anthropic_client

        mock_sheets_client = Mock()
        mock_sheets_client.get_api_key_mappings.return_value = mock_api_responses["api_mappings"]
        mock_sheets.return_value = mock_sheets_client

        mock_transformer_instance = Mock()
        mock_transformer_instance.transform_all_usage_data.return_value = {
            "success": True,
            "usage_records": [Mock(user_email="user@company.com")],
            "transformation_stats": {"total_input": 3, "total_output": 1}
        }
        mock_transformer_instance.create_cost_records.return_value = [Mock()]
        mock_transformer.return_value = mock_transformer_instance

        mock_attribution.return_value = Mock()
        mock_monitor.return_value = Mock()

        # Run pipeline in dry run mode to avoid BigQuery
        orchestrator = DailyJobOrchestrator(ExecutionMode.DRY_RUN)
        result = orchestrator.run_daily_job(target_date=date(2022, 1, 1))

        # Verify successful execution
        assert result["success"] is True
        assert result["data_ingestion"]["cursor_records"] == 2
        assert result["data_ingestion"]["anthropic_usage_records"] == 1
        assert result["data_ingestion"]["anthropic_cost_records"] == 1
        assert result["data_ingestion"]["sheets_mappings"] == 1
        assert result["storage_metrics"]["usage_records_inserted"] == 1
        assert result["storage_metrics"]["cost_records_inserted"] == 1
        assert result["error_summary"]["total_errors"] == 0

    @patch('src.orchestration.daily_job.CursorClient')
    @patch('src.orchestration.daily_job.AnthropicClient')
    @patch('src.orchestration.daily_job.GoogleSheetsClient')
    @patch('src.orchestration.daily_job.MultiPlatformTransformer')
    @patch('src.orchestration.daily_job.UserAttributionEngine')
    @patch('src.orchestration.daily_job.SystemMonitor')
    def test_pipeline_partial_failure_handling(self, mock_monitor, mock_attribution, mock_transformer,
                                              mock_sheets, mock_anthropic, mock_cursor):
        """Test pipeline handling of partial failures."""
        from src.ingestion.cursor_client import CursorAPIError

        # Setup mocks with one failing API
        mock_cursor_client = Mock()
        mock_cursor_client.get_daily_usage_data.side_effect = CursorAPIError("API Error")
        mock_cursor.return_value = mock_cursor_client

        mock_anthropic_client = Mock()
        mock_anthropic_client.get_usage_data.return_value = []
        mock_anthropic_client.get_cost_data.return_value = []
        mock_anthropic.return_value = mock_anthropic_client

        mock_sheets_client = Mock()
        mock_sheets_client.get_api_key_mappings.return_value = []
        mock_sheets.return_value = mock_sheets_client

        mock_transformer_instance = Mock()
        mock_transformer_instance.transform_all_usage_data.return_value = {
            "success": True,
            "usage_records": [],
            "transformation_stats": {"total_input": 0, "total_output": 0}
        }
        mock_transformer_instance.create_cost_records.return_value = []
        mock_transformer.return_value = mock_transformer_instance

        mock_attribution.return_value = Mock()
        mock_monitor.return_value = Mock()

        # Run pipeline
        orchestrator = DailyJobOrchestrator(ExecutionMode.DRY_RUN)
        result = orchestrator.run_daily_job(target_date=date(2022, 1, 1))

        # Verify partial failure handling
        assert result["success"] is False  # No data inserted
        assert result["error_summary"]["total_errors"] == 1
        assert "CURSOR_API_ERROR" in str(result)

    def test_health_check_functionality(self):
        """Test comprehensive health check functionality."""
        with patch('src.orchestration.daily_job.CursorClient') as mock_cursor, \
             patch('src.orchestration.daily_job.AnthropicClient') as mock_anthropic, \
             patch('src.orchestration.daily_job.GoogleSheetsClient') as mock_sheets, \
             patch('src.orchestration.daily_job.SystemMonitor') as mock_monitor:

            # Setup healthy mocks
            mock_cursor_instance = Mock()
            mock_cursor_instance.health_check.return_value = True
            mock_cursor.return_value = mock_cursor_instance

            mock_anthropic_instance = Mock()
            mock_anthropic_instance.health_check.return_value = True
            mock_anthropic.return_value = mock_anthropic_instance

            mock_sheets.return_value = Mock()
            mock_monitor.return_value = Mock()

            # Run health check
            orchestrator = DailyJobOrchestrator(ExecutionMode.DRY_RUN)
            result = orchestrator.health_check()

            # Verify health check results
            assert result["overall_status"] == "healthy"
            assert "cursor_api" in result["components"]
            assert "anthropic_api" in result["components"]
            assert result["components"]["cursor_api"]["status"] == "healthy"
            assert result["components"]["anthropic_api"]["status"] == "healthy"

    def test_generate_metrics_summary(self):
        """Test comprehensive metrics summary generation."""
        import time

        metrics = PipelineMetrics("test-request-id", ExecutionMode.PRODUCTION, time.time())
        metrics.cursor_records = 100
        metrics.anthropic_usage_records = 50
        metrics.anthropic_cost_records = 25
        metrics.sheets_mappings = 10
        metrics.transformation_success_rate = 0.95
        metrics.attribution_rate = 0.80
        metrics.usage_records_inserted = 90
        metrics.cost_records_inserted = 20
        metrics.errors.append(PipelineError("TEST_ERROR", "Test error", "test_component"))

        orchestrator = DailyJobOrchestrator(ExecutionMode.PRODUCTION)
        summary = orchestrator._generate_metrics_summary(metrics)

        # Verify summary structure and content
        assert summary["request_id"] == "test-request-id"
        assert summary["execution_mode"] == "production"
        assert summary["data_ingestion"]["cursor_records"] == 100
        assert summary["data_ingestion"]["anthropic_usage_records"] == 50
        assert summary["data_ingestion"]["anthropic_cost_records"] == 25
        assert summary["data_ingestion"]["sheets_mappings"] == 10
        assert summary["processing_metrics"]["transformation_success_rate"] == 0.95
        assert summary["processing_metrics"]["attribution_rate"] == 0.80
        assert summary["storage_metrics"]["usage_records_inserted"] == 90
        assert summary["storage_metrics"]["cost_records_inserted"] == 20
        assert summary["error_summary"]["total_errors"] == 1
        assert summary["error_summary"]["critical_errors"] == 0
        assert "test_component" in summary["error_summary"]["error_components"]

    def test_execution_mode_configurations(self):
        """Test different execution mode configurations."""
        # Test development mode
        dev_orchestrator = DailyJobOrchestrator(ExecutionMode.DEVELOPMENT)
        assert dev_orchestrator.batch_size == 100

        # Test production mode
        prod_orchestrator = DailyJobOrchestrator(ExecutionMode.PRODUCTION)
        assert prod_orchestrator.batch_size == 1000

        # Test dry run mode
        dry_orchestrator = DailyJobOrchestrator(ExecutionMode.DRY_RUN)
        assert dry_orchestrator.execution_mode == ExecutionMode.DRY_RUN