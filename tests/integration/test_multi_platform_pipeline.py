"""Integration tests for multi-platform data pipeline."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date, timedelta

from src.ingestion.cursor_client import CursorClient, CursorUsageData
from src.ingestion.anthropic_client import AnthropicClient, AnthropicUsageData, AnthropicCostData
from src.ingestion.sheets_client import GoogleSheetsClient, APIKeyMapping
from src.processing.multi_platform_transformer import MultiPlatformTransformer
from src.processing.attribution import UserAttributionEngine
from src.shared.monitoring import SystemMonitor


@pytest.fixture
def mock_api_responses():
    """Mock API responses for integration testing."""
    return {
        "cursor_response": {
            "data": [
                {
                    "email": "john.doe@company.com",
                    "totalLinesAdded": 1500,
                    "acceptedLinesAdded": 1200,
                    "totalAccepts": 45,
                    "subscriptionIncludedReqs": 100,
                    "usageBasedReqs": 25,
                    "timestamp": 1640995200
                },
                {
                    "email": "jane.smith@company.com",
                    "totalLinesAdded": 800,
                    "acceptedLinesAdded": 600,
                    "totalAccepts": 22,
                    "subscriptionIncludedReqs": 50,
                    "usageBasedReqs": 10,
                    "timestamp": 1640995200
                }
            ]
        },
        "anthropic_usage_response": {
            "data": [
                {
                    "starting_at": "2022-01-01T00:00:00Z",
                    "ending_at": "2022-01-02T00:00:00Z",
                    "api_key_id": "key_prod_123",
                    "workspace_id": "ws_456",
                    "model": "claude-3-sonnet-20240229",
                    "results": [
                        {
                            "uncached_input_tokens": 2000,
                            "cache_creation": {"ephemeral_1h_input_tokens": 300},
                            "cache_read_input_tokens": 200,
                            "output_tokens": 1000
                        }
                    ]
                }
            ],
            "next_page_token": None
        },
        "anthropic_cost_response": {
            "data": [
                {
                    "starting_at": "2022-01-01T00:00:00Z",
                    "ending_at": "2022-01-02T00:00:00Z",
                    "api_key_id": "key_prod_123",
                    "workspace_id": "ws_456",
                    "model": "claude-3-sonnet-20240229",
                    "results": [
                        {
                            "currency": "USD",
                            "amount": "0.182",
                            "workspace_id": "ws_456"
                        }
                    ]
                }
            ],
            "next_page_token": None
        },
        "sheets_response": {
            "values": [
                ["api_key_name", "email", "description"],
                ["key_prod_123", "sarah.wilson@company.com", "Production Claude API key"],
                ["cursor-team-key", "team@company.com", "Team Cursor key"]
            ]
        }
    }


class TestMultiPlatformPipelineIntegration:
    """Integration tests for the complete multi-platform pipeline."""

    @patch('src.ingestion.cursor_client.requests.post')
    @patch('src.ingestion.anthropic_client.requests.get')
    def test_end_to_end_data_flow(self, mock_anthropic_get, mock_cursor_post, mock_api_responses):
        """Test complete end-to-end data flow from APIs to normalized records."""

        # Mock API responses
        mock_cursor_response = Mock()
        mock_cursor_response.status_code = 200
        mock_cursor_response.json.return_value = mock_api_responses["cursor_response"]
        mock_cursor_post.return_value = mock_cursor_response

        mock_anthropic_response = Mock()
        mock_anthropic_response.status_code = 200
        mock_anthropic_response.json.return_value = mock_api_responses["anthropic_usage_response"]
        mock_anthropic_get.return_value = mock_anthropic_response

        # Mock Google Sheets
        with patch('src.ingestion.sheets_client.GoogleSheetsClient') as mock_sheets_class:
            mock_sheets = Mock()
            mock_sheets.get_api_key_mappings.return_value = [
                APIKeyMapping(
                    api_key_name="key_prod_123",
                    user_email="sarah.wilson@company.com",
                    description="Production Claude API key",
                    platform="anthropic"
                )
            ]
            mock_sheets_class.return_value = mock_sheets

            # Mock config
            with patch('src.ingestion.cursor_client.config') as mock_cursor_config:
                mock_cursor_config.cursor_api_key = "test-cursor-key"
                with patch('src.ingestion.anthropic_client.config') as mock_anthropic_config:
                    mock_anthropic_config.anthropic_api_key = "test-anthropic-key"

                    # Execute the pipeline
                    cursor_client = CursorClient()
                    anthropic_client = AnthropicClient()
                    transformer = MultiPlatformTransformer()

                    # Get data from APIs
                    start_date = date(2022, 1, 1)
                    end_date = date(2022, 1, 2)

                    cursor_data = cursor_client.get_daily_usage_data(start_date, end_date)
                    anthropic_data = anthropic_client.get_usage_data(start_date, end_date)
                    api_mappings = mock_sheets.get_api_key_mappings()

                    # Transform data
                    result = transformer.transform_all_usage_data(
                        cursor_data=cursor_data,
                        anthropic_data=anthropic_data,
                        api_key_mappings=api_mappings
                    )

                    # Validate results
                    assert result["success"] is True
                    assert len(result["usage_records"]) == 3  # 2 Cursor + 1 Anthropic
                    assert result["transformation_stats"]["total_input"] == 3
                    assert result["transformation_stats"]["total_output"] == 3

                    # Check platform distribution
                    platforms = {record.platform for record in result["usage_records"]}
                    assert "cursor" in platforms
                    assert "anthropic_api" in platforms

                    # Check user attribution
                    emails = {record.user_email for record in result["usage_records"]}
                    assert "john.doe@company.com" in emails
                    assert "jane.smith@company.com" in emails
                    assert "sarah.wilson@company.com" in emails

    def test_cost_attribution_accuracy(self, mock_api_responses):
        """Test cost attribution accuracy across platforms."""

        with patch('src.ingestion.anthropic_client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_responses["anthropic_cost_response"]
            mock_get.return_value = mock_response

            with patch('src.ingestion.sheets_client.GoogleSheetsClient') as mock_sheets_class:
                mock_sheets = Mock()
                mock_sheets.get_api_key_mappings.return_value = [
                    APIKeyMapping(
                        api_key_name="key_prod_123",
                        user_email="sarah.wilson@company.com",
                        description="Production Claude API key",
                        platform="anthropic"
                    )
                ]
                mock_sheets_class.return_value = mock_sheets

                with patch('src.ingestion.anthropic_client.config') as mock_config:
                    mock_config.anthropic_api_key = "test-key"

                    # Test cost data flow
                    anthropic_client = AnthropicClient()
                    transformer = MultiPlatformTransformer()

                    cost_data = anthropic_client.get_cost_data(date(2022, 1, 1), date(2022, 1, 2))
                    cost_records = transformer.create_cost_records(
                        cost_data,
                        mock_sheets.get_api_key_mappings()
                    )

                    # Validate cost attribution - real API returns single total cost record
                    assert len(cost_records) == 1  # Single total cost record
                    record = cost_records[0]
                    assert record["user_email"] == "sarah.wilson@company.com"
                    assert record["api_key_id"] == "key_prod_123"
                    assert record["platform"] == "anthropic"

                    # Verify cost type and amount
                    assert record["cost_type"] == "total_cost"
                    assert record["cost_usd"] == 0.182


    def test_user_attribution_cross_platform(self, mock_api_responses):
        """Test user attribution consistency across platforms."""

        # Mock both API clients
        with patch('src.ingestion.cursor_client.requests.post') as mock_cursor_post:
            with patch('src.ingestion.anthropic_client.requests.get') as mock_anthropic_get:

                # Setup API mocks
                mock_cursor_response = Mock()
                mock_cursor_response.status_code = 200
                mock_cursor_response.json.return_value = mock_api_responses["cursor_response"]
                mock_cursor_post.return_value = mock_cursor_response

                mock_anthropic_response = Mock()
                mock_anthropic_response.status_code = 200
                mock_anthropic_response.json.return_value = mock_api_responses["anthropic_usage_response"]
                mock_anthropic_get.return_value = mock_anthropic_response

                # Mock Google Sheets with user who has both Cursor and Anthropic usage
                with patch('src.ingestion.sheets_client.GoogleSheetsClient') as mock_sheets_class:
                    mock_sheets = Mock()
                    mock_sheets.get_api_key_mappings.return_value = [
                        APIKeyMapping(
                            api_key_name="key_prod_123",
                            user_email="john.doe@company.com",  # Same user as in Cursor data
                            description="Production Claude API key",
                            platform="anthropic"
                        )
                    ]
                    mock_sheets_class.return_value = mock_sheets

                    # Mock configs
                    with patch('src.ingestion.cursor_client.config') as mock_cursor_config:
                        mock_cursor_config.cursor_api_key = "test-cursor-key"
                        with patch('src.ingestion.anthropic_client.config') as mock_anthropic_config:
                            mock_anthropic_config.anthropic_api_key = "test-anthropic-key"

                            # Execute attribution test
                            attribution_engine = UserAttributionEngine(mock_sheets)
                            transformer = MultiPlatformTransformer()

                            # Get test data
                            cursor_client = CursorClient()
                            anthropic_client = AnthropicClient()

                            cursor_data = cursor_client.get_daily_usage_data(date(2022, 1, 1), date(2022, 1, 2))
                            anthropic_data = anthropic_client.get_usage_data(date(2022, 1, 1), date(2022, 1, 2))

                            # Transform with attribution
                            result = transformer.transform_all_usage_data(
                                cursor_data=cursor_data,
                                anthropic_data=anthropic_data,
                                api_key_mappings=mock_sheets.get_api_key_mappings()
                            )

                            # Validate cross-platform attribution
                            user_platforms = {}
                            for record in result["usage_records"]:
                                user = record.user_email
                                if user not in user_platforms:
                                    user_platforms[user] = set()
                                user_platforms[user].add(record.platform)

                            # john.doe should appear on both platforms
                            assert "john.doe@company.com" in user_platforms
                            john_platforms = user_platforms["john.doe@company.com"]
                            assert "cursor" in john_platforms
                            assert "anthropic_api" in john_platforms

    def test_data_quality_validation_pipeline(self):
        """Test comprehensive data quality validation."""

        # Create test data with quality issues
        cursor_data = [
            CursorUsageData(
                email="valid@company.com",
                total_lines_added=1000,
                accepted_lines_added=800,
                total_accepts=25,
                subscription_included_reqs=50,
                usage_based_reqs=10,
                date=datetime(2022, 1, 1)
            ),
            CursorUsageData(
                email="",  # Invalid: empty email
                total_lines_added=500,
                accepted_lines_added=400,
                total_accepts=15,
                subscription_included_reqs=30,
                usage_based_reqs=5,
                date=datetime(2022, 1, 1)
            )
        ]

        anthropic_data = [
            AnthropicUsageData(
                api_key_id="mapped_key",
                workspace_id="ws_123",
                model="claude-3-sonnet-20240229",
                uncached_input_tokens=1000,
                cached_input_tokens=200,
                cache_read_input_tokens=150,
                output_tokens=500,
                usage_date=date(2022, 1, 1),
                usage_hour=12
            ),
            AnthropicUsageData(
                api_key_id="unmapped_key",  # No mapping available
                workspace_id="ws_123",
                model="claude-3-haiku-20240307",
                uncached_input_tokens=800,
                cached_input_tokens=100,
                cache_read_input_tokens=50,
                output_tokens=300,
                usage_date=date(2022, 1, 1),
                usage_hour=14
            )
        ]

        api_mappings = [
            APIKeyMapping(
                api_key_name="mapped_key",
                user_email="mapped.user@company.com",
                description="Mapped key",
                platform="anthropic"
            )
        ]

        # Run transformation and validation
        transformer = MultiPlatformTransformer()

        # Test data validation
        validation_result = transformer.validate_multi_platform_data(
            cursor_data=cursor_data,
            anthropic_data=anthropic_data,
            api_key_mappings=api_mappings
        )

        # Should detect data quality issues
        assert validation_result["overall_status"] in ["acceptable", "needs_attention"]
        assert validation_result["cursor_validation"]["invalid"] == 1  # Empty email
        assert validation_result["mapping_validation"]["coverage"] == 0.5  # 1/2 keys mapped

        # Transform data
        transform_result = transformer.transform_all_usage_data(
            cursor_data=cursor_data,
            anthropic_data=anthropic_data,
            api_key_mappings=api_mappings
        )

        # Should handle quality issues gracefully
        assert transform_result["success"] is True
        # Should only process valid records
        assert len(transform_result["usage_records"]) == 2  # 1 valid Cursor + 1 mapped Anthropic

    def test_performance_and_scalability(self):
        """Test pipeline performance with larger datasets."""

        # Create larger test dataset
        cursor_data = []
        for i in range(50):  # 50 Cursor records
            cursor_data.append(
                CursorUsageData(
                    email=f"user{i}@company.com",
                    total_lines_added=1000 + i,
                    accepted_lines_added=800 + i,
                    total_accepts=25 + i,
                    subscription_included_reqs=50,
                    usage_based_reqs=10,
                    date=datetime(2022, 1, 1)
                )
            )

        anthropic_data = []
        api_mappings = []
        for i in range(30):  # 30 Anthropic records
            api_key = f"key_{i}"
            anthropic_data.append(
                AnthropicUsageData(
                    api_key_id=api_key,
                    workspace_id="ws_123",
                    model="claude-3-sonnet-20240229",
                    uncached_input_tokens=1000 + i * 10,
                    cached_input_tokens=200,
                    cache_read_input_tokens=150,
                    output_tokens=500 + i * 5,
                    usage_date=date(2022, 1, 1),
                    usage_hour=12
                )
            )

            api_mappings.append(
                APIKeyMapping(
                    api_key_name=api_key,
                    user_email=f"api_user{i}@company.com",
                    description=f"API key {i}",
                    platform="anthropic"
                )
            )

        # Measure performance
        start_time = datetime.now()

        transformer = MultiPlatformTransformer()
        result = transformer.transform_all_usage_data(
            cursor_data=cursor_data,
            anthropic_data=anthropic_data,
            api_key_mappings=api_mappings
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Validate performance
        assert result["success"] is True
        assert len(result["usage_records"]) == 80  # 50 Cursor + 30 Anthropic
        assert processing_time < 10.0  # Should complete within 10 seconds

        # Validate data quality
        assert result["transformation_stats"]["total_input"] == 80
        assert result["transformation_stats"]["total_output"] == 80
        assert len(result["transformation_stats"]["cursor"]["errors"]) == 0
        assert len(result["transformation_stats"]["anthropic"]["errors"]) == 0

    def test_error_handling_and_resilience(self):
        """Test pipeline resilience to various error conditions."""

        # Test with mixed valid/invalid data
        mixed_cursor_data = [
            CursorUsageData(
                email="valid@company.com",
                total_lines_added=1000,
                accepted_lines_added=800,
                total_accepts=25,
                subscription_included_reqs=50,
                usage_based_reqs=10,
                date=datetime(2022, 1, 1)
            ),
            CursorUsageData(
                email="invalid-email",  # Invalid email format
                total_lines_added=-100,  # Invalid: negative value
                accepted_lines_added=800,
                total_accepts=25,
                subscription_included_reqs=50,
                usage_based_reqs=10,
                date=datetime(2022, 1, 1)
            )
        ]

        transformer = MultiPlatformTransformer()
        result = transformer.transform_all_usage_data(cursor_data=mixed_cursor_data)

        # Should handle errors gracefully
        assert result["success"] is True
        # Should only process valid records
        assert len(result["usage_records"]) == 1
        assert result["usage_records"][0].user_email == "valid@company.com"

    @patch('src.shared.monitoring.config')
    def test_system_health_monitoring(self, mock_config):
        """Test comprehensive system health monitoring."""

        # Mock config to avoid actual API calls
        mock_config.cursor_api_key = None
        mock_config.anthropic_api_key = None
        mock_config.sheets_id = None

        # Mock individual health checks
        with patch('src.shared.monitoring.BigQuerySchemaManager') as mock_bq:
            mock_bq_instance = Mock()
            mock_bq_instance.health_check.return_value = True
            mock_bq.return_value = mock_bq_instance

            monitor = SystemMonitor()

            # Register a test health check
            monitor.health_checker.register_check("test_component", Mock(return_value=True))

            # Run health check
            health_report = monitor.run_system_health_check()

            assert health_report.total_checks >= 1
            assert health_report.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]

    def test_attribution_consistency_validation(self):
        """Test attribution consistency across different data sources."""

        # Create test records with potential consistency issues
        records = [
            # Same user across different platforms
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="cursor",
                user_email="john.doe@company.com",
                user_id=None,
                api_key_id=None,
                model=None,
                workspace_id=None,
                input_tokens=0,
                output_tokens=0,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=1000,
                lines_of_code_accepted=800,
                acceptance_rate=0.8,
                total_accepts=25,
                subscription_requests=50,
                usage_based_requests=10,
                ingest_date=date.today(),
                request_id="test1"
            ),
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="anthropic_api",
                user_email="john.doe@company.com",  # Same user
                user_id=None,
                api_key_id="key_123",
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=1000,
                output_tokens=500,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=0,
                lines_of_code_accepted=0,
                acceptance_rate=None,
                total_accepts=0,
                subscription_requests=1,
                usage_based_requests=0,
                ingest_date=date.today(),
                request_id="test2"
            )
        ]

        # Test attribution consistency
        with patch('src.processing.attribution.GoogleSheetsClient'):
            attribution_engine = UserAttributionEngine()
            consistency_result = attribution_engine.validate_attribution_consistency(records)

            # Should detect multi-platform user
            assert consistency_result["total_users"] == 1
            assert "john.doe@company.com" in consistency_result["multi_platform_users"]
            assert consistency_result["multi_platform_count"] == 1

            # Should validate that same user has consistent attribution
            user_platforms = consistency_result["multi_platform_users"]["john.doe@company.com"]
            assert "cursor" in user_platforms
            assert "anthropic_api" in user_platforms

    def test_cost_reconciliation_ranges(self):
        """Test cost reconciliation against expected ranges."""

        # Create cost data within expected ranges
        cost_data = [
            {"cost_usd": 50.00, "user_email": "user1@company.com"},
            {"cost_usd": 75.50, "user_email": "user2@company.com"},
            {"cost_usd": 120.25, "user_email": "user3@company.com"}
        ]

        # Test cost validation
        from src.processing.validator import DataQualityValidator

        validator = DataQualityValidator()

        # Test against reasonable monthly cost range ($20-$300 per user)
        expected_range = (20.0, 300.0)
        cost_issues = validator.validate_cost_reconciliation(cost_data, expected_range)

        # All costs should be within range
        assert len(cost_issues) == 0

        # Test with costs outside range
        extreme_cost_data = [
            {"cost_usd": 500.00, "user_email": "heavy_user@company.com"},  # Above range
            {"cost_usd": 0.01, "user_email": "light_user@company.com"}   # Below range
        ]

        extreme_issues = validator.validate_cost_reconciliation(extreme_cost_data, expected_range)
        assert len(extreme_issues) > 0


from src.processing.transformer import UsageFactRecord