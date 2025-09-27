"""Unit tests for monitoring system."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.shared.monitoring import (
    HealthChecker, MetricsCollector, AlertManager, SystemMonitor,
    HealthStatus, HealthCheckResult, SystemHealthReport
)
from src.shared.cloud_monitoring import CloudMonitoringClient, MetricType, MetricPoint
from src.shared.alert_manager import AlertManager as NewAlertManager, AlertPolicyConfig, NotificationChannelConfig
from src.shared.business_metrics import BusinessMetricsCollector, BusinessMetricResult
from src.shared.error_tracker import ErrorTracker, ErrorEvent, ErrorCategory, ErrorSeverity
from src.shared.logging_setup import StructuredFormatter, RequestContextLogger, generate_request_id


@pytest.fixture
def health_checker():
    """Create HealthChecker instance."""
    return HealthChecker()


@pytest.fixture
def metrics_collector():
    """Create MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def alert_manager(metrics_collector):
    """Create AlertManager instance."""
    return AlertManager(metrics_collector)


class TestHealthChecker:
    """Test cases for HealthChecker."""

    def test_register_check(self, health_checker):
        """Test registering a health check."""
        mock_check = Mock(return_value=True)
        health_checker.register_check("test_component", mock_check)

        assert "test_component" in health_checker.checks
        assert health_checker.checks["test_component"] == mock_check

    def test_run_check_success(self, health_checker):
        """Test running a successful health check."""
        mock_check = Mock(return_value=True)

        result = health_checker.run_check("test_component", mock_check)

        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Health check passed"
        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0

    def test_run_check_failure(self, health_checker):
        """Test running a failed health check."""
        mock_check = Mock(return_value=False)

        result = health_checker.run_check("test_component", mock_check)

        assert result.component == "test_component"
        assert result.status == HealthStatus.CRITICAL
        assert result.message == "Health check failed"

    def test_run_check_exception(self, health_checker):
        """Test running a health check that raises exception."""
        mock_check = Mock(side_effect=Exception("Test error"))

        result = health_checker.run_check("test_component", mock_check)

        assert result.component == "test_component"
        assert result.status == HealthStatus.CRITICAL
        assert "Test error" in result.message
        assert result.details is not None

    def test_run_all_checks(self, health_checker):
        """Test running all registered checks."""
        # Register multiple checks
        health_checker.register_check("healthy_component", Mock(return_value=True))
        health_checker.register_check("unhealthy_component", Mock(return_value=False))

        report = health_checker.run_all_checks()

        assert isinstance(report, SystemHealthReport)
        assert report.total_checks == 2
        assert report.healthy_checks == 1
        assert report.critical_checks == 1
        assert report.overall_status == HealthStatus.CRITICAL  # One critical component

    def test_run_all_checks_empty(self, health_checker):
        """Test running checks with no registered components."""
        report = health_checker.run_all_checks()

        assert report.total_checks == 0
        assert report.overall_status == HealthStatus.UNKNOWN


