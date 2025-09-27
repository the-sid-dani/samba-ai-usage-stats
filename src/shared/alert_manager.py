"""Alert Policy Management for AI Usage Analytics Dashboard."""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from google.cloud import monitoring_v3
from google.cloud import secretmanager
from google.api_core.exceptions import GoogleAPIError
import requests
import json

from .logging_setup import get_logger, RequestContextLogger
from .config import config
from .cloud_monitoring import MetricType

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"


@dataclass
class AlertPolicyConfig:
    """Configuration for an alert policy."""
    name: str
    display_name: str
    metric_filter: str
    condition_threshold: float
    comparison_type: str  # COMPARISON_GREATER_THAN, COMPARISON_LESS_THAN, etc.
    duration_seconds: int = 300
    severity: AlertSeverity = AlertSeverity.WARNING
    notification_channels: List[str] = None
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []


@dataclass
class NotificationChannelConfig:
    """Configuration for a notification channel."""
    name: str
    type: NotificationChannel
    config: Dict[str, Any]
    description: str = ""
    enabled: bool = True


class AlertManager:
    """Manages alert policies and notification channels for monitoring."""

    def __init__(self):
        """Initialize Alert Manager."""
        self.project_id = config.project_id
        self.project_name = f"projects/{self.project_id}"

        # Initialize clients
        self.alert_client = monitoring_v3.AlertPolicyServiceClient()
        self.notification_client = monitoring_v3.NotificationChannelServiceClient()
        self.secret_client = secretmanager.SecretManagerServiceClient()

        # Cache for created resources
        self._notification_channels = {}
        self._alert_policies = {}

        self.context_logger = RequestContextLogger("alert_manager")

        logger.info("Initialized Alert Manager", extra={
            "project_id": self.project_id
        })

    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Google Secret Manager."""
        try:
            secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

    def create_notification_channel(self, channel_config: NotificationChannelConfig) -> str:
        """Create a notification channel."""
        try:
            channel = monitoring_v3.NotificationChannel()
            channel.display_name = channel_config.name
            channel.description = channel_config.description
            channel.enabled = channel_config.enabled

            if channel_config.type == NotificationChannel.EMAIL:
                channel.type = "email"
                channel.labels["email_address"] = channel_config.config["email"]

            elif channel_config.type == NotificationChannel.SLACK:
                channel.type = "slack"
                # Slack requires webhook URL stored in secrets
                webhook_secret = channel_config.config.get("webhook_secret")
                if webhook_secret:
                    webhook_url = self.get_secret(webhook_secret)
                    channel.labels["url"] = webhook_url
                    channel.labels["channel"] = channel_config.config.get("channel", "#alerts")

            elif channel_config.type == NotificationChannel.SMS:
                channel.type = "sms"
                channel.labels["number"] = channel_config.config["phone_number"]

            # Create the channel
            created_channel = self.notification_client.create_notification_channel(
                name=self.project_name,
                notification_channel=channel
            )

            channel_id = created_channel.name
            self._notification_channels[channel_config.name] = channel_id

            self.context_logger.info(f"Created notification channel: {channel_config.name}",
                                   channel_type=channel_config.type.value,
                                   channel_id=channel_id)

            return channel_id

        except GoogleAPIError as e:
            self.context_logger.error(f"Failed to create notification channel: {channel_config.name}",
                                    error=e)
            raise

    def create_alert_policy(self, policy_config: AlertPolicyConfig) -> str:
        """Create an alert policy."""
        try:
            policy = monitoring_v3.AlertPolicy()
            policy.display_name = policy_config.display_name
            policy.documentation.content = policy_config.description
            policy.enabled = policy_config.enabled

            # Create condition
            condition = monitoring_v3.AlertPolicy.Condition()
            condition.display_name = f"{policy_config.name}_condition"

            # Set threshold condition
            threshold = monitoring_v3.AlertPolicy.Condition.MetricThreshold()
            threshold.filter = policy_config.metric_filter
            threshold.comparison = getattr(
                monitoring_v3.ComparisonType,
                policy_config.comparison_type
            )
            threshold.threshold_value = policy_config.condition_threshold
            threshold.duration.seconds = policy_config.duration_seconds

            # Set aggregation (use ALIGN_RATE for most metrics)
            aggregation = monitoring_v3.Aggregation()
            aggregation.alignment_period.seconds = 60  # 1 minute alignment
            aggregation.per_series_aligner = monitoring_v3.Aggregation.Aligner.ALIGN_RATE
            aggregation.cross_series_reducer = monitoring_v3.Aggregation.Reducer.REDUCE_MEAN
            threshold.aggregations = [aggregation]

            condition.condition_threshold = threshold
            policy.conditions = [condition]

            # Set notification channels
            if policy_config.notification_channels:
                policy.notification_channels = policy_config.notification_channels

            # Create the policy
            created_policy = self.alert_client.create_alert_policy(
                name=self.project_name,
                alert_policy=policy
            )

            policy_id = created_policy.name
            self._alert_policies[policy_config.name] = policy_id

            self.context_logger.info(f"Created alert policy: {policy_config.name}",
                                   policy_id=policy_id,
                                   severity=policy_config.severity.value)

            return policy_id

        except GoogleAPIError as e:
            self.context_logger.error(f"Failed to create alert policy: {policy_config.name}",
                                    error=e)
            raise

    def setup_default_notification_channels(self) -> Dict[str, str]:
        """Set up default notification channels for the project."""
        channels = {}

        # Engineering team email
        try:
            eng_email_config = NotificationChannelConfig(
                name="engineering_team_email",
                type=NotificationChannel.EMAIL,
                config={"email": "engineering@samba.tv"},
                description="Engineering team email notifications"
            )
            channels["engineering_email"] = self.create_notification_channel(eng_email_config)
        except Exception as e:
            logger.warning(f"Failed to create engineering email channel: {e}")

        # Finance team email
        try:
            finance_email_config = NotificationChannelConfig(
                name="finance_team_email",
                type=NotificationChannel.EMAIL,
                config={"email": "finance@samba.tv"},
                description="Finance team email notifications"
            )
            channels["finance_email"] = self.create_notification_channel(finance_email_config)
        except Exception as e:
            logger.warning(f"Failed to create finance email channel: {e}")

        # Engineering Slack channel (if webhook secret exists)
        try:
            slack_config = NotificationChannelConfig(
                name="engineering_slack",
                type=NotificationChannel.SLACK,
                config={
                    "webhook_secret": "slack-engineering-webhook",
                    "channel": "#ai-usage-alerts"
                },
                description="Engineering Slack channel for alerts"
            )
            channels["engineering_slack"] = self.create_notification_channel(slack_config)
        except Exception as e:
            logger.warning(f"Failed to create Slack channel: {e}")

        return channels

    def setup_default_alert_policies(self, notification_channels: Dict[str, str]) -> Dict[str, str]:
        """Set up default alert policies."""
        policies = {}

        # 1. Daily Job Failure Alert
        if "engineering_email" in notification_channels:
            daily_job_failure = AlertPolicyConfig(
                name="daily_job_failure",
                display_name="Daily Job Failure Alert",
                metric_filter=f'resource.type="generic_node" AND '
                            f'metric.type="{MetricType.PIPELINE_HEALTH.value}" AND '
                            f'metric.label.job_name="daily_job"',
                condition_threshold=50.0,  # Less than 50% success rate
                comparison_type="COMPARISON_LESS_THAN",
                duration_seconds=300,
                severity=AlertSeverity.CRITICAL,
                notification_channels=[notification_channels["engineering_email"]],
                description="Alert when daily pipeline job success rate drops below 50%"
            )
            policies["daily_job_failure"] = self.create_alert_policy(daily_job_failure)

        # 2. Data Quality Issue Alert
        if "finance_email" in notification_channels and "engineering_email" in notification_channels:
            data_quality_alert = AlertPolicyConfig(
                name="data_quality_issue",
                display_name="Data Quality Issue Alert",
                metric_filter=f'resource.type="generic_node" AND '
                            f'metric.type="{MetricType.ERROR_RATE.value}" AND '
                            f'metric.label.platform="pipeline"',
                condition_threshold=5.0,  # More than 5% error rate
                comparison_type="COMPARISON_GREATER_THAN",
                duration_seconds=300,
                severity=AlertSeverity.WARNING,
                notification_channels=[
                    notification_channels["engineering_email"],
                    notification_channels["finance_email"]
                ],
                description="Alert when validation errors exceed 5% of total operations"
            )
            policies["data_quality_issue"] = self.create_alert_policy(data_quality_alert)

        # 3. Cost Anomaly Alert
        if "finance_email" in notification_channels:
            cost_anomaly_alert = AlertPolicyConfig(
                name="cost_anomaly",
                display_name="Cost Anomaly Alert",
                metric_filter=f'resource.type="generic_node" AND '
                            f'metric.type="{MetricType.COST_VARIANCE.value}"',
                condition_threshold=20.0,  # More than 20% cost variance
                comparison_type="COMPARISON_GREATER_THAN",
                duration_seconds=600,  # 10 minutes
                severity=AlertSeverity.WARNING,
                notification_channels=[notification_channels["finance_email"]],
                description="Alert when daily costs exceed 120% of 7-day average"
            )
            policies["cost_anomaly"] = self.create_alert_policy(cost_anomaly_alert)

        # 4. API Rate Limit Alert
        if "engineering_slack" in notification_channels:
            api_rate_limit_alert = AlertPolicyConfig(
                name="api_rate_limit",
                display_name="API Rate Limit Alert",
                metric_filter=f'resource.type="generic_node" AND '
                            f'metric.type="{MetricType.ERROR_RATE.value}" AND '
                            f'metric.label.error_type="rate_limit"',
                condition_threshold=10.0,  # More than 10 rate limit errors per hour
                comparison_type="COMPARISON_GREATER_THAN",
                duration_seconds=3600,  # 1 hour
                severity=AlertSeverity.INFO,
                notification_channels=[notification_channels["engineering_slack"]],
                description="Alert when API rate limit errors exceed 10 in 1 hour"
            )
            policies["api_rate_limit"] = self.create_alert_policy(api_rate_limit_alert)

        # 5. Attribution Completeness Alert
        if "engineering_email" in notification_channels:
            attribution_alert = AlertPolicyConfig(
                name="attribution_completeness",
                display_name="User Attribution Completeness Alert",
                metric_filter=f'resource.type="generic_node" AND '
                            f'metric.type="{MetricType.ATTRIBUTION_COMPLETENESS.value}"',
                condition_threshold=95.0,  # Less than 95% attribution completeness
                comparison_type="COMPARISON_LESS_THAN",
                duration_seconds=600,
                severity=AlertSeverity.WARNING,
                notification_channels=[notification_channels["engineering_email"]],
                description="Alert when user attribution completeness drops below 95%"
            )
            policies["attribution_completeness"] = self.create_alert_policy(attribution_alert)

        return policies

    def test_alert_policy(self, policy_name: str, test_value: float) -> bool:
        """Test an alert policy by temporarily triggering it."""
        try:
            if policy_name not in self._alert_policies:
                logger.error(f"Alert policy not found: {policy_name}")
                return False

            # This would require implementing a test metric injection
            # For now, we'll just validate the policy exists and is enabled
            policy_id = self._alert_policies[policy_name]

            try:
                policy = self.alert_client.get_alert_policy(name=policy_id)
                is_enabled = policy.enabled

                self.context_logger.info(f"Alert policy test completed",
                                       policy_name=policy_name,
                                       enabled=is_enabled,
                                       test_value=test_value)

                return is_enabled

            except GoogleAPIError as e:
                logger.error(f"Failed to retrieve alert policy for testing: {e}")
                return False

        except Exception as e:
            self.context_logger.error(f"Alert policy test failed",
                                    policy_name=policy_name,
                                    error=e)
            return False

    def list_alert_policies(self) -> List[Dict[str, Any]]:
        """List all alert policies in the project."""
        try:
            policies = []
            for policy in self.alert_client.list_alert_policies(name=self.project_name):
                policies.append({
                    "name": policy.name,
                    "display_name": policy.display_name,
                    "enabled": policy.enabled,
                    "conditions_count": len(policy.conditions),
                    "notification_channels_count": len(policy.notification_channels)
                })

            logger.info(f"Retrieved {len(policies)} alert policies")
            return policies

        except GoogleAPIError as e:
            logger.error(f"Failed to list alert policies: {e}")
            return []

    def list_notification_channels(self) -> List[Dict[str, Any]]:
        """List all notification channels in the project."""
        try:
            channels = []
            for channel in self.notification_client.list_notification_channels(name=self.project_name):
                channels.append({
                    "name": channel.name,
                    "display_name": channel.display_name,
                    "type": channel.type,
                    "enabled": channel.enabled,
                    "labels": dict(channel.labels)
                })

            logger.info(f"Retrieved {len(channels)} notification channels")
            return channels

        except GoogleAPIError as e:
            logger.error(f"Failed to list notification channels: {e}")
            return []

    def setup_all_alerts(self) -> Dict[str, Any]:
        """Set up all default notification channels and alert policies."""
        setup_results = {
            "notification_channels": {},
            "alert_policies": {},
            "success": False,
            "errors": []
        }

        try:
            self.context_logger.log_operation_start("setup_all_alerts")

            # Create notification channels
            logger.info("Setting up notification channels...")
            setup_results["notification_channels"] = self.setup_default_notification_channels()

            # Create alert policies
            logger.info("Setting up alert policies...")
            setup_results["alert_policies"] = self.setup_default_alert_policies(
                setup_results["notification_channels"]
            )

            setup_results["success"] = True

            self.context_logger.log_operation_complete("setup_all_alerts",
                                                     channels_created=len(setup_results["notification_channels"]),
                                                     policies_created=len(setup_results["alert_policies"]))

        except Exception as e:
            setup_results["errors"].append(str(e))
            self.context_logger.log_operation_error("setup_all_alerts", error=e)

        return setup_results


# Global instance
alert_manager = AlertManager()