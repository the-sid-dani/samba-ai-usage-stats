"""Business metrics monitoring for AI Usage Analytics Dashboard."""

import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from .logging_setup import get_logger, RequestContextLogger
from .cloud_monitoring import get_cloud_monitoring
from .config import config

logger = get_logger(__name__)


class MetricPeriod(Enum):
    """Time periods for metric calculations."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class BusinessMetricResult:
    """Result of a business metric calculation."""
    metric_name: str
    value: float
    target_value: Optional[float] = None
    variance_percentage: Optional[float] = None
    status: str = "normal"  # normal, warning, critical
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CostVarianceAnalysis:
    """Cost variance analysis results."""
    platform: str
    current_cost: float
    baseline_cost: float
    variance_percentage: float
    is_anomaly: bool
    trend_direction: str  # "increasing", "decreasing", "stable"
    analysis_period: str


class BusinessMetricsCollector:
    """Collects and analyzes business metrics for monitoring."""

    def __init__(self):
        """Initialize business metrics collector."""
        self.project_id = config.project_id
        self.dataset_id = config.dataset
        self.client = bigquery.Client(project=self.project_id)
        self.context_logger = RequestContextLogger("business_metrics")

        logger.info("Initialized Business Metrics Collector", extra={
            "project_id": self.project_id,
            "dataset": self.dataset_id
        })

    def collect_daily_metrics(self, target_date: date = None) -> Dict[str, BusinessMetricResult]:
        """Collect all daily business metrics."""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        self.context_logger.log_operation_start("collect_daily_metrics", target_date=str(target_date))

        metrics = {}

        try:
            # Records processed metrics
            metrics.update(self._get_records_processed_metrics(target_date))

            # Cost accuracy metrics
            metrics.update(self._get_cost_accuracy_metrics(target_date))

            # Attribution completeness metrics
            metrics.update(self._get_attribution_completeness_metrics(target_date))

            # Cross-platform consistency metrics
            metrics.update(self._get_consistency_metrics(target_date))

            # Record metrics to Cloud Monitoring
            self._record_business_metrics_to_cloud_monitoring(metrics)

            self.context_logger.log_operation_complete(
                "collect_daily_metrics",
                metrics_collected=len(metrics),
                target_date=str(target_date)
            )

        except Exception as e:
            self.context_logger.log_operation_error("collect_daily_metrics", error=e)
            raise

        return metrics

    def _get_records_processed_metrics(self, target_date: date) -> Dict[str, BusinessMetricResult]:
        """Get records processed metrics by platform."""
        metrics = {}

        try:
            query = f"""
            SELECT
                platform,
                COUNT(*) as record_count,
                COUNT(DISTINCT user_email) as unique_users
            FROM `{self.project_id}.{self.dataset_id}.fct_usage_daily`
            WHERE DATE(usage_date) = '{target_date}'
            GROUP BY platform
            """

            query_job = self.client.query(query)
            results = query_job.result()

            total_records = 0
            total_users = 0

            for row in results:
                platform = row.platform
                record_count = row.record_count
                unique_users = row.unique_users

                total_records += record_count
                total_users += unique_users

                # Record platform-specific metrics
                monitoring_client = get_cloud_monitoring()
                monitoring_client.record_records_processed(platform, record_count, "daily_processing")

                metrics[f"records_processed_{platform}"] = BusinessMetricResult(
                    metric_name=f"records_processed_{platform}",
                    value=record_count,
                    metadata={"unique_users": unique_users, "platform": platform}
                )

            # Total records metric
            cloud_monitoring.record_records_processed("all_platforms", total_records, "daily_processing")

            metrics["records_processed_total"] = BusinessMetricResult(
                metric_name="records_processed_total",
                value=total_records,
                target_value=100.0,  # Minimum expected daily records
                metadata={"unique_users_total": total_users}
            )

            # Calculate variance if we have historical data
            if total_records > 0:
                variance = self._calculate_records_variance(target_date, total_records)
                if variance is not None:
                    metrics["records_processed_total"].variance_percentage = variance

        except Exception as e:
            logger.error("Failed to get records processed metrics", extra={"error": str(e)})
            raise

        return metrics

    def _get_cost_accuracy_metrics(self, target_date: date) -> Dict[str, BusinessMetricResult]:
        """Get cost data accuracy variance metrics."""
        metrics = {}

        try:
            # Get daily cost by platform
            query = f"""
            SELECT
                platform,
                SUM(cost_usd) as daily_cost,
                COUNT(*) as cost_records
            FROM `{self.project_id}.{self.dataset_id}.fct_cost_daily`
            WHERE DATE(cost_date) = '{target_date}'
            GROUP BY platform
            """

            query_job = self.client.query(query)
            results = query_job.result()

            for row in results:
                platform = row.platform
                daily_cost = float(row.daily_cost)
                cost_records = row.cost_records

                # Calculate cost variance
                variance_analysis = self._calculate_cost_variance(platform, target_date, daily_cost)

                # Record cost variance to Cloud Monitoring
                cloud_monitoring.record_cost_variance(
                    variance_analysis.variance_percentage,
                    platform,
                    "daily"
                )

                metrics[f"cost_variance_{platform}"] = BusinessMetricResult(
                    metric_name=f"cost_variance_{platform}",
                    value=variance_analysis.variance_percentage,
                    target_value=20.0,  # Alert if >20% variance
                    variance_percentage=variance_analysis.variance_percentage,
                    status="warning" if variance_analysis.is_anomaly else "normal",
                    metadata={
                        "current_cost": variance_analysis.current_cost,
                        "baseline_cost": variance_analysis.baseline_cost,
                        "trend": variance_analysis.trend_direction,
                        "cost_records": cost_records
                    }
                )

        except Exception as e:
            logger.error("Failed to get cost accuracy metrics", extra={"error": str(e)})
            raise

        return metrics

    def _get_attribution_completeness_metrics(self, target_date: date) -> Dict[str, BusinessMetricResult]:
        """Get user attribution completeness metrics."""
        metrics = {}

        try:
            query = f"""
            SELECT
                platform,
                COUNT(*) as total_records,
                COUNT(user_email) as attributed_records,
                SAFE_DIVIDE(COUNT(user_email), COUNT(*)) * 100 as attribution_rate
            FROM `{self.project_id}.{self.dataset_id}.fct_usage_daily`
            WHERE DATE(usage_date) = '{target_date}'
            GROUP BY platform
            """

            query_job = self.client.query(query)
            results = query_job.result()

            total_records = 0
            total_attributed = 0

            for row in results:
                platform = row.platform
                attribution_rate = float(row.attribution_rate or 0.0)
                total_platform_records = row.total_records
                attributed_records = row.attributed_records

                total_records += total_platform_records
                total_attributed += attributed_records

                # Record to Cloud Monitoring
                cloud_monitoring.record_attribution_completeness(attribution_rate, platform)

                # Determine status
                status = "normal"
                if attribution_rate < 95.0:
                    status = "warning"
                if attribution_rate < 85.0:
                    status = "critical"

                metrics[f"attribution_completeness_{platform}"] = BusinessMetricResult(
                    metric_name=f"attribution_completeness_{platform}",
                    value=attribution_rate,
                    target_value=95.0,
                    status=status,
                    metadata={
                        "total_records": total_platform_records,
                        "attributed_records": attributed_records,
                        "platform": platform
                    }
                )

            # Overall attribution rate
            overall_rate = (total_attributed / max(1, total_records)) * 100
            cloud_monitoring.record_attribution_completeness(overall_rate, "all_platforms")

            metrics["attribution_completeness_overall"] = BusinessMetricResult(
                metric_name="attribution_completeness_overall",
                value=overall_rate,
                target_value=95.0,
                status="warning" if overall_rate < 95.0 else "normal",
                metadata={
                    "total_records": total_records,
                    "attributed_records": total_attributed
                }
            )

        except Exception as e:
            logger.error("Failed to get attribution completeness metrics", extra={"error": str(e)})
            raise

        return metrics

    def _get_consistency_metrics(self, target_date: date) -> Dict[str, BusinessMetricResult]:
        """Get cross-platform data consistency metrics."""
        metrics = {}

        try:
            # Check for data consistency across platforms
            query = f"""
            WITH platform_stats AS (
                SELECT
                    platform,
                    COUNT(*) as record_count,
                    AVG(CAST(JSON_EXTRACT_SCALAR(usage_metadata, '$.total_interactions') AS INT64)) as avg_interactions
                FROM `{self.project_id}.{self.dataset_id}.fct_usage_daily`
                WHERE DATE(usage_date) = '{target_date}'
                GROUP BY platform
            )
            SELECT
                platform,
                record_count,
                avg_interactions,
                STDDEV(avg_interactions) OVER() as interaction_stddev
            FROM platform_stats
            """

            query_job = self.client.query(query)
            results = query_job.result()

            consistency_scores = []
            platform_data = []

            for row in results:
                platform_data.append({
                    "platform": row.platform,
                    "record_count": row.record_count,
                    "avg_interactions": float(row.avg_interactions or 0.0),
                    "stddev": float(row.interaction_stddev or 0.0)
                })

            # Calculate consistency score (lower stddev = higher consistency)
            if platform_data:
                avg_stddev = statistics.mean([p["stddev"] for p in platform_data if p["stddev"] > 0])
                consistency_score = max(0, 100 - (avg_stddev / 10))  # Normalize to 0-100 scale

                metrics["cross_platform_consistency"] = BusinessMetricResult(
                    metric_name="cross_platform_consistency",
                    value=consistency_score,
                    target_value=80.0,
                    status="warning" if consistency_score < 80.0 else "normal",
                    metadata={
                        "platform_count": len(platform_data),
                        "avg_stddev": avg_stddev,
                        "platform_data": platform_data
                    }
                )

        except Exception as e:
            logger.error("Failed to get consistency metrics", extra={"error": str(e)})
            # Don't raise - consistency metrics are nice-to-have

        return metrics

    def _calculate_records_variance(self, target_date: date, current_count: int) -> Optional[float]:
        """Calculate variance from 7-day average for records processed."""
        try:
            start_date = target_date - timedelta(days=7)
            query = f"""
            SELECT AVG(daily_count) as avg_count
            FROM (
                SELECT
                    DATE(usage_date) as date,
                    COUNT(*) as daily_count
                FROM `{self.project_id}.{self.dataset_id}.fct_usage_daily`
                WHERE DATE(usage_date) BETWEEN '{start_date}' AND '{target_date - timedelta(days=1)}'
                GROUP BY DATE(usage_date)
            )
            """

            query_job = self.client.query(query)
            results = list(query_job.result())

            if results and results[0].avg_count:
                baseline = float(results[0].avg_count)
                variance = ((current_count - baseline) / baseline) * 100
                return variance

        except Exception as e:
            logger.warning("Failed to calculate records variance", extra={"error": str(e)})

        return None

    def _calculate_cost_variance(self, platform: str, target_date: date, current_cost: float) -> CostVarianceAnalysis:
        """Calculate cost variance analysis."""
        try:
            # Get 7-day baseline
            start_date = target_date - timedelta(days=7)
            query = f"""
            SELECT
                AVG(daily_cost) as baseline_cost,
                STDDEV(daily_cost) as cost_stddev
            FROM (
                SELECT
                    DATE(cost_date) as date,
                    SUM(cost_usd) as daily_cost
                FROM `{self.project_id}.{self.dataset_id}.fct_cost_daily`
                WHERE platform = '{platform}'
                AND DATE(cost_date) BETWEEN '{start_date}' AND '{target_date - timedelta(days=1)}'
                GROUP BY DATE(cost_date)
            )
            """

            query_job = self.client.query(query)
            results = list(query_job.result())

            if results and results[0].baseline_cost:
                baseline_cost = float(results[0].baseline_cost)
                cost_stddev = float(results[0].cost_stddev or 0.0)

                variance_percentage = ((current_cost - baseline_cost) / baseline_cost) * 100
                is_anomaly = abs(variance_percentage) > 20.0  # More than 20% variance

                # Determine trend
                trend = "stable"
                if variance_percentage > 5:
                    trend = "increasing"
                elif variance_percentage < -5:
                    trend = "decreasing"

                return CostVarianceAnalysis(
                    platform=platform,
                    current_cost=current_cost,
                    baseline_cost=baseline_cost,
                    variance_percentage=variance_percentage,
                    is_anomaly=is_anomaly,
                    trend_direction=trend,
                    analysis_period="7_day_baseline"
                )

        except Exception as e:
            logger.warning(f"Failed to calculate cost variance for {platform}", extra={"error": str(e)})

        # Return default analysis if calculation fails
        return CostVarianceAnalysis(
            platform=platform,
            current_cost=current_cost,
            baseline_cost=current_cost,
            variance_percentage=0.0,
            is_anomaly=False,
            trend_direction="unknown",
            analysis_period="insufficient_data"
        )

    def _record_business_metrics_to_cloud_monitoring(self, metrics: Dict[str, BusinessMetricResult]) -> None:
        """Record business metrics to Cloud Monitoring."""
        for metric_name, metric_result in metrics.items():
            try:
                if "records_processed" in metric_name:
                    platform = metric_result.metadata.get("platform", "all") if metric_result.metadata else "all"
                    cloud_monitoring.record_records_processed(
                        platform,
                        int(metric_result.value),
                        "business_metrics"
                    )

                elif "cost_variance" in metric_name:
                    platform = metric_result.metadata.get("platform", "unknown") if metric_result.metadata else "unknown"
                    cloud_monitoring.record_cost_variance(
                        metric_result.value,
                        platform,
                        "daily"
                    )

                elif "attribution_completeness" in metric_name:
                    platform = metric_result.metadata.get("platform", "all") if metric_result.metadata else "all"
                    cloud_monitoring.record_attribution_completeness(
                        metric_result.value,
                        platform
                    )

            except Exception as e:
                logger.warning(f"Failed to record business metric to Cloud Monitoring: {metric_name}",
                             extra={"error": str(e)})

    def generate_daily_business_report(self, target_date: date = None) -> Dict[str, Any]:
        """Generate comprehensive daily business metrics report."""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        self.context_logger.log_operation_start("generate_daily_business_report")

        try:
            # Collect all metrics
            metrics = self.collect_daily_metrics(target_date)

            # Analyze overall health
            warning_metrics = [m for m in metrics.values() if m.status == "warning"]
            critical_metrics = [m for m in metrics.values() if m.status == "critical"]

            overall_status = "healthy"
            if critical_metrics:
                overall_status = "critical"
            elif warning_metrics:
                overall_status = "warning"

            # Generate report
            report = {
                "report_date": str(target_date),
                "overall_status": overall_status,
                "metrics_collected": len(metrics),
                "warning_metrics": len(warning_metrics),
                "critical_metrics": len(critical_metrics),
                "metrics": {name: {
                    "value": metric.value,
                    "target": metric.target_value,
                    "variance": metric.variance_percentage,
                    "status": metric.status,
                    "metadata": metric.metadata
                } for name, metric in metrics.items()},
                "summary": {
                    "total_records_processed": metrics.get("records_processed_total", BusinessMetricResult("", 0)).value,
                    "attribution_completeness": metrics.get("attribution_completeness_overall", BusinessMetricResult("", 0)).value,
                    "anomalies_detected": len(critical_metrics) + len(warning_metrics)
                },
                "generated_at": datetime.now().isoformat()
            }

            self.context_logger.log_operation_complete(
                "generate_daily_business_report",
                overall_status=overall_status,
                metrics_count=len(metrics),
                warnings=len(warning_metrics),
                criticals=len(critical_metrics)
            )

            return report

        except Exception as e:
            self.context_logger.log_operation_error("generate_daily_business_report", error=e)
            raise

    def get_data_freshness_hours(self, table_name: str) -> float:
        """Calculate data freshness in hours for a table."""
        try:
            query = f"""
            SELECT
                DATETIME_DIFF(CURRENT_DATETIME(), MAX(DATETIME(ingest_date)), HOUR) as hours_since_update
            FROM `{self.project_id}.{self.dataset_id}.{table_name}`
            WHERE DATE(ingest_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
            """

            query_job = self.client.query(query)
            results = list(query_job.result())

            if results and results[0].hours_since_update is not None:
                hours = float(results[0].hours_since_update)

                # Record to Cloud Monitoring
                cloud_monitoring.record_data_freshness(hours, table_name)

                return hours

        except Exception as e:
            logger.warning(f"Failed to calculate data freshness for {table_name}", extra={"error": str(e)})

        return 999.0  # Return high value if calculation fails


# Global instance - lazy initialization
business_metrics_collector = None

def get_business_metrics_collector():
    """Get or create business metrics collector instance."""
    global business_metrics_collector
    if business_metrics_collector is None:
        business_metrics_collector = BusinessMetricsCollector()
    return business_metrics_collector