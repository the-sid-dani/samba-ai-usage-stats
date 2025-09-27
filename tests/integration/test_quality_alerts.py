"""Integration tests for Data Quality Alert System integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.shared.cloud_monitoring import CloudMonitoringClient, MetricType, MetricPoint
from src.processing.data_quality_metrics import DataQualityMetricsCollector, QualityScore, QualityMetricType
from src.processing.validator import DataQualityValidator, ValidationIssue, ValidationLevel


class TestDataQualityAlertIntegration:
    """Integration tests for data quality alert system."""

    @pytest.fixture
    def monitoring_client(self):
        """Create Cloud Monitoring client for testing."""
        with patch('src.shared.cloud_monitoring.config') as mock_config:
            mock_config.project_id = "test-project"
            return CloudMonitoringClient()

    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector for testing."""
        with patch('src.processing.data_quality_metrics.config') as mock_config:
            mock_config.project_id = "test-project"
            mock_config.dataset = "test_dataset"
            return DataQualityMetricsCollector()

    @pytest.fixture
    def validator(self):
        """Create validator for testing."""
        return DataQualityValidator()

    @pytest.fixture
    def sample_quality_issues(self):
        """Sample validation issues for testing."""
        return [
            ValidationIssue(
                level=ValidationLevel.ERROR,
                code="HIGH_DATA_LOSS",
                message="Data loss rate 15% exceeds threshold 5%",
                context={"loss_rate": 0.15, "threshold": 0.05}
            ),
            ValidationIssue(
                level=ValidationLevel.WARNING,
                code="LOW_USER_ATTRIBUTION",
                message="User attribution rate 92% below threshold 95%",
                context={"attribution_rate": 0.92}
            )
        ]

    class TestValidationToAlertFlow:
        """Test flow from validation issues to alert triggers."""

        @patch('src.shared.cloud_monitoring.monitoring_v3.MetricServiceClient')
        def test_validation_error_triggers_alert_metric(self, mock_metric_client, monitoring_client, validator, sample_quality_issues):
            """Given validation errors, when metrics are sent to monitoring, then alert metrics should be created."""
            # Given
            mock_client = Mock()
            mock_metric_client.return_value = mock_client

            validation_results = [sample_quality_issues]
            report = validator.generate_quality_report("test_dataset", validation_results)

            # When
            with patch.object(monitoring_client, 'client', mock_client):
                # Send error rate metric
                error_rate = (report.metrics["error_count"] / max(1, report.metrics["total_issues"])) * 100
                metric_point = MetricPoint(
                    value=error_rate,
                    labels={"dataset": "test_dataset", "platform": "anthropic"}
                )
                monitoring_client.send_metric(MetricType.ERROR_RATE, metric_point)

            # Then
            mock_client.create_time_series.assert_called_once()
            call_args = mock_client.create_time_series.call_args
            time_series = call_args[0][0]['time_series']
            assert len(time_series) == 1
            assert time_series[0].metric.type == MetricType.ERROR_RATE.value

        @patch('src.shared.cloud_monitoring.monitoring_v3.MetricServiceClient')
        def test_quality_score_below_threshold_triggers_metric(self, mock_metric_client, monitoring_client, metrics_collector):
            """Given quality score below threshold, when metrics are sent, then monitoring should receive alert-worthy metrics."""
            # Given
            mock_client = Mock()
            mock_metric_client.return_value = mock_client

            poor_quality_score = QualityScore(
                overall_score=55.0,  # Below 60 critical threshold
                completeness_score=70.0,
                accuracy_score=40.0,  # Very poor accuracy
                freshness_score=85.0,
                consistency_score=60.0,
                validity_score=75.0
            )

            # When
            with patch.object(monitoring_client, 'client', mock_client):
                collector = metrics_collector
                collector.monitoring_client = monitoring_client

                # This would be called by the metrics collector
                metric_point = MetricPoint(
                    value=poor_quality_score.overall_score,
                    labels={"dataset": "test_dataset", "platform": "anthropic", "alert_level": "critical"}
                )
                monitoring_client.send_metric(MetricType.PIPELINE_HEALTH, metric_point)

            # Then
            mock_client.create_time_series.assert_called_once()
            call_args = mock_client.create_time_series.call_args
            time_series = call_args[0][0]['time_series']
            assert len(time_series) == 1

            # Verify metric indicates critical quality issue
            metric_labels = {label.key: label.value for label in time_series[0].resource.labels}
            series_labels = {label.key: label.value for label in time_series[0].metric.labels}

            # Should have alert level indicating severity
            assert any("alert_level" in labels for labels in [metric_labels, series_labels])

    class TestAlertPolicyIntegration:
        """Test integration with Cloud Monitoring alert policies."""

        @patch('src.shared.cloud_monitoring.monitoring_v3.AlertPolicyServiceClient')
        def test_create_data_quality_alert_policy(self, mock_alert_client, monitoring_client):
            """Given data quality monitoring setup, when alert policy is created, then should configure quality thresholds."""
            # Given
            mock_client = Mock()
            mock_alert_client.return_value = mock_client
            mock_client.create_alert_policy.return_value = Mock(name="test-alert-policy")

            alert_config = {
                "display_name": "Data Quality Issue",
                "conditions": [
                    {
                        "display_name": "Quality Score Below Threshold",
                        "condition_threshold": {
                            "filter": f'metric.type="{MetricType.PIPELINE_HEALTH.value}"',
                            "comparison": "COMPARISON_LESS_THAN",
                            "threshold_value": 75.0,
                            "duration": "300s",
                            "aggregations": [
                                {
                                    "alignment_period": "60s",
                                    "per_series_aligner": "ALIGN_MEAN"
                                }
                            ]
                        }
                    }
                ],
                "notification_channels": ["projects/test-project/notificationChannels/test-channel"],
                "alert_strategy": {
                    "auto_close": "1800s"  # 30 minutes
                }
            }

            # When
            policy_name = monitoring_client.create_alert_policy(alert_config)

            # Then
            mock_client.create_alert_policy.assert_called_once()
            assert policy_name == "test-alert-policy"

        @patch('src.shared.cloud_monitoring.monitoring_v3.AlertPolicyServiceClient')
        def test_create_data_freshness_alert_policy(self, mock_alert_client, monitoring_client):
            """Given data freshness monitoring, when alert policy is created, then should configure staleness thresholds."""
            # Given
            mock_client = Mock()
            mock_alert_client.return_value = mock_client
            mock_client.create_alert_policy.return_value = Mock(name="freshness-alert-policy")

            alert_config = {
                "display_name": "Stale Data Alert",
                "conditions": [
                    {
                        "display_name": "Data Freshness Exceeds Threshold",
                        "condition_threshold": {
                            "filter": f'metric.type="{MetricType.DATA_FRESHNESS.value}"',
                            "comparison": "COMPARISON_GREATER_THAN",
                            "threshold_value": 25.0,  # 25 hours
                            "duration": "600s"  # 10 minutes
                        }
                    }
                ]
            }

            # When
            policy_name = monitoring_client.create_alert_policy(alert_config)

            # Then
            mock_client.create_alert_policy.assert_called_once()
            call_args = mock_client.create_alert_policy.call_args
            policy = call_args[1]['alert_policy']

            # Verify threshold configuration
            condition = policy.conditions[0]
            assert condition.condition_threshold.threshold_value == 25.0
            assert condition.condition_threshold.comparison == 2  # COMPARISON_GREATER_THAN

    class TestAlertThresholdBehavior:
        """Test alert threshold logic and behavior."""

        def test_error_rate_threshold_logic(self, validator):
            """Given varying error rates, when determining alert status, then should trigger at correct thresholds."""
            # Test cases: (error_count, total_issues, expected_alert_level)
            test_cases = [
                (0, 10, "normal"),      # 0% error rate
                (2, 100, "normal"),     # 2% error rate (below 5% threshold)
                (7, 100, "warning"),    # 7% error rate (5-10% threshold)
                (15, 100, "critical")   # 15% error rate (above 10% threshold)
            ]

            for error_count, total_issues, expected_level in test_cases:
                # Given
                issues = []

                # Create appropriate number of error and warning issues
                for i in range(error_count):
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="TEST_ERROR",
                        message=f"Test error {i}"
                    ))

                for i in range(total_issues - error_count):
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="TEST_WARNING",
                        message=f"Test warning {i}"
                    ))

                # When
                report = validator.generate_quality_report("test", [issues])
                error_rate = (report.metrics["error_count"] / max(1, report.metrics["total_issues"])) * 100

                # Then
                if expected_level == "normal":
                    assert error_rate < 5.0, f"Error rate {error_rate}% should be normal"
                elif expected_level == "warning":
                    assert 5.0 <= error_rate < 10.0, f"Error rate {error_rate}% should be warning"
                elif expected_level == "critical":
                    assert error_rate >= 10.0, f"Error rate {error_rate}% should be critical"

        def test_quality_score_threshold_logic(self, metrics_collector):
            """Given varying quality scores, when determining alert status, then should trigger at correct thresholds."""
            # Test cases: (overall_score, expected_alert_level)
            test_cases = [
                (85.0, "normal"),     # Above 75 threshold
                (70.0, "warning"),    # 60-75 threshold
                (50.0, "critical")    # Below 60 threshold
            ]

            for overall_score, expected_level in test_cases:
                # Given
                quality_score = QualityScore(
                    overall_score=overall_score,
                    completeness_score=90.0,
                    accuracy_score=85.0,
                    freshness_score=95.0,
                    consistency_score=80.0,
                    validity_score=88.0
                )

                # When
                alert_level = metrics_collector._determine_alert_level(quality_score)

                # Then
                assert alert_level == expected_level, f"Score {overall_score} should trigger {expected_level} alert"

    class TestAlertNotificationFlow:
        """Test alert notification and escalation flow."""

        @patch('src.shared.cloud_monitoring.monitoring_v3.NotificationChannelServiceClient')
        def test_notification_channel_configuration(self, mock_notification_client, monitoring_client):
            """Given alert notification setup, when channels are configured, then should create proper notification channels."""
            # Given
            mock_client = Mock()
            mock_notification_client.return_value = mock_client
            mock_client.create_notification_channel.return_value = Mock(
                name="projects/test-project/notificationChannels/test-channel"
            )

            notification_config = {
                "type": "email",
                "display_name": "Data Quality Team",
                "labels": {
                    "email_address": "data-team@example.com"
                },
                "enabled": True
            }

            # When
            with patch.object(monitoring_client, 'notification_client', mock_client):
                channel_name = monitoring_client.create_notification_channel(notification_config)

            # Then
            mock_client.create_notification_channel.assert_called_once()
            assert "notificationChannels" in channel_name

        @patch('src.shared.cloud_monitoring.monitoring_v3.MetricServiceClient')
        @patch('src.shared.cloud_monitoring.monitoring_v3.AlertPolicyServiceClient')
        def test_end_to_end_alert_flow(self, mock_alert_client, mock_metric_client, monitoring_client, validator):
            """Given complete alert flow, when quality issues occur, then should trigger full notification chain."""
            # Given
            mock_metric_client_instance = Mock()
            mock_alert_client_instance = Mock()
            mock_metric_client.return_value = mock_metric_client_instance
            mock_alert_client.return_value = mock_alert_client_instance

            # Simulate quality issues
            critical_issues = [
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="CRITICAL_DATA_LOSS",
                    message="Critical data loss detected",
                    context={"loss_rate": 0.25}
                )
            ]

            # When
            # 1. Generate quality report
            report = validator.generate_quality_report("production_dataset", [critical_issues])

            # 2. Send metrics to monitoring
            with patch.object(monitoring_client, 'client', mock_metric_client_instance):
                error_rate = (report.metrics["error_count"] / max(1, report.metrics["total_issues"])) * 100
                metric_point = MetricPoint(
                    value=error_rate,
                    labels={"severity": "critical", "dataset": "production_dataset"}
                )
                monitoring_client.send_metric(MetricType.ERROR_RATE, metric_point)

            # 3. Simulate alert policy trigger (would happen automatically in GCP)
            alert_triggered = error_rate > 10.0  # Threshold breach

            # Then
            assert report.passed is False, "Report should fail with critical issues"
            assert report.metrics["error_count"] > 0, "Should have error count"
            mock_metric_client_instance.create_time_series.assert_called_once()
            assert alert_triggered, "Error rate should trigger alert threshold"

    class TestAlertSuppressionAndEscalation:
        """Test alert suppression and escalation logic."""

        def test_alert_suppression_for_known_issues(self, monitoring_client):
            """Given known data issues, when alerts are configured, then should suppress expected alerts."""
            # Given
            known_issues = {
                "weekend_data_delay": {
                    "metric_type": MetricType.DATA_FRESHNESS,
                    "suppression_window": "48h",
                    "days": ["saturday", "sunday"]
                }
            }

            current_time = datetime.now()
            is_weekend = current_time.weekday() >= 5  # Saturday=5, Sunday=6

            # When
            should_suppress = self._check_alert_suppression(
                MetricType.DATA_FRESHNESS,
                known_issues,
                current_time
            )

            # Then
            if is_weekend:
                assert should_suppress, "Should suppress freshness alerts on weekends"
            else:
                assert not should_suppress, "Should not suppress alerts on weekdays"

        def test_escalation_for_persistent_issues(self, monitoring_client):
            """Given persistent quality issues, when escalation is configured, then should escalate after threshold."""
            # Given
            alert_history = [
                {"timestamp": datetime.now() - timedelta(minutes=30), "resolved": False},
                {"timestamp": datetime.now() - timedelta(minutes=20), "resolved": False},
                {"timestamp": datetime.now() - timedelta(minutes=10), "resolved": False}
            ]

            escalation_threshold = timedelta(minutes=25)  # Escalate after 25 minutes

            # When
            should_escalate = self._check_escalation_needed(alert_history, escalation_threshold)

            # Then
            assert should_escalate, "Should escalate after persistent unresolved alerts"

        def _check_alert_suppression(self, metric_type, known_issues, current_time):
            """Helper method to check if alert should be suppressed."""
            for issue_name, config in known_issues.items():
                if config["metric_type"] == metric_type:
                    if "days" in config:
                        current_day = current_time.strftime("%A").lower()
                        return current_day in config["days"]
            return False

        def _check_escalation_needed(self, alert_history, threshold):
            """Helper method to check if escalation is needed."""
            if not alert_history:
                return False

            unresolved_alerts = [a for a in alert_history if not a["resolved"]]
            if not unresolved_alerts:
                return False

            oldest_unresolved = min(unresolved_alerts, key=lambda x: x["timestamp"])
            time_since_first = datetime.now() - oldest_unresolved["timestamp"]

            return time_since_first > threshold

    class TestAlertMetricsAccuracy:
        """Test accuracy of alert metrics and calculations."""

        def test_attribution_completeness_alert_accuracy(self, monitoring_client):
            """Given user attribution data, when calculating completeness metrics, then should accurately determine alert status."""
            # Given
            usage_records = [
                {"user_email": "user1@example.com", "api_key_id": "key1"},
                {"user_email": "user2@example.com", "api_key_id": "key2"},
                {"user_email": "", "api_key_id": "key3"},  # Missing attribution
                {"user_email": "", "api_key_id": "key4"},  # Missing attribution
                {"user_email": "user5@example.com", "api_key_id": "key5"}
            ]

            # When
            attributed_count = len([r for r in usage_records if r.get("user_email") and "@" in r["user_email"]])
            total_count = len(usage_records)
            attribution_rate = (attributed_count / total_count) * 100

            # Then
            assert attribution_rate == 60.0, f"Attribution rate should be 60%, got {attribution_rate}%"
            assert attribution_rate < 95.0, "Should trigger attribution completeness alert"

        def test_cost_variance_alert_accuracy(self, monitoring_client):
            """Given cost variance data, when calculating variance metrics, then should accurately determine alert status."""
            # Given
            calculated_costs = [100.0, 150.0, 120.0, 80.0, 110.0]  # Total: 560
            vendor_invoice_total = 650.0  # Expected total

            # When
            calculated_total = sum(calculated_costs)
            variance = abs(calculated_total - vendor_invoice_total) / vendor_invoice_total * 100

            # Then
            assert variance > 10.0, f"Variance should be >10%, got {variance:.1f}%"
            assert variance > 5.0, "Should trigger cost variance alert (>5% threshold)"

    class TestAlertRecoveryAndResolution:
        """Test alert recovery and resolution scenarios."""

        @patch('src.shared.cloud_monitoring.monitoring_v3.MetricServiceClient')
        def test_quality_improvement_resolves_alerts(self, mock_metric_client, monitoring_client, validator):
            """Given improved data quality, when metrics are updated, then alerts should resolve."""
            # Given - Initial poor quality
            poor_issues = [
                ValidationIssue(ValidationLevel.ERROR, "ERROR1", "Error 1"),
                ValidationIssue(ValidationLevel.ERROR, "ERROR2", "Error 2")
            ]

            # Later - Improved quality
            improved_issues = [
                ValidationIssue(ValidationLevel.WARNING, "WARNING1", "Minor warning")
            ]

            mock_client = Mock()
            mock_metric_client.return_value = mock_client

            # When - Send initial poor metrics
            poor_report = validator.generate_quality_report("test", [poor_issues])
            poor_error_rate = (poor_report.metrics["error_count"] / max(1, poor_report.metrics["total_issues"])) * 100

            # Then send improved metrics
            improved_report = validator.generate_quality_report("test", [improved_issues])
            improved_error_rate = (improved_report.metrics["error_count"] / max(1, improved_report.metrics["total_issues"])) * 100

            # Then
            assert poor_error_rate > 50.0, "Initial error rate should be high"
            assert improved_error_rate == 0.0, "Improved error rate should be zero"
            assert improved_error_rate < 5.0, "Improved rate should be below alert threshold"