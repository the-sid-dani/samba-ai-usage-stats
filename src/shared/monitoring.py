"""Monitoring and health check system for AI Usage Analytics Dashboard."""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .logging_setup import get_logger
from .config import config


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SystemHealthReport:
    """Comprehensive system health report."""
    overall_status: HealthStatus
    components: List[HealthCheckResult]
    total_checks: int
    healthy_checks: int
    warning_checks: int
    critical_checks: int
    report_timestamp: datetime
    recommendations: List[str]


class HealthChecker:
    """Centralized health checking system."""

    def __init__(self):
        self.logger = get_logger("health_checker")
        self.checks: Dict[str, Callable] = {}

    def register_check(self, name: str, check_function: Callable) -> None:
        """
        Register a health check function.

        Args:
            name: Name of the component being checked
            check_function: Function that returns bool (True = healthy)
        """
        self.checks[name] = check_function
        self.logger.info(f"Registered health check: {name}")

    def run_check(self, component: str, check_function: Callable) -> HealthCheckResult:
        """
        Run a single health check with timing.

        Args:
            component: Name of component being checked
            check_function: Function to execute

        Returns:
            HealthCheckResult with status and timing
        """
        start_time = time.time()

        try:
            self.logger.debug(f"Running health check: {component}")
            result = check_function()
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms

            if result is True:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message="Health check passed",
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message="Health check failed",
                    response_time_ms=response_time
                )

        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            self.logger.error(f"Health check error for {component}: {e}")
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"Health check error: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)}
            )

    def run_all_checks(self) -> SystemHealthReport:
        """
        Run all registered health checks.

        Returns:
            SystemHealthReport with consolidated results
        """
        start_time = datetime.now()
        self.logger.info(f"Starting health checks for {len(self.checks)} components")

        results = []
        for component, check_function in self.checks.items():
            result = self.run_check(component, check_function)
            results.append(result)

        # Count statuses
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 0,
            HealthStatus.CRITICAL: 0,
            HealthStatus.UNKNOWN: 0
        }

        for result in results:
            status_counts[result.status] += 1

        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            overall_status = HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > 0:
            overall_status = HealthStatus.WARNING
        elif status_counts[HealthStatus.HEALTHY] > 0:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        # Generate recommendations
        recommendations = self._generate_health_recommendations(results)

        report = SystemHealthReport(
            overall_status=overall_status,
            components=results,
            total_checks=len(results),
            healthy_checks=status_counts[HealthStatus.HEALTHY],
            warning_checks=status_counts[HealthStatus.WARNING],
            critical_checks=status_counts[HealthStatus.CRITICAL],
            report_timestamp=start_time,
            recommendations=recommendations
        )

        total_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(
            f"Health checks completed in {total_time:.2f}s - "
            f"Overall: {overall_status.value}, "
            f"Healthy: {status_counts[HealthStatus.HEALTHY]}/{len(results)}"
        )

        return report

    def _generate_health_recommendations(self, results: List[HealthCheckResult]) -> List[str]:
        """Generate actionable recommendations based on health check results."""
        recommendations = []

        critical_components = [r for r in results if r.status == HealthStatus.CRITICAL]
        warning_components = [r for r in results if r.status == HealthStatus.WARNING]

        if critical_components:
            recommendations.append(
                f"IMMEDIATE ACTION REQUIRED: {len(critical_components)} critical issues detected"
            )
            for comp in critical_components[:3]:
                recommendations.append(f"  - {comp.component}: {comp.message}")

        if warning_components:
            recommendations.append(
                f"ATTENTION NEEDED: {len(warning_components)} components with warnings"
            )

        # Performance recommendations
        slow_components = [r for r in results if r.response_time_ms and r.response_time_ms > 5000]
        if slow_components:
            recommendations.append(
                f"PERFORMANCE: {len(slow_components)} components responding slowly (>5s)"
            )

        if not recommendations:
            recommendations.append("System health is excellent - all components healthy")

        return recommendations


class MetricsCollector:
    """Collects and tracks system metrics."""

    def __init__(self):
        self.logger = get_logger("metrics_collector")
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}

    def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str] = None,
        timestamp: datetime = None
    ) -> None:
        """
        Record a metric value.

        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Optional labels for the metric
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        if labels is None:
            labels = {}

        metric_record = {
            "value": value,
            "labels": labels,
            "timestamp": timestamp.isoformat()
        }

        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        self.metrics[metric_name].append(metric_record)

        # Keep only last 1000 records per metric to prevent memory issues
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]

        self.logger.debug(f"Recorded metric {metric_name}={value} with labels {labels}")

    def get_recent_metrics(
        self,
        metric_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent metrics for a specific metric name.

        Args:
            metric_name: Name of the metric
            hours: Number of hours to look back

        Returns:
            List of metric records
        """
        if metric_name not in self.metrics:
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = []

        for metric in self.metrics[metric_name]:
            metric_time = datetime.fromisoformat(metric["timestamp"])
            if metric_time >= cutoff_time:
                recent_metrics.append(metric)

        return recent_metrics

    def calculate_summary_stats(
        self,
        metric_name: str,
        hours: int = 24
    ) -> Dict[str, float]:
        """
        Calculate summary statistics for a metric.

        Args:
            metric_name: Name of the metric
            hours: Number of hours to analyze

        Returns:
            Dictionary with summary statistics
        """
        recent_metrics = self.get_recent_metrics(metric_name, hours)

        if not recent_metrics:
            return {}

        values = [m["value"] for m in recent_metrics]
        values.sort()

        stats = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "median": values[len(values) // 2] if values else 0
        }

        # Calculate percentiles
        if len(values) >= 10:
            p95_idx = int(len(values) * 0.95)
            p99_idx = int(len(values) * 0.99)
            stats["p95"] = values[p95_idx]
            stats["p99"] = values[p99_idx]

        return stats


