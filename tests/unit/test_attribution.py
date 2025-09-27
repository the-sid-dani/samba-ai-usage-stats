"""Unit tests for user attribution system."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date

from src.processing.attribution import (
    UserAttributionEngine, AttributionMethod, AttributionResult, AttributionReport
)
from src.processing.transformer import UsageFactRecord
from src.ingestion.sheets_client import APIKeyMapping


@pytest.fixture
def mock_sheets_client():
    """Mock Google Sheets client."""
    mock_client = Mock()
    mock_client.health_check.return_value = True
    mock_client.validate_sheet_format.return_value = {"validation_passed": True}
    return mock_client


@pytest.fixture
def attribution_engine(mock_sheets_client):
    """Create UserAttributionEngine with mocked sheets client."""
    return UserAttributionEngine(mock_sheets_client)


@pytest.fixture
def sample_api_key_mappings():
    """Sample API key mappings."""
    return [
        APIKeyMapping(
            api_key_name="key_123",
            user_email="john.doe@company.com",
            description="Production Claude API key",
            platform="anthropic"
        ),
        APIKeyMapping(
            api_key_name="key_789",
            user_email="jane.smith@company.com",
            description="Development Claude API key",
            platform="anthropic"
        )
    ]


@pytest.fixture
def sample_usage_records():
    """Sample usage fact records."""
    return [
        UsageFactRecord(
            usage_date=date(2022, 1, 1),
            platform="cursor",
            user_email="user1@company.com",
            user_id=None,
            api_key_id=None,
            model=None,
            workspace_id=None,
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            cache_read_tokens=0,
            sessions=1,
            lines_of_code_added=100,
            lines_of_code_accepted=80,
            acceptance_rate=0.8,
            total_accepts=5,
            subscription_requests=10,
            usage_based_requests=2,
            ingest_date=date.today(),
            request_id="test1"
        ),
        UsageFactRecord(
            usage_date=date(2022, 1, 1),
            platform="anthropic_api",
            user_email="",
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


class TestUserAttributionEngine:
    """Test cases for UserAttributionEngine."""

    def test_init_with_sheets_client(self, mock_sheets_client):
        """Test initialization with provided sheets client."""
        engine = UserAttributionEngine(mock_sheets_client)
        assert engine.sheets_client == mock_sheets_client

    def test_init_without_sheets_client(self):
        """Test initialization creates default sheets client."""
        with patch('src.processing.attribution.GoogleSheetsClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            engine = UserAttributionEngine()
            assert engine.sheets_client == mock_client

    def test_get_api_key_mappings_cache(self, attribution_engine, sample_api_key_mappings):
        """Test API key mappings caching."""
        attribution_engine.sheets_client.get_api_key_mappings.return_value = sample_api_key_mappings

        # First call should fetch from sheets
        result1 = attribution_engine._get_api_key_mappings()
        # Second call should use cache
        result2 = attribution_engine._get_api_key_mappings()

        assert result1 == sample_api_key_mappings
        assert result2 == sample_api_key_mappings
        # Should only call sheets client once due to caching
        attribution_engine.sheets_client.get_api_key_mappings.assert_called_once()

    def test_get_api_key_mappings_force_refresh(self, attribution_engine, sample_api_key_mappings):
        """Test forcing cache refresh."""
        attribution_engine.sheets_client.get_api_key_mappings.return_value = sample_api_key_mappings

        # First call
        attribution_engine._get_api_key_mappings()
        # Force refresh
        attribution_engine._get_api_key_mappings(force_refresh=True)

        # Should call sheets client twice
        assert attribution_engine.sheets_client.get_api_key_mappings.call_count == 2

    def test_attribute_user_direct_email(self, attribution_engine, sample_usage_records):
        """Test user attribution with direct email (Cursor)."""
        cursor_record = sample_usage_records[0]  # Has user_email populated

        result = attribution_engine.attribute_user(cursor_record, [])

        assert result.user_email == "user1@company.com"
        assert result.method == AttributionMethod.DIRECT_EMAIL
        assert result.confidence == 0.95
        assert result.source == "cursor"
        assert len(result.warnings) == 0

    def test_attribute_user_api_key_mapping(self, attribution_engine, sample_usage_records, sample_api_key_mappings):
        """Test user attribution via API key mapping."""
        anthropic_record = sample_usage_records[1]  # Has api_key_id

        result = attribution_engine.attribute_user(anthropic_record, sample_api_key_mappings)

        assert result.user_email == "john.doe@company.com"
        assert result.method == AttributionMethod.API_KEY_MAPPING
        assert result.confidence == 0.90
        assert result.source == "google_sheets"

    def test_attribute_user_no_mapping(self, attribution_engine, sample_usage_records):
        """Test user attribution when no mapping exists."""
        anthropic_record = sample_usage_records[1]
        anthropic_record.api_key_id = "unmapped_key"

        result = attribution_engine.attribute_user(anthropic_record, [])

        assert result.user_email == "unknown@unattributed.com"
        assert result.method == AttributionMethod.FALLBACK_UNKNOWN
        assert result.confidence == 0.0
        assert len(result.warnings) > 0

    def test_attribute_user_invalid_email(self, attribution_engine):
        """Test attribution with invalid email format."""
        invalid_record = UsageFactRecord(
            usage_date=date(2022, 1, 1),
            platform="cursor",
            user_email="invalid-email-format",  # No @ symbol
            user_id=None,
            api_key_id=None,
            model=None,
            workspace_id=None,
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            cache_read_tokens=0,
            sessions=1,
            lines_of_code_added=100,
            lines_of_code_accepted=80,
            acceptance_rate=0.8,
            total_accepts=5,
            subscription_requests=10,
            usage_based_requests=2,
            ingest_date=date.today(),
            request_id="test"
        )

        result = attribution_engine.attribute_user(invalid_record, [])

        assert result.method == AttributionMethod.FALLBACK_UNKNOWN
        assert len(result.warnings) > 0
        assert "Invalid email format" in str(result.warnings)

    def test_get_expected_platforms(self, attribution_engine):
        """Test platform mapping logic."""
        assert attribution_engine._get_expected_platforms("cursor") == ["cursor"]
        assert "anthropic_api" in attribution_engine._get_expected_platforms("anthropic")
        assert "anthropic_code" in attribution_engine._get_expected_platforms("anthropic")

    def test_attribute_batch_success(self, attribution_engine, sample_usage_records, sample_api_key_mappings):
        """Test successful batch attribution."""
        attribution_engine.sheets_client.get_api_key_mappings.return_value = sample_api_key_mappings

        attributed_records, report = attribution_engine.attribute_batch(sample_usage_records)

        assert len(attributed_records) == 2
        assert report.total_records == 2
        assert report.attributed_records == 2
        assert report.attribution_rate == 1.0
        assert report.method_breakdown[AttributionMethod.DIRECT_EMAIL.value] == 1
        assert report.method_breakdown[AttributionMethod.API_KEY_MAPPING.value] == 1

    def test_attribute_batch_with_unmapped_keys(self, attribution_engine, sample_usage_records):
        """Test batch attribution with unmapped API keys."""
        # Modify record to have unmapped key
        sample_usage_records[1].api_key_id = "unmapped_key"
        attribution_engine.sheets_client.get_api_key_mappings.return_value = []

        attributed_records, report = attribution_engine.attribute_batch(sample_usage_records)

        assert len(attributed_records) == 2
        assert report.attribution_rate < 1.0
        assert "unmapped_key" in report.unmapped_api_keys
        assert len(report.recommendations) > 0

    def test_validate_attribution_consistency(self, attribution_engine, sample_usage_records):
        """Test attribution consistency validation."""
        # Add a record for same user on different platform
        multi_platform_record = UsageFactRecord(
            usage_date=date(2022, 1, 1),
            platform="anthropic_api",
            user_email="user1@company.com",  # Same user as first record
            user_id=None,
            api_key_id="key_456",
            model="claude-3-sonnet-20240229",
            workspace_id=None,
            input_tokens=500,
            output_tokens=250,
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
            request_id="test3"
        )

        records = sample_usage_records + [multi_platform_record]
        result = attribution_engine.validate_attribution_consistency(records)

        assert result["total_users"] == 2  # user1@company.com and john.doe@company.com
        assert "user1@company.com" in result["multi_platform_users"]
        assert result["multi_platform_count"] == 1

    def test_validate_email_domains(self, attribution_engine, sample_usage_records):
        """Test email domain validation."""
        allowed_domains = ["company.com"]

        result = attribution_engine.validate_email_domains(sample_usage_records, allowed_domains)

        assert result["total_records"] == 2
        assert "company.com" in result["domain_distribution"]
        assert len(result["invalid_domains"]) == 0  # All emails from allowed domain

    def test_validate_email_domains_invalid(self, attribution_engine):
        """Test email domain validation with invalid domains."""
        records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="cursor",
                user_email="user@external.com",  # Not in allowed domains
                user_id=None,
                api_key_id=None,
                model=None,
                workspace_id=None,
                input_tokens=0,
                output_tokens=0,
                cached_input_tokens=0,
                cache_read_tokens=0,
                sessions=1,
                lines_of_code_added=100,
                lines_of_code_accepted=80,
                acceptance_rate=0.8,
                total_accepts=5,
                subscription_requests=10,
                usage_based_requests=2,
                ingest_date=date.today(),
                request_id="test"
            )
        ]

        allowed_domains = ["company.com"]
        result = attribution_engine.validate_email_domains(records, allowed_domains)

        assert "external.com" in result["invalid_domains"]

    def test_generate_attribution_summary(self, attribution_engine):
        """Test attribution summary generation."""
        report = AttributionReport(
            total_records=100,
            attributed_records=95,
            attribution_rate=0.95,
            method_breakdown={
                "direct_email": 50,
                "api_key_mapping": 45,
                "fallback_unknown": 5
            },
            unmapped_api_keys={"key1", "key2"},
            attribution_conflicts=[],
            data_quality_issues=["Issue 1"],
            recommendations=["Recommendation 1"]
        )

        summary = attribution_engine.generate_attribution_summary(report)

        assert "User Attribution Summary" in summary
        assert "Total Records: 100" in summary
        assert "Attribution Rate: 95.0%" in summary
        assert "Direct Email: 50 (50.0%)" in summary
        assert "Unmapped API Keys (2):" in summary
        assert "Recommendations:" in summary

    def test_resolve_conflicts_most_recent(self, attribution_engine):
        """Test conflict resolution using most recent strategy."""
        conflicts = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="anthropic_api",
                user_email="old@company.com",
                user_id=None,
                api_key_id="conflicted_key",
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=500,
                output_tokens=250,
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
                request_id="test1"
            ),
            UsageFactRecord(
                usage_date=date(2022, 1, 2),  # More recent
                platform="anthropic_api",
                user_email="new@company.com",
                user_id=None,
                api_key_id="conflicted_key",  # Same API key
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=600,
                output_tokens=300,
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

        resolved = attribution_engine.resolve_conflicts(conflicts, "most_recent")

        assert len(resolved) == 2
        # Both records should now have the email from the most recent record
        assert all(record.user_email == "new@company.com" for record in resolved)

    def test_audit_attribution_changes(self, attribution_engine):
        """Test attribution change auditing."""
        old_records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="anthropic_api",
                user_email="old@company.com",
                user_id=None,
                api_key_id="key_123",
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=500,
                output_tokens=250,
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
                request_id="test"
            )
        ]

        new_records = [
            UsageFactRecord(
                usage_date=date(2022, 1, 1),
                platform="anthropic_api",
                user_email="new@company.com",  # Changed email
                user_id=None,
                api_key_id="key_123",
                model="claude-3-sonnet-20240229",
                workspace_id=None,
                input_tokens=500,
                output_tokens=250,
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
                request_id="test"
            )
        ]

        audit = attribution_engine.audit_attribution_changes(old_records, new_records)

        assert audit["total_changes"] == 1
        assert len(audit["attribution_changes"]) == 1
        assert audit["attribution_changes"][0]["old_email"] == "old@company.com"
        assert audit["attribution_changes"][0]["new_email"] == "new@company.com"

    def test_health_check_success(self, attribution_engine):
        """Test successful health check."""
        attribution_engine.sheets_client.get_api_key_mappings.return_value = [Mock()]

        result = attribution_engine.health_check()

        assert result is True

    def test_health_check_failure(self, attribution_engine):
        """Test health check failure."""
        attribution_engine.sheets_client.health_check.return_value = False

        result = attribution_engine.health_check()

        assert result is False


class TestAttributionResult:
    """Test cases for AttributionResult dataclass."""

    def test_attribution_result_creation(self):
        """Test AttributionResult creation."""
        result = AttributionResult(
            user_email="test@example.com",
            method=AttributionMethod.DIRECT_EMAIL,
            confidence=0.95,
            source="cursor",
            warnings=["Warning 1"]
        )

        assert result.user_email == "test@example.com"
        assert result.method == AttributionMethod.DIRECT_EMAIL
        assert result.confidence == 0.95
        assert result.source == "cursor"
        assert len(result.warnings) == 1


class TestAttributionReport:
    """Test cases for AttributionReport dataclass."""

    def test_attribution_report_creation(self):
        """Test AttributionReport creation."""
        report = AttributionReport(
            total_records=100,
            attributed_records=95,
            attribution_rate=0.95,
            method_breakdown={"direct_email": 50, "api_key_mapping": 45},
            unmapped_api_keys={"key1", "key2"},
            attribution_conflicts=[],
            data_quality_issues=["Issue 1"],
            recommendations=["Rec 1"]
        )

        assert report.total_records == 100
        assert report.attributed_records == 95
        assert report.attribution_rate == 0.95
        assert len(report.unmapped_api_keys) == 2
        assert len(report.data_quality_issues) == 1
        assert len(report.recommendations) == 1