class TestMetricsCollector:
    """Test cases for MetricsCollector."""

    def test_record_metric_basic(self, metrics_collector):
        """Test basic metric recording."""
        metrics_collector.record_metric("test_metric", 123.45)

        assert "test_metric" in metrics_collector.metrics
        assert len(metrics_collector.metrics["test_metric"]) == 1
        assert metrics_collector.metrics["test_metric"][0]["value"] == 123.45

    def test_record_metric_with_labels(self, metrics_collector):
        """Test metric recording with labels."""
        labels = {"environment": "test", "component": "api"}
        metrics_collector.record_metric("response_time", 50.0, labels=labels)

        metric = metrics_collector.metrics["response_time"][0]
        assert metric["value"] == 50.0
        assert metric["labels"] == labels

    def test_record_metric_with_timestamp(self, metrics_collector):
        """Test metric recording with custom timestamp."""
        timestamp = datetime(2022, 1, 1, 12, 0, 0)
        metrics_collector.record_metric("test_metric", 100, timestamp=timestamp)

        metric = metrics_collector.metrics["test_metric"][0]
        assert metric["timestamp"] == "2022-01-01T12:00:00"

    def test_record_metric_memory_limit(self, metrics_collector):
        """Test metric recording respects memory limits."""
        # Record more than 1000 metrics
        for i in range(1050):
            metrics_collector.record_metric("test_metric", i)

        # Should only keep last 1000
        assert len(metrics_collector.metrics["test_metric"]) == 1000
        # Should have the most recent values
        assert metrics_collector.metrics["test_metric"][-1]["value"] == 1049

    def test_get_recent_metrics(self, metrics_collector):
        """Test getting recent metrics."""
        now = datetime.now()
        old_time = now - timedelta(hours=25)  # Older than 24h
        recent_time = now - timedelta(hours=1)  # Within 24h

        # Record metrics at different times
        metrics_collector.record_metric("test_metric", 1, timestamp=old_time)
        metrics_collector.record_metric("test_metric", 2, timestamp=recent_time)

        recent = metrics_collector.get_recent_metrics("test_metric", hours=24)

        assert len(recent) == 1
        assert recent[0]["value"] == 2

    def test_get_recent_metrics_empty(self, metrics_collector):
        """Test getting recent metrics for non-existent metric."""
        recent = metrics_collector.get_recent_metrics("non_existent", hours=24)
        assert len(recent) == 0

    def test_calculate_summary_stats(self, metrics_collector):
        """Test summary statistics calculation."""
        # Record multiple values
        values = [10, 20, 30, 40, 50]
        for value in values:
            metrics_collector.record_metric("test_metric", value)

        stats = metrics_collector.calculate_summary_stats("test_metric")

        assert stats["count"] == 5
        assert stats["min"] == 10
        assert stats["max"] == 50
        assert stats["mean"] == 30
        assert stats["median"] == 30

    def test_calculate_summary_stats_percentiles(self, metrics_collector):
        """Test percentile calculations with larger dataset."""
        # Record 100 values
        for i in range(100):
            metrics_collector.record_metric("test_metric", i)

        stats = metrics_collector.calculate_summary_stats("test_metric")

        assert "p95" in stats
        assert "p99" in stats
        assert stats["p95"] >= stats["median"]
        assert stats["p99"] >= stats["p95"]

    def test_calculate_summary_stats_empty(self, metrics_collector):
        """Test summary stats for non-existent metric."""
        stats = metrics_collector.calculate_summary_stats("non_existent")
        assert stats == {}


class TestAlertManager:
    """Test cases for AlertManager."""

    def test_init_with_metrics_collector(self, metrics_collector):
        """Test AlertManager initialization with metrics collector."""
        alert_manager = AlertManager(metrics_collector)
        assert alert_manager.metrics == metrics_collector

    def test_init_without_metrics_collector(self):
        """Test AlertManager initialization creates default metrics collector."""
        alert_manager = AlertManager()
        assert alert_manager.metrics is not None

    def test_check_alert_conditions_no_data(self, alert_manager):
        """Test alert checking with no metrics data."""
        alerts = alert_manager.check_alert_conditions()
        assert len(alerts) == 0

    def test_check_alert_conditions_low_attribution(self, alert_manager):
        """Test alert for low attribution rate."""
        # Record low attribution rate
        alert_manager.metrics.record_metric("attribution_rate", 0.75)  # Below 0.90 threshold

        alerts = alert_manager.check_alert_conditions()

        assert len(alerts) > 0
        attribution_alerts = [a for a in alerts if a["type"] == "low_attribution_rate"]
        assert len(attribution_alerts) == 1
        assert attribution_alerts[0]["severity"] == "critical"

    def test_check_alert_conditions_slow_processing(self, alert_manager):
        """Test alert for slow processing."""
        # Record slow processing time
        alert_manager.metrics.record_metric("processing_time_seconds", 400)  # Above 300s threshold

        alerts = alert_manager.check_alert_conditions()

        slow_alerts = [a for a in alerts if a["type"] == "slow_processing"]
        assert len(slow_alerts) == 1
        assert slow_alerts[0]["severity"] == "warning"

    def test_send_alert_critical(self, alert_manager):
        """Test sending critical alert."""
        alert = {
            "type": "test_alert",
            "severity": "critical",
            "message": "Test critical alert"
        }

        result = alert_manager.send_alert(alert)

        assert result is True
        # Check that alert metric was recorded
        alert_metrics = alert_manager.metrics.get_recent_metrics("alerts_sent")
        assert len(alert_metrics) == 1

    def test_send_alert_warning(self, alert_manager):
        """Test sending warning alert."""
        alert = {
            "type": "test_alert",
            "severity": "warning",
            "message": "Test warning alert"
        }

        result = alert_manager.send_alert(alert)
        assert result is True