class AlertManager:
    """Simple alerting system for critical issues."""

    def __init__(self, metrics_collector: MetricsCollector = None):
        self.logger = get_logger("alert_manager")
        self.metrics = metrics_collector or MetricsCollector()
        self.alert_thresholds = {
            "attribution_rate": 0.90,  # Alert if attribution rate < 90%
            "processing_time_seconds": 300,  # Alert if processing > 5 minutes
            "error_rate": 0.05,  # Alert if error rate > 5%
            "api_response_time_ms": 10000  # Alert if API response > 10 seconds
        }

    def check_alert_conditions(self) -> List[Dict[str, Any]]:
        """
        Check for alert conditions based on recent metrics.

        Returns:
            List of active alerts
        """
        alerts = []

        for metric_name, threshold in self.alert_thresholds.items():
            stats = self.metrics.calculate_summary_stats(metric_name, hours=1)

            if not stats:
                continue

            # Check different alert conditions
            if metric_name == "attribution_rate" and stats.get("min", 1.0) < threshold:
                alerts.append({
                    "type": "low_attribution_rate",
                    "metric": metric_name,
                    "current_value": stats["min"],
                    "threshold": threshold,
                    "severity": "critical",
                    "message": f"Attribution rate dropped to {stats['min']:.1%} (threshold: {threshold:.1%})"
                })

            elif metric_name == "processing_time_seconds" and stats.get("max", 0) > threshold:
                alerts.append({
                    "type": "slow_processing",
                    "metric": metric_name,
                    "current_value": stats["max"],
                    "threshold": threshold,
                    "severity": "warning",
                    "message": f"Processing time reached {stats['max']:.1f}s (threshold: {threshold}s)"
                })

            elif metric_name == "error_rate" and stats.get("mean", 0) > threshold:
                alerts.append({
                    "type": "high_error_rate",
                    "metric": metric_name,
                    "current_value": stats["mean"],
                    "threshold": threshold,
                    "severity": "critical",
                    "message": f"Error rate is {stats['mean']:.1%} (threshold: {threshold:.1%})"
                })

            elif metric_name == "api_response_time_ms" and stats.get("p95", 0) > threshold:
                alerts.append({
                    "type": "slow_api_response",
                    "metric": metric_name,
                    "current_value": stats["p95"],
                    "threshold": threshold,
                    "severity": "warning",
                    "message": f"API response time P95: {stats['p95']:.0f}ms (threshold: {threshold}ms)"
                })

        return alerts

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Send an alert (currently just logs, can be extended for email/Slack).

        Args:
            alert: Alert dictionary

        Returns:
            True if alert was sent successfully
        """
        severity = alert.get("severity", "info")
        message = alert.get("message", "Alert triggered")

        if severity == "critical":
            self.logger.critical(f"CRITICAL ALERT: {message}")
        elif severity == "warning":
            self.logger.warning(f"WARNING ALERT: {message}")
        else:
            self.logger.info(f"INFO ALERT: {message}")

        # Record alert metric
        self.metrics.record_metric(
            "alerts_sent",
            1,
            labels={"type": alert.get("type", "unknown"), "severity": severity}
        )

        return True


class SystemMonitor:
    """Comprehensive system monitoring orchestrator."""

    def __init__(self):
        self.logger = get_logger("system_monitor")
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager(self.metrics_collector)

        # Register built-in health checks
        self._register_builtin_checks()

    def _register_builtin_checks(self):
        """Register built-in system health checks."""
        from ..storage.bigquery_client import BigQuerySchemaManager
        from ..ingestion.cursor_client import CursorClient
        from ..ingestion.anthropic_client import AnthropicClient
        from ..ingestion.sheets_client import GoogleSheetsClient
        from ..processing.attribution import UserAttributionEngine

        try:
            # BigQuery health check
            bq_manager = BigQuerySchemaManager()
            self.health_checker.register_check("bigquery", bq_manager.health_check)

            # Cursor API health check
            if config.cursor_api_key:
                cursor_client = CursorClient()
                self.health_checker.register_check("cursor_api", cursor_client.health_check)

            # Anthropic API health check
            if config.anthropic_api_key:
                anthropic_client = AnthropicClient()
                self.health_checker.register_check("anthropic_api", anthropic_client.health_check)

            # Google Sheets health check
            if config.sheets_id:
                sheets_client = GoogleSheetsClient()
                self.health_checker.register_check("google_sheets", sheets_client.health_check)

                # Attribution system health check
                attribution_engine = UserAttributionEngine(sheets_client)
                self.health_checker.register_check("attribution_system", attribution_engine.health_check)

        except Exception as e:
            self.logger.warning(f"Could not register some health checks: {e}")

    def run_system_health_check(self) -> SystemHealthReport:
        """
        Run comprehensive system health check.

        Returns:
            SystemHealthReport with all component statuses
        """
        self.logger.info("Starting comprehensive system health check")

        # Run all health checks
        health_report = self.health_checker.run_all_checks()

        # Record metrics
        self.metrics_collector.record_metric(
            "health_check_duration_ms",
            (datetime.now() - health_report.report_timestamp).total_seconds() * 1000,
            labels={"overall_status": health_report.overall_status.value}
        )

        self.metrics_collector.record_metric(
            "healthy_components",
            health_report.healthy_checks
        )

        self.metrics_collector.record_metric(
            "critical_components",
            health_report.critical_checks
        )

        # Check for alerts
        alerts = self.alert_manager.check_alert_conditions()
        for alert in alerts:
            self.alert_manager.send_alert(alert)

        return health_report

    def record_pipeline_metrics(
        self,
        pipeline_result: Dict[str, Any]
    ) -> None:
        """
        Record metrics from a pipeline execution.

        Args:
            pipeline_result: Result dictionary from pipeline execution
        """
        # Record processing time
        processing_time = pipeline_result.get("processing_time_seconds", 0)
        self.metrics_collector.record_metric(
            "processing_time_seconds",
            processing_time,
            labels={"pipeline": "data_ingestion"}
        )

        # Record record counts
        if "transformation_stats" in pipeline_result:
            stats = pipeline_result["transformation_stats"]

            self.metrics_collector.record_metric(
                "records_processed",
                stats.get("total_output", 0),
                labels={"stage": "transformation"}
            )

            self.metrics_collector.record_metric(
                "records_input",
                stats.get("total_input", 0),
                labels={"stage": "ingestion"}
            )

            # Calculate and record error rate
            total_input = stats.get("total_input", 0)
            total_output = stats.get("total_output", 0)
            if total_input > 0:
                error_rate = 1 - (total_output / total_input)
                self.metrics_collector.record_metric(
                    "error_rate",
                    error_rate,
                    labels={"pipeline": "transformation"}
                )

        # Record attribution metrics if available
        if "attribution_report" in pipeline_result:
            attribution = pipeline_result["attribution_report"]

            self.metrics_collector.record_metric(
                "attribution_rate",
                attribution.get("attribution_rate", 0),
                labels={"system": "attribution"}
            )

            self.metrics_collector.record_metric(
                "unmapped_api_keys",
                len(attribution.get("unmapped_api_keys", [])),
                labels={"system": "attribution"}
            )

    def generate_monitoring_summary(self) -> str:
        """Generate human-readable monitoring summary."""
        summary = []
        summary.append("System Monitoring Summary")
        summary.append("=" * 40)
        summary.append(f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("")

        # Health status
        health_report = self.run_system_health_check()
        summary.append(f"Overall Health: {health_report.overall_status.value.upper()}")
        summary.append(f"Components: {health_report.healthy_checks}/{health_report.total_checks} healthy")
        summary.append("")

        # Recent metrics
        key_metrics = ["processing_time_seconds", "attribution_rate", "error_rate"]
        summary.append("Recent Metrics (24h):")

        for metric in key_metrics:
            stats = self.metrics_collector.calculate_summary_stats(metric)
            if stats:
                summary.append(f"  {metric.replace('_', ' ').title()}:")
                summary.append(f"    Average: {stats.get('mean', 0):.3f}")
                summary.append(f"    Range: {stats.get('min', 0):.3f} - {stats.get('max', 0):.3f}")

        # Active alerts
        alerts = self.alert_manager.check_alert_conditions()
        if alerts:
            summary.append("")
            summary.append(f"Active Alerts ({len(alerts)}):")
            for alert in alerts[:5]:
                summary.append(f"  • {alert['severity'].upper()}: {alert['message']}")

        return "\n".join(summary)

    def export_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Export metrics for external monitoring systems.

        Args:
            hours: Number of hours of metrics to export

        Returns:
            Dictionary with metrics data
        """
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "time_range_hours": hours,
            "metrics": {}
        }

        for metric_name in self.metrics_collector.metrics:
            recent_data = self.metrics_collector.get_recent_metrics(metric_name, hours)
            stats = self.metrics_collector.calculate_summary_stats(metric_name, hours)

            export_data["metrics"][metric_name] = {
                "recent_values": recent_data,
                "summary_stats": stats
            }

        return export_data