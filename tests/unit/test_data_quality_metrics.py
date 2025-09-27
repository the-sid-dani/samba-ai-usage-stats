"""Unit tests for data quality metrics and KPI tracking."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta

from src.processing.data_quality_metrics import (
    DataQualityMetricsCollector, QualityMetric, QualityScore,
    QualityMetricType
)


@pytest.fixture
def quality_collector():
    """Create DataQualityMetricsCollector instance with mocked dependencies."""
    with patch('src.processing.data_quality_metrics.bigquery.Client'), \
         patch('src.processing.data_quality_metrics.config') as mock_config:
        mock_config.project_id = "test-project"
        mock_config.dataset = "test_dataset"

        return DataQualityMetricsCollector()


class TestDataQualityMetricsCollector:
    """Test cases for DataQualityMetricsCollector."""

    def test_initialization(self, quality_collector):
        """Test quality metrics collector initialization."""
        assert quality_collector.project_id == "test-project"
        assert quality_collector.dataset_id == "test_dataset"
        assert quality_collector.COMPLETENESS_TARGET == 95.0
        assert quality_collector.ACCURACY_TARGET == 98.0

    @patch('src.processing.data_quality_metrics.bigquery.Client')
    def test_get_active_platforms(self, mock_client, quality_collector):
        """Test active platforms retrieval (AC 4)."""
        # Given: Mocked BigQuery results
        mock_row1 = Mock()
        mock_row1.platform = "anthropic"
        mock_row2 = Mock()
        mock_row2.platform = "cursor"

        mock_client.return_value.query.return_value.result.return_value = [mock_row1, mock_row2]

        # When: Getting active platforms
        platforms = quality_collector._get_active_platforms(date(2025, 9, 27))

        # Then: Should return platform list
        assert "anthropic" in platforms
        assert "cursor" in platforms
        assert len(platforms) == 2

    @patch('src.processing.data_quality_metrics.bigquery.Client')
    def test_calculate_completeness_score_high(self, mock_client, quality_collector):
        """Test completeness score calculation with high completeness (AC 4)."""
        # Given: High completeness data
        mock_row = Mock()
        mock_row.total_records = 1000
        mock_row.attributed_records = 950  # 95% attribution
        mock_row.cost_records = 980        # 98% cost coverage

        mock_client.return_value.query.return_value.result.return_value = [mock_row]

        # When: Calculating completeness score
        score = quality_collector._calculate_completeness_score("anthropic", date(2025, 9, 27))

        # Then: Should return high score
        # Expected: (95 * 0.7) + (98 * 0.3) = 66.5 + 29.4 = 95.9
        assert score == pytest.approx(95.9, rel=0.1)

    @patch('src.processing.data_quality_metrics.bigquery.Client')
    def test_calculate_completeness_score_low(self, mock_client, quality_collector):
        """Test completeness score calculation with low completeness (AC 4)."""
        # Given: Low completeness data
        mock_row = Mock()
        mock_row.total_records = 1000
        mock_row.attributed_records = 600  # 60% attribution
        mock_row.cost_records = 700        # 70% cost coverage

        mock_client.return_value.query.return_value.result.return_value = [mock_row]

        # When: Calculating completeness score
        score = quality_collector._calculate_completeness_score("cursor", date(2025, 9, 27))

        # Then: Should return lower score
        # Expected: (60 * 0.7) + (70 * 0.3) = 42 + 21 = 63
        assert score == pytest.approx(63.0, rel=0.1)

    @patch('src.processing.data_quality_metrics.bigquery.Client')
    def test_calculate_completeness_score_no_data(self, mock_client, quality_collector):
        """Test completeness score with no data available."""
        # Given: No data found
        mock_client.return_value.query.return_value.result.return_value = []

        # When: Calculating completeness score
        score = quality_collector._calculate_completeness_score("missing_platform", date(2025, 9, 27))

        # Then: Should return zero score
        assert score == 0.0

    def test_calculate_freshness_score_very_fresh(self, quality_collector):
        """Test freshness score calculation for very fresh data (AC 4)."""
        # Given: Very fresh data (1 hour old)
        with patch.object(quality_collector, '_get_data_freshness_hours', return_value=1.0):
            # When: Calculating freshness score
            score = quality_collector._calculate_freshness_score("anthropic", date(2025, 9, 27))

            # Then: Should return perfect score
            assert score == 100.0

    def test_calculate_freshness_score_stale(self, quality_collector):
        """Test freshness score calculation for stale data (AC 4)."""
        # Given: Stale data (30 hours old)
        with patch.object(quality_collector, '_get_data_freshness_hours', return_value=30.0):
            # When: Calculating freshness score
            score = quality_collector._calculate_freshness_score("cursor", date(2025, 9, 27))

            # Then: Should return low score
            assert score == 50.0

    def test_calculate_freshness_score_very_stale(self, quality_collector):
        """Test freshness score calculation for very stale data (AC 4)."""
        # Given: Very stale data (72 hours old)
        with patch.object(quality_collector, '_get_data_freshness_hours', return_value=72.0):
            # When: Calculating freshness score
            score = quality_collector._calculate_freshness_score("anthropic", date(2025, 9, 27))

            # Then: Should return zero score
            assert score == 0.0


class TestQualityScore:
    """Test cases for QualityScore dataclass."""

    def test_quality_score_creation(self):
        """Test QualityScore creation with all metrics."""
        # Given: Complete quality score data
        score = QualityScore(
            overall_score=85.5,
            completeness_score=90.0,
            accuracy_score=95.0,
            freshness_score=80.0,
            consistency_score=85.0,
            validity_score=88.0,
            platform="anthropic"
        )

        # Then: Should create valid quality score
        assert score.overall_score == 85.5
        assert score.completeness_score == 90.0
        assert score.accuracy_score == 95.0
        assert score.freshness_score == 80.0
        assert score.consistency_score == 85.0
        assert score.validity_score == 88.0
        assert score.platform == "anthropic"
        assert score.measurement_date is not None


class TestQualityMetric:
    """Test cases for QualityMetric dataclass."""

    def test_quality_metric_creation(self):
        """Test QualityMetric creation with thresholds."""
        # Given: Quality metric data
        metric = QualityMetric(
            metric_type=QualityMetricType.COMPLETENESS,
            name="user_attribution_completeness",
            value=94.5,
            target_value=95.0,
            threshold_warning=90.0,
            threshold_critical=85.0,
            status="warning",
            platform="cursor"
        )

        # Then: Should create valid metric
        assert metric.metric_type == QualityMetricType.COMPLETENESS
        assert metric.name == "user_attribution_completeness"
        assert metric.value == 94.5
        assert metric.target_value == 95.0
        assert metric.status == "warning"
        assert metric.platform == "cursor"
        assert metric.measurement_date is not None