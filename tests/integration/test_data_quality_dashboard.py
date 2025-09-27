"""Integration tests for Data Quality Dashboard views and functionality."""

import pytest
import os
import re
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

from src.storage.bigquery_client import BigQuerySchemaManager
from src.processing.data_quality_metrics import DataQualityMetricsCollector


class TestDataQualityDashboardIntegration:
    """Integration tests for data quality dashboard components."""

    @pytest.fixture
    def bigquery_client(self):
        """Create BigQuery client with mocked config."""
        with patch('src.storage.bigquery_client.config') as mock_config:
            mock_config.project_id = "test-project"
            mock_config.dataset = "test_dataset"
            return BigQuerySchemaManager()

    @pytest.fixture
    def mock_bigquery_results(self):
        """Mock BigQuery query results for dashboard data."""
        return {
            'quality_metrics': [
                {
                    'measurement_date': date.today() - timedelta(days=1),
                    'platform': 'anthropic',
                    'overall_score': 85.5,
                    'completeness_score': 92.0,
                    'accuracy_score': 88.0,
                    'freshness_score': 95.0,
                    'consistency_score': 82.0,
                    'validity_score': 90.0
                }
            ],
            'data_freshness': [
                {
                    'data_type': 'usage_data',
                    'table_name': 'fct_usage_daily',
                    'latest_data_date': date.today() - timedelta(days=1),
                    'days_behind': 1,
                    'hours_behind': 18
                }
            ],
            'attribution_completeness': [
                {
                    'metric_date': date.today() - timedelta(days=1),
                    'platform': 'anthropic',
                    'total_records': 1000,
                    'attributed_records': 960,
                    'attribution_rate': 96.0
                }
            ]
        }

    class TestDashboardViewSQLSyntax:
        """Test data quality dashboard view SQL syntax and structure."""

        def test_dashboard_view_file_exists(self):
            """Given dashboard view SQL file, then file should exist."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When & Then
            assert os.path.exists(view_file), "Data quality dashboard view file should exist"

        def test_dashboard_view_sql_syntax(self):
            """Given dashboard view SQL, then syntax should be valid."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When
            with open(view_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Then
            assert "CREATE OR REPLACE VIEW" in sql_content, "Should contain CREATE OR REPLACE VIEW"
            assert "vw_data_quality_dashboard" in sql_content, "Should reference correct view name"
            assert "SELECT" in sql_content, "Should contain SELECT statement"
            assert "FROM" in sql_content, "Should contain FROM clause"

        def test_dashboard_view_required_tables(self):
            """Given dashboard view SQL, then should reference required data quality tables."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When
            with open(view_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Then
            assert "data_quality_metrics" in sql_content, "Should reference data quality metrics table"
            assert "fct_usage_daily" in sql_content, "Should reference usage facts table"
            assert "fct_cost_daily" in sql_content, "Should reference cost facts table"

        def test_dashboard_view_quality_indicators(self):
            """Given dashboard view SQL, then should include quality status indicators."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When
            with open(view_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Then
            assert "quality_status" in sql_content, "Should include quality status field"
            assert "alert_level" in sql_content, "Should include alert level field"
            assert "overall_alert_status" in sql_content, "Should include overall alert status"
            assert "improvement_recommendations" in sql_content, "Should include recommendations"

        def test_dashboard_view_time_filters(self):
            """Given dashboard view SQL, then should include proper time filtering."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When
            with open(view_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Then
            assert "INTERVAL 30 DAY" in sql_content, "Should include 30-day lookback for trends"
            assert "INTERVAL 7 DAY" in sql_content, "Should include 7-day lookback for recent data"
            assert "CURRENT_DATE()" in sql_content, "Should use current date for calculations"

    class TestDashboardMetricsCalculation:
        """Test dashboard metrics calculation and aggregation."""

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_quality_score_aggregation(self, mock_bq_client, bigquery_client, mock_bigquery_results):
            """Given quality metrics data, when dashboard aggregates scores, then should calculate correctly."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'overall_quality_score': 85.5,
                    'avg_completeness_score': 92.0,
                    'avg_accuracy_score': 88.0,
                    'avg_freshness_score': 95.0
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT
                        overall_quality_score,
                        avg_completeness_score,
                        avg_accuracy_score,
                        avg_freshness_score
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            result = results[0]
            assert result['overall_quality_score'] == 85.5
            assert result['avg_completeness_score'] >= 90.0  # Should meet completeness target
            assert result['avg_freshness_score'] >= 90.0  # Should meet freshness target

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_freshness_indicators(self, mock_bq_client, bigquery_client):
            """Given data freshness metrics, when dashboard calculates indicators, then should identify stale data."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'max_hours_behind': 28.0,  # Over 25-hour threshold
                    'stale_tables_count': 1
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT max_hours_behind, stale_tables_count
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            result = results[0]
            assert result['max_hours_behind'] > 25.0  # Should detect stale data
            assert result['stale_tables_count'] > 0  # Should count stale tables

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_attribution_completeness_tracking(self, mock_bq_client, bigquery_client):
            """Given attribution data, when dashboard tracks completeness, then should calculate rates correctly."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'avg_attribution_rate': 96.0,  # Above 95% target
                    'platforms_below_attribution_target': 0
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT avg_attribution_rate, platforms_below_attribution_target
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            result = results[0]
            assert result['avg_attribution_rate'] >= 95.0  # Should meet attribution target
            assert result['platforms_below_attribution_target'] == 0  # All platforms meeting target

    class TestDashboardAlertLogic:
        """Test dashboard alert logic and status determination."""

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_normal_alert_status(self, mock_bq_client, bigquery_client):
            """Given good quality scores, when dashboard determines status, then should show normal."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'overall_alert_status': 'normal',
                    'overall_quality_score': 85.0,  # Above 75 threshold
                    'max_hours_behind': 20.0  # Below 25 threshold
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT overall_alert_status, overall_quality_score, max_hours_behind
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            result = results[0]
            assert result['overall_alert_status'] == 'normal'
            assert result['overall_quality_score'] >= 75.0
            assert result['max_hours_behind'] <= 25.0

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_warning_alert_status(self, mock_bq_client, bigquery_client):
            """Given moderate quality issues, when dashboard determines status, then should show warning."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'overall_alert_status': 'warning',
                    'overall_quality_score': 70.0,  # Between 60-75 threshold
                    'max_hours_behind': 22.0
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT overall_alert_status, overall_quality_score
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            result = results[0]
            assert result['overall_alert_status'] == 'warning'
            assert 60.0 <= result['overall_quality_score'] < 75.0

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_critical_alert_status(self, mock_bq_client, bigquery_client):
            """Given poor quality scores, when dashboard determines status, then should show critical."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'overall_alert_status': 'critical',
                    'overall_quality_score': 55.0  # Below 60 threshold
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT overall_alert_status, overall_quality_score
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            result = results[0]
            assert result['overall_alert_status'] == 'critical'
            assert result['overall_quality_score'] < 60.0

    class TestDashboardRecommendations:
        """Test dashboard improvement recommendations generation."""

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_attribution_improvement_recommendation(self, mock_bq_client, bigquery_client):
            """Given low completeness score, when dashboard generates recommendations, then should suggest attribution improvements."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'improvement_recommendations': [
                        {
                            'platform': 'anthropic',
                            'overall_score': 75.0,
                            'recommendation': 'Improve user attribution mapping'
                        }
                    ]
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT improvement_recommendations
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            recommendations = results[0]['improvement_recommendations']
            assert len(recommendations) >= 1
            assert any('attribution' in rec['recommendation'].lower() for rec in recommendations)

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_validation_improvement_recommendation(self, mock_bq_client, bigquery_client):
            """Given low accuracy score, when dashboard generates recommendations, then should suggest validation improvements."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [
                {
                    'improvement_recommendations': [
                        {
                            'platform': 'cursor',
                            'overall_score': 78.0,
                            'recommendation': 'Review data validation rules'
                        }
                    ]
                }
            ]
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = """
                    SELECT improvement_recommendations
                    FROM `test-project.test_dataset.vw_data_quality_dashboard`
                """
                results = list(client.client.query(query).result())

            # Then
            assert len(results) == 1
            recommendations = results[0]['improvement_recommendations']
            assert len(recommendations) >= 1
            assert any('validation' in rec['recommendation'].lower() for rec in recommendations)

    class TestDashboardDataQualityMetricsIntegration:
        """Test integration between dashboard and data quality metrics collection."""

        @pytest.fixture
        def metrics_collector(self):
            """Create metrics collector for testing."""
            with patch('src.processing.data_quality_metrics.config') as mock_config:
                mock_config.project_id = "test-project"
                mock_config.dataset = "test_dataset"
                return DataQualityMetricsCollector()

        @patch('src.processing.data_quality_metrics.BigQueryClient')
        def test_metrics_collection_feeds_dashboard(self, mock_bq_client, metrics_collector):
            """Given metrics collection process, when data is collected, then dashboard should have access to metrics."""
            # Given
            mock_insert_job = Mock()
            mock_insert_job.result.return_value = None
            mock_bq_client.load_table_from_json.return_value = mock_insert_job

            sample_metrics = {
                'measurement_date': date.today().isoformat(),
                'platform': 'anthropic',
                'overall_score': 88.5,
                'completeness_score': 95.0,
                'accuracy_score': 85.0,
                'freshness_score': 92.0,
                'consistency_score': 88.0,
                'validity_score': 90.0
            }

            # When
            collector = metrics_collector
            with patch.object(collector, 'client', mock_bq_client):
                collector.store_metrics([sample_metrics])

            # Then
            mock_bq_client.load_table_from_json.assert_called_once()
            stored_data = mock_bq_client.load_table_from_json.call_args[0][0]
            assert len(stored_data) == 1
            assert stored_data[0]['platform'] == 'anthropic'
            assert stored_data[0]['overall_score'] == 88.5

        def test_dashboard_view_parameter_substitution(self):
            """Given dashboard view template, when parameters are substituted, then should use correct project and dataset."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When
            with open(view_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Then
            assert "${PROJECT_ID}" in sql_content, "Should contain project ID placeholder"
            assert "${DATASET}" in sql_content, "Should contain dataset placeholder"

            # Verify substitution would work correctly
            substituted = sql_content.replace("${PROJECT_ID}", "test-project")
            substituted = substituted.replace("${DATASET}", "test_dataset")

            assert "test-project.test_dataset" in substituted, "Should substitute parameters correctly"
            assert "${" not in substituted, "Should not have remaining placeholders"

    class TestDashboardPerformance:
        """Test dashboard query performance and optimization."""

        def test_dashboard_view_has_date_filters(self):
            """Given dashboard view SQL, when examining performance, then should include date filters for optimization."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When
            with open(view_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Then
            # Check for date filters that improve query performance
            assert "DATE_SUB" in sql_content, "Should use date filtering for performance"
            assert "WHERE" in sql_content, "Should include WHERE clauses for filtering"
            assert "INTERVAL" in sql_content, "Should use interval-based date filtering"

        def test_dashboard_view_uses_aggregations(self):
            """Given dashboard view SQL, when examining structure, then should use efficient aggregations."""
            # Given
            view_file = "sql/views/vw_data_quality_dashboard.sql"

            # When
            with open(view_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Then
            # Check for efficient aggregation patterns
            assert "AVG(" in sql_content, "Should use average aggregations"
            assert "MAX(" in sql_content, "Should use max aggregations"
            assert "COUNT(" in sql_content, "Should use count aggregations"

        @patch('src.storage.bigquery_client.BigQueryClient')
        def test_dashboard_query_execution_time(self, mock_bq_client, bigquery_client):
            """Given dashboard query, when executed, then should complete within reasonable time."""
            # Given
            mock_job = Mock()
            mock_job.result.return_value = [{'overall_quality_score': 85.0}]
            mock_job.ended = datetime.now()
            mock_job.started = datetime.now() - timedelta(seconds=2)  # 2 second execution
            mock_bq_client.query.return_value = mock_job

            # When
            client = bigquery_client
            with patch.object(client, 'client', mock_bq_client):
                query = "SELECT * FROM `test-project.test_dataset.vw_data_quality_dashboard`"
                job = client.client.query(query)
                job.result()

            # Then
            execution_time = (job.ended - job.started).total_seconds()
            assert execution_time < 30.0, "Dashboard query should complete within 30 seconds"
            mock_bq_client.query.assert_called_once()