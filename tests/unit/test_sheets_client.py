"""Unit tests for Google Sheets API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from google.auth.exceptions import DefaultCredentialsError

from src.ingestion.sheets_client import (
    GoogleSheetsClient, SheetsAPIError, APIKeyMapping
)


@pytest.fixture
def mock_config():
    """Mock configuration with test sheets ID."""
    with patch('src.ingestion.sheets_client.config') as mock:
        mock.sheets_id = "test-sheets-id-123"
        yield mock


@pytest.fixture
def mock_service():
    """Mock Google Sheets API service."""
    with patch('src.ingestion.sheets_client.build') as mock_build:
        mock_service = Mock()
        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_credentials():
    """Mock Google authentication."""
    with patch('src.ingestion.sheets_client.default') as mock_default:
        mock_creds = Mock()
        mock_default.return_value = (mock_creds, "test-project")
        yield mock_default


@pytest.fixture
def sheets_client(mock_config, mock_service, mock_credentials):
    """Create GoogleSheetsClient with mocked dependencies."""
    return GoogleSheetsClient()


@pytest.fixture
def sample_sheet_data():
    """Sample Google Sheets response data."""
    return {
        'values': [
            ['api_key_name', 'email', 'description'],  # Header row
            ['cursor-dev-key-1', 'john.doe@company.com', 'Development Cursor key'],
            ['anthropic-prod-key-2', 'jane.smith@company.com', 'Production Claude API key'],
            ['cursor-team-key-3', 'team-lead@company.com', 'Team shared Cursor key'],
            ['', '', ''],  # Empty row
            ['anthropic-test-key-4', 'developer@company.com', 'Testing Claude integration']
        ]
    }


class TestGoogleSheetsClient:
    """Test cases for GoogleSheetsClient."""

    def test_init_success(self, mock_config, mock_service, mock_credentials):
        """Test successful client initialization."""
        client = GoogleSheetsClient()
        assert client.sheets_id == "test-sheets-id-123"
        assert client.service == mock_service

    def test_init_no_sheets_id(self):
        """Test initialization fails without sheets ID."""
        with patch('src.ingestion.sheets_client.config') as mock_config:
            mock_config.sheets_id = None
            with pytest.raises(SheetsAPIError, match="Google Sheets ID not found"):
                GoogleSheetsClient()

    def test_init_auth_failure(self, mock_config):
        """Test initialization fails with authentication error."""
        with patch('src.ingestion.sheets_client.default') as mock_default:
            mock_default.side_effect = DefaultCredentialsError("Auth failed")
            with pytest.raises(SheetsAPIError, match="Authentication failed"):
                GoogleSheetsClient()

    def test_validate_email_valid(self, sheets_client):
        """Test email validation with valid emails."""
        valid_emails = [
            "user@example.com",
            "user.name@company.co.uk",
            "test+tag@domain.org",
            "123@test.com"
        ]

        for email in valid_emails:
            assert sheets_client._validate_email(email) is True

    def test_validate_email_invalid(self, sheets_client):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "",
            "   ",
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user name@domain.com",
            None
        ]

        for email in invalid_emails:
            assert sheets_client._validate_email(email) is False

    def test_determine_platform_cursor(self, sheets_client):
        """Test platform determination for Cursor keys."""
        assert sheets_client._determine_platform("cursor-dev-key", "Cursor development") == "cursor"
        assert sheets_client._determine_platform("my-cursor-key", "For Cursor IDE") == "cursor"
        assert sheets_client._determine_platform("dev-key", "CURSOR environment") == "cursor"

    def test_determine_platform_anthropic(self, sheets_client):
        """Test platform determination for Anthropic keys."""
        assert sheets_client._determine_platform("anthropic-key", "Claude API") == "anthropic"
        assert sheets_client._determine_platform("claude-prod", "Production key") == "anthropic"
        assert sheets_client._determine_platform("api-key", "ANTHROPIC testing") == "anthropic"

    def test_determine_platform_default(self, sheets_client):
        """Test platform determination defaults to anthropic."""
        assert sheets_client._determine_platform("unknown-key", "Some description") == "anthropic"
        assert sheets_client._determine_platform("", "") == "anthropic"

    def test_is_header_row_true(self, sheets_client):
        """Test header row detection with typical headers."""
        header_rows = [
            ["api_key_name", "email", "description"],
            ["API Key", "User Email", "Notes"],
            ["key", "user", "desc"],
            ["name", "email", "info"]
        ]

        for header in header_rows:
            assert sheets_client._is_header_row(header) is True

    def test_is_header_row_false(self, sheets_client):
        """Test header row detection with data rows."""
        data_rows = [
            ["prod-api-123", "user@example.com", "Production instance"],
            ["staging-token-456", "dev@company.com", "Development environment"],
            ["", "", ""],
            []
        ]

        for row in data_rows:
            assert sheets_client._is_header_row(row) is False

    def test_get_api_key_mappings_success(self, sheets_client, mock_service, sample_sheet_data):
        """Test successful API key mappings retrieval."""
        # Mock the Sheets API response
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = sample_sheet_data

        mappings = sheets_client.get_api_key_mappings()

        assert len(mappings) == 4  # Excludes header and empty rows

        # Check first mapping
        assert mappings[0].api_key_name == "cursor-dev-key-1"
        assert mappings[0].user_email == "john.doe@company.com"
        assert mappings[0].platform == "cursor"
        assert mappings[0].is_active is True

        # Check second mapping
        assert mappings[1].api_key_name == "anthropic-prod-key-2"
        assert mappings[1].user_email == "jane.smith@company.com"
        assert mappings[1].platform == "anthropic"

    def test_get_api_key_mappings_empty_sheet(self, sheets_client, mock_service):
        """Test handling of empty spreadsheet."""
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = {'values': []}

        mappings = sheets_client.get_api_key_mappings()

        assert len(mappings) == 0

    def test_get_api_key_mappings_no_values(self, sheets_client, mock_service):
        """Test handling of spreadsheet with no values key."""
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = {}

        mappings = sheets_client.get_api_key_mappings()

        assert len(mappings) == 0

    def test_get_api_key_mappings_invalid_data(self, sheets_client, mock_service):
        """Test handling of invalid data in spreadsheet."""
        invalid_data = {
            'values': [
                ['api_key_name', 'email', 'description'],
                ['', 'missing-key@example.com', 'Missing key name'],  # Missing key name
                ['valid-key', 'invalid-email', 'Invalid email'],  # Invalid email
                ['another-key', 'valid@example.com', 'Valid entry']  # Valid entry
            ]
        }

        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = invalid_data

        mappings = sheets_client.get_api_key_mappings()

        assert len(mappings) == 1  # Only the valid entry
        assert mappings[0].api_key_name == "another-key"
        assert mappings[0].user_email == "valid@example.com"

    def test_get_api_key_mappings_api_error(self, sheets_client, mock_service):
        """Test handling of API errors."""
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.side_effect = Exception("API Error")

        with pytest.raises(SheetsAPIError, match="Failed to fetch mappings"):
            sheets_client.get_api_key_mappings()

    def test_get_mapping_by_api_key_found(self, sheets_client, mock_service, sample_sheet_data):
        """Test finding mapping by API key name."""
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = sample_sheet_data

        mapping = sheets_client.get_mapping_by_api_key("cursor-dev-key-1")

        assert mapping is not None
        assert mapping.api_key_name == "cursor-dev-key-1"
        assert mapping.user_email == "john.doe@company.com"
        assert mapping.platform == "cursor"

    def test_get_mapping_by_api_key_not_found(self, sheets_client, mock_service, sample_sheet_data):
        """Test searching for non-existent API key."""
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = sample_sheet_data

        mapping = sheets_client.get_mapping_by_api_key("non-existent-key")

        assert mapping is None

    def test_get_mappings_by_platform(self, sheets_client, mock_service, sample_sheet_data):
        """Test filtering mappings by platform."""
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = sample_sheet_data

        cursor_mappings = sheets_client.get_mappings_by_platform("cursor")
        anthropic_mappings = sheets_client.get_mappings_by_platform("anthropic")

        assert len(cursor_mappings) == 2
        assert len(anthropic_mappings) == 2

        # Verify platform filtering
        for mapping in cursor_mappings:
            assert mapping.platform == "cursor"

        for mapping in anthropic_mappings:
            assert mapping.platform == "anthropic"

    def test_validate_sheet_format_success(self, sheets_client, mock_service, sample_sheet_data):
        """Test sheet format validation with valid data."""
        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = sample_sheet_data

        result = sheets_client.validate_sheet_format()

        assert result["validation_passed"] is True
        assert result["total_mappings"] == 4
        assert result["unique_users"] == 4
        assert len(result["duplicate_keys"]) == 0
        assert "cursor" in result["platform_counts"]
        assert "anthropic" in result["platform_counts"]

    def test_validate_sheet_format_with_duplicates(self, sheets_client, mock_service):
        """Test sheet format validation with duplicate keys."""
        duplicate_data = {
            'values': [
                ['api_key_name', 'email', 'description'],
                ['duplicate-key', 'user1@example.com', 'First instance'],
                ['duplicate-key', 'user2@example.com', 'Second instance'],
                ['unique-key', 'user3@example.com', 'Unique entry']
            ]
        }

        mock_values = mock_service.spreadsheets().values()
        mock_values.get().execute.return_value = duplicate_data

        result = sheets_client.validate_sheet_format()

        assert result["validation_passed"] is False
        assert len(result["duplicate_keys"]) == 1
        assert "duplicate-key" in result["duplicate_keys"]
        assert len(result["warnings"]) > 0

    def test_health_check_success(self, sheets_client, mock_service):
        """Test successful health check."""
        mock_spreadsheets = mock_service.spreadsheets()
        mock_spreadsheets.get().execute.return_value = {
            'properties': {'title': 'API Key Mappings'}
        }

        result = sheets_client.health_check()

        assert result is True

    def test_health_check_failure(self, sheets_client, mock_service):
        """Test health check failure."""
        mock_spreadsheets = mock_service.spreadsheets()
        mock_spreadsheets.get().execute.side_effect = Exception("Access denied")

        result = sheets_client.health_check()

        assert result is False

    def test_create_sample_template(self, sheets_client):
        """Test sample template creation."""
        template = sheets_client.create_sample_template()

        assert isinstance(template, str)
        assert "api_key_name,email,description" in template
        assert "cursor-dev-key-1,john.doe@company.com" in template
        assert "anthropic-prod-key-2,jane.smith@company.com" in template


class TestAPIKeyMapping:
    """Test cases for APIKeyMapping dataclass."""

    def test_api_key_mapping_creation(self):
        """Test APIKeyMapping creation."""
        mapping = APIKeyMapping(
            api_key_name="test-key",
            user_email="user@example.com",
            description="Test API key",
            platform="anthropic",
            is_active=True
        )

        assert mapping.api_key_name == "test-key"
        assert mapping.user_email == "user@example.com"
        assert mapping.description == "Test API key"
        assert mapping.platform == "anthropic"
        assert mapping.is_active is True

    def test_api_key_mapping_default_active(self):
        """Test APIKeyMapping with default is_active value."""
        mapping = APIKeyMapping(
            api_key_name="test-key",
            user_email="user@example.com",
            description="Test API key",
            platform="anthropic"
        )

        assert mapping.is_active is True  # Default value


class TestSheetsAPIError:
    """Test cases for SheetsAPIError exception."""

    def test_sheets_api_error(self):
        """Test SheetsAPIError creation."""
        error = SheetsAPIError("Test error message")
        assert str(error) == "Test error message"