class TestSystemMonitor:
    """Test cases for SystemMonitor."""

    @patch('src.shared.monitoring.BigQuerySchemaManager')
    @patch('src.shared.monitoring.config')
    def test_init_registers_checks(self, mock_config, mock_bq_manager_class):
        """Test SystemMonitor initialization registers health checks."""
        # Mock config to avoid actual API calls
        mock_config.cursor_api_key = None
        mock_config.anthropic_api_key = None
        mock_config.sheets_id = None

        mock_bq_manager = Mock()
        mock_bq_manager.health_check = Mock(return_value=True)
        mock_bq_manager_class.return_value = mock_bq_manager

        monitor = SystemMonitor()

        assert "bigquery" in monitor.health_checker.checks

    def test_record_pipeline_metrics(self):
        """Test recording pipeline metrics."""
        monitor = SystemMonitor()

        pipeline_result = {
            "processing_time_seconds": 45.5,
            "transformation_stats": {
                "total_input": 100,
                "total_output": 95
            }
        }

        monitor.record_pipeline_metrics(pipeline_result)

        # Check that metrics were recorded
        processing_metrics = monitor.metrics_collector.get_recent_metrics("processing_time_seconds")
        assert len(processing_metrics) == 1
        assert processing_metrics[0]["value"] == 45.5

        records_metrics = monitor.metrics_collector.get_recent_metrics("records_processed")
        assert len(records_metrics) == 1
        assert records_metrics[0]["value"] == 95

    def test_generate_monitoring_summary(self):
        """Test monitoring summary generation."""
        with patch.object(SystemMonitor, '_register_builtin_checks'):
            monitor = SystemMonitor()

        # Register a mock health check
        monitor.health_checker.register_check("test_component", Mock(return_value=True))

        summary = monitor.generate_monitoring_summary()

        assert "System Monitoring Summary" in summary
        assert "Overall Health:" in summary
        assert "Components:" in summary

    def test_export_metrics(self):
        """Test metrics export functionality."""
        with patch.object(SystemMonitor, '_register_builtin_checks'):
            monitor = SystemMonitor()

        # Record some test metrics
        monitor.metrics_collector.record_metric("test_metric", 123)

        export_data = monitor.export_metrics(hours=1)

        assert "export_timestamp" in export_data
        assert "time_range_hours" in export_data
        assert "metrics" in export_data
        assert export_data["time_range_hours"] == 1


class TestHealthCheckResult:
    """Test cases for HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation."""
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="All good",
            response_time_ms=50.0
        )

        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.response_time_ms == 50.0
        assert result.timestamp is not None

    def test_health_check_result_auto_timestamp(self):
        """Test automatic timestamp assignment."""
        result = HealthCheckResult(
            component="test",
            status=HealthStatus.HEALTHY,
            message="Test"
        )

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)


class TestCloudMonitoringClient:
    """Test cases for CloudMonitoringClient."""

    @patch('src.shared.cloud_monitoring.monitoring_v3.MetricServiceClient')
    @patch('src.shared.cloud_monitoring.config')
    def test_initialization(self, mock_config, mock_client):
        """Test CloudMonitoringClient initialization."""
        mock_config.project_id = "test-project"
        mock_config.env = "test"

        client = CloudMonitoringClient()

        assert client.project_id == "test-project"
        assert client.project_name == "projects/test-project"
        mock_client.assert_called_once()

    @patch('src.shared.cloud_monitoring.monitoring_v3.MetricServiceClient')
    @patch('src.shared.cloud_monitoring.config')
    def test_record_pipeline_health(self, mock_config, mock_client):
        """Test pipeline health metric recording."""
        mock_config.project_id = "test-project"
        mock_config.env = "test"

        client = CloudMonitoringClient()
        client.record_pipeline_health(95.5, "test_job")

        # Should create time series
        mock_client.return_value.create_time_series.assert_called()


class TestErrorTracker:
    """Test cases for ErrorTracker."""

    def test_initialization(self):
        """Test ErrorTracker initialization."""
        tracker = ErrorTracker()
        assert tracker.errors == []

    def test_error_categorization_api_error(self):
        """Test API error categorization."""
        error = ValueError("HTTP 429 rate limit exceeded")
        event = ErrorEvent.from_exception(error, "cursor_client", "cursor")

        assert event.category == ErrorCategory.API_ERROR
        assert event.component == "cursor_client"
        assert event.platform == "cursor"

    def test_track_error(self):
        """Test error tracking functionality."""
        tracker = ErrorTracker()
        error_event = ErrorEvent(
            error_id="test123",
            category=ErrorCategory.API_ERROR,
            severity=ErrorSeverity.MEDIUM,
            component="test_component",
            error_type="TestError",
            message="Test error message"
        )

        tracker.track_error(error_event)

        assert len(tracker.errors) == 1
        assert tracker.errors[0].error_id == "test123"


def test_generate_request_id():
    """Test request ID generation."""
    request_id1 = generate_request_id()
    request_id2 = generate_request_id()

    # Should be unique UUIDs
    assert request_id1 != request_id2
    assert len(request_id1) == 36  # UUID format
    assert "-" in request_id1