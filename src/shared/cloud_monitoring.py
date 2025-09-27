"""Google Cloud Monitoring integration for AI Usage Analytics Dashboard."""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from google.cloud import monitoring_v3
from google.cloud.monitoring_v3 import TimeSeries, Point, TimeInterval
from google.api_core.exceptions import GoogleAPIError
import google.protobuf.timestamp_pb2 as timestamp_pb2

from .logging_setup import get_logger
from .config import config

logger = get_logger(__name__)


class MetricType(Enum):
    """Supported custom metric types."""
    PIPELINE_HEALTH = "custom.googleapis.com/pipeline/health_score"
    API_RESPONSE_TIME = "custom.googleapis.com/api/response_time"
    BIGQUERY_LOAD_TIME = "custom.googleapis.com/bigquery/load_time"
    DATA_FRESHNESS = "custom.googleapis.com/data/freshness_hours"
    RECORDS_PROCESSED = "custom.googleapis.com/pipeline/records_processed"
    ERROR_RATE = "custom.googleapis.com/pipeline/error_rate"
    ATTRIBUTION_COMPLETENESS = "custom.googleapis.com/data/attribution_completeness"
    COST_VARIANCE = "custom.googleapis.com/data/cost_variance"


@dataclass
class MetricPoint:
    """Single metric data point."""
    value: Union[int, float]
    timestamp: Optional[datetime] = None
    labels: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.labels is None:
            self.labels = {}


class CloudMonitoringClient:
    """Google Cloud Monitoring client for custom metrics."""

    def __init__(self):
        """Initialize Cloud Monitoring client."""
        self.project_id = config.project_id
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{self.project_id}"

        # Cache for metric descriptors to avoid recreation
        self._metric_descriptors_created = set()

        logger.info("Initialized Cloud Monitoring client", extra={
            "project_id": self.project_id
        })

    def _create_metric_descriptor(self, metric_type: MetricType, description: str,
                                unit: str = "1", value_type: str = "DOUBLE") -> None:
        """Create metric descriptor if it doesn't exist."""
        if metric_type.value in self._metric_descriptors_created:
            return

        try:
            descriptor = monitoring_v3.MetricDescriptor()
            descriptor.type = metric_type.value
            descriptor.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.GAUGE
            descriptor.value_type = getattr(monitoring_v3.MetricDescriptor.ValueType, value_type)
            descriptor.description = description
            descriptor.unit = unit
            descriptor.display_name = metric_type.name.replace('_', ' ').title()

            # Add common labels
            labels = [
                monitoring_v3.LabelDescriptor(
                    key="environment",
                    value_type=monitoring_v3.LabelDescriptor.ValueType.STRING,
                    description="Environment (dev/staging/prod)"
                ),
                monitoring_v3.LabelDescriptor(
                    key="component",
                    value_type=monitoring_v3.LabelDescriptor.ValueType.STRING,
                    description="Component name"
                )
            ]

            # Add metric-specific labels
            if metric_type == MetricType.API_RESPONSE_TIME:
                labels.append(monitoring_v3.LabelDescriptor(
                    key="api_platform",
                    value_type=monitoring_v3.LabelDescriptor.ValueType.STRING,
                    description="API platform (cursor/anthropic/sheets)"
                ))
            elif metric_type in [MetricType.RECORDS_PROCESSED, MetricType.ERROR_RATE]:
                labels.append(monitoring_v3.LabelDescriptor(
                    key="platform",
                    value_type=monitoring_v3.LabelDescriptor.ValueType.STRING,
                    description="Data platform"
                ))

            descriptor.labels.extend(labels)

            self.client.create_metric_descriptor(
                name=self.project_name,
                metric_descriptor=descriptor
            )

            self._metric_descriptors_created.add(metric_type.value)
            logger.info("Created metric descriptor", extra={
                "metric_type": metric_type.value,
                "description": description
            })

        except GoogleAPIError as e:
            if "already exists" in str(e).lower():
                self._metric_descriptors_created.add(metric_type.value)
                logger.debug("Metric descriptor already exists", extra={
                    "metric_type": metric_type.value
                })
            else:
                logger.error("Failed to create metric descriptor", extra={
                    "metric_type": metric_type.value,
                    "error": str(e)
                })
                raise

    def _create_time_series(self, metric_type: MetricType, point: MetricPoint) -> TimeSeries:
        """Create a time series object for the metric."""
        series = TimeSeries()
        series.metric.type = metric_type.value

        # Add default labels
        series.metric.labels["environment"] = config.env
        series.metric.labels["component"] = "pipeline"

        # Add custom labels
        for key, value in point.labels.items():
            series.metric.labels[key] = str(value)

        # Set resource (generic_node for custom metrics)
        series.resource.type = "generic_node"
        series.resource.labels["location"] = "global"
        series.resource.labels["namespace"] = "ai-usage-analytics"
        series.resource.labels["node_id"] = f"{config.env}-pipeline"

        # Create time interval
        now = timestamp_pb2.Timestamp()
        now.FromDatetime(point.timestamp)

        interval = TimeInterval()
        interval.end_time = now

        # Create point
        metric_point = Point()
        metric_point.value.double_value = float(point.value)
        metric_point.interval = interval

        series.points = [metric_point]
        return series

    def record_pipeline_health(self, success_rate: float, job_name: str = "daily_job") -> None:
        """Record pipeline health score (0-100)."""
        self._create_metric_descriptor(
            MetricType.PIPELINE_HEALTH,
            "Pipeline job success rate percentage",
            "%"
        )

        point = MetricPoint(
            value=success_rate,
            labels={"job_name": job_name}
        )

        self._write_time_series(MetricType.PIPELINE_HEALTH, point)

        logger.info("Recorded pipeline health metric", extra={
            "success_rate": success_rate,
            "job_name": job_name
        })

    def record_api_response_time(self, platform: str, response_time_ms: float,
                               endpoint: str = "default") -> None:
        """Record API response time in milliseconds."""
        self._create_metric_descriptor(
            MetricType.API_RESPONSE_TIME,
            "API response time in milliseconds",
            "ms"
        )

        point = MetricPoint(
            value=response_time_ms,
            labels={
                "api_platform": platform,
                "endpoint": endpoint
            }
        )

        self._write_time_series(MetricType.API_RESPONSE_TIME, point)

        logger.debug("Recorded API response time", extra={
            "platform": platform,
            "response_time_ms": response_time_ms,
            "endpoint": endpoint
        })

    def record_bigquery_load_time(self, table_name: str, load_time_seconds: float,
                                 record_count: int = 0) -> None:
        """Record BigQuery data load time in seconds."""
        self._create_metric_descriptor(
            MetricType.BIGQUERY_LOAD_TIME,
            "BigQuery table load time in seconds",
            "s"
        )

        point = MetricPoint(
            value=load_time_seconds,
            labels={
                "table_name": table_name,
                "record_count": str(record_count)
            }
        )

        self._write_time_series(MetricType.BIGQUERY_LOAD_TIME, point)

        logger.info("Recorded BigQuery load time", extra={
            "table_name": table_name,
            "load_time_seconds": load_time_seconds,
            "record_count": record_count
        })

    def record_data_freshness(self, hours_since_update: float, data_source: str) -> None:
        """Record data freshness in hours since last update."""
        self._create_metric_descriptor(
            MetricType.DATA_FRESHNESS,
            "Hours since data was last updated",
            "h"
        )

        point = MetricPoint(
            value=hours_since_update,
            labels={"data_source": data_source}
        )

        self._write_time_series(MetricType.DATA_FRESHNESS, point)

        logger.info("Recorded data freshness metric", extra={
            "hours_since_update": hours_since_update,
            "data_source": data_source
        })

    def record_records_processed(self, platform: str, record_count: int,
                               processing_stage: str = "ingestion") -> None:
        """Record number of records processed."""
        self._create_metric_descriptor(
            MetricType.RECORDS_PROCESSED,
            "Number of records processed",
            "1",
            "INT64"
        )

        point = MetricPoint(
            value=record_count,
            labels={
                "platform": platform,
                "processing_stage": processing_stage
            }
        )

        self._write_time_series(MetricType.RECORDS_PROCESSED, point)

        logger.info("Recorded records processed", extra={
            "platform": platform,
            "record_count": record_count,
            "processing_stage": processing_stage
        })

    def record_error_rate(self, platform: str, error_rate: float,
                         error_type: str = "general") -> None:
        """Record error rate as percentage (0-100)."""
        self._create_metric_descriptor(
            MetricType.ERROR_RATE,
            "Error rate percentage",
            "%"
        )

        point = MetricPoint(
            value=error_rate,
            labels={
                "platform": platform,
                "error_type": error_type
            }
        )

        self._write_time_series(MetricType.ERROR_RATE, point)

        logger.info("Recorded error rate", extra={
            "platform": platform,
            "error_rate": error_rate,
            "error_type": error_type
        })

    def record_attribution_completeness(self, completeness_percentage: float,
                                       platform: str = "all") -> None:
        """Record user attribution completeness percentage."""
        self._create_metric_descriptor(
            MetricType.ATTRIBUTION_COMPLETENESS,
            "User attribution completeness percentage",
            "%"
        )

        point = MetricPoint(
            value=completeness_percentage,
            labels={"platform": platform}
        )

        self._write_time_series(MetricType.ATTRIBUTION_COMPLETENESS, point)

        logger.info("Recorded attribution completeness", extra={
            "completeness_percentage": completeness_percentage,
            "platform": platform
        })

    def record_cost_variance(self, variance_percentage: float, platform: str,
                            time_period: str = "daily") -> None:
        """Record cost variance from expected values."""
        self._create_metric_descriptor(
            MetricType.COST_VARIANCE,
            "Cost variance from expected percentage",
            "%"
        )

        point = MetricPoint(
            value=variance_percentage,
            labels={
                "platform": platform,
                "time_period": time_period
            }
        )

        self._write_time_series(MetricType.COST_VARIANCE, point)

        logger.info("Recorded cost variance", extra={
            "variance_percentage": variance_percentage,
            "platform": platform,
            "time_period": time_period
        })

    def _write_time_series(self, metric_type: MetricType, point: MetricPoint) -> None:
        """Write time series data to Cloud Monitoring."""
        try:
            series = self._create_time_series(metric_type, point)
            self.client.create_time_series(
                name=self.project_name,
                time_series=[series]
            )
        except GoogleAPIError as e:
            logger.error("Failed to write time series", extra={
                "metric_type": metric_type.value,
                "error": str(e)
            })
            raise

    def get_metric_values(self, metric_type: MetricType, hours_back: int = 24,
                         labels_filter: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Retrieve metric values from Cloud Monitoring."""
        try:
            # Build filter
            filter_str = f'metric.type="{metric_type.value}"'
            if labels_filter:
                for key, value in labels_filter.items():
                    filter_str += f' AND metric.label.{key}="{value}"'

            # Create time interval
            now = datetime.utcnow()
            end_time = timestamp_pb2.Timestamp()
            end_time.FromDatetime(now)

            start_time = timestamp_pb2.Timestamp()
            start_time.FromDatetime(now - timedelta(hours=hours_back))

            interval = TimeInterval()
            interval.start_time = start_time
            interval.end_time = end_time

            # Query metrics
            results = self.client.list_time_series(
                request={
                    "name": self.project_name,
                    "filter": filter_str,
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )

            # Process results
            metric_values = []
            for result in results:
                for point in result.points:
                    metric_values.append({
                        "timestamp": point.interval.end_time.ToDatetime(),
                        "value": point.value.double_value or point.value.int64_value,
                        "labels": dict(result.metric.labels)
                    })

            logger.debug("Retrieved metric values", extra={
                "metric_type": metric_type.value,
                "count": len(metric_values),
                "hours_back": hours_back
            })

            return metric_values

        except GoogleAPIError as e:
            logger.error("Failed to retrieve metric values", extra={
                "metric_type": metric_type.value,
                "error": str(e)
            })
            return []

    def create_alert_policy(self, policy_config: Dict[str, Any]) -> str:
        """Create alert policy for monitoring metrics."""
        try:
            alert_client = monitoring_v3.AlertPolicyServiceClient()

            policy = monitoring_v3.AlertPolicy()
            policy.display_name = policy_config["name"]
            policy.enabled = True

            # Create condition
            condition = monitoring_v3.AlertPolicy.Condition()
            condition.display_name = policy_config["condition_name"]

            # Set threshold condition
            threshold = monitoring_v3.AlertPolicy.Condition.MetricThreshold()
            threshold.filter = policy_config["filter"]
            threshold.comparison = getattr(
                monitoring_v3.ComparisonType,
                policy_config["comparison"]
            )
            threshold.threshold_value = policy_config["threshold"]
            threshold.duration.seconds = policy_config.get("duration_seconds", 300)

            condition.condition_threshold = threshold
            policy.conditions = [condition]

            # Set notification channels if provided
            if "notification_channels" in policy_config:
                policy.notification_channels = policy_config["notification_channels"]

            # Create the policy
            created_policy = alert_client.create_alert_policy(
                name=self.project_name,
                alert_policy=policy
            )

            logger.info("Created alert policy", extra={
                "policy_name": policy_config["name"],
                "policy_id": created_policy.name
            })

            return created_policy.name

        except GoogleAPIError as e:
            logger.error("Failed to create alert policy", extra={
                "policy_name": policy_config.get("name", "unknown"),
                "error": str(e)
            })
            raise


# Global instance - lazy initialization
cloud_monitoring = None

def get_cloud_monitoring():
    """Get or create cloud monitoring client instance."""
    global cloud_monitoring
    if cloud_monitoring is None:
        cloud_monitoring = CloudMonitoringClient()
    return cloud_monitoring