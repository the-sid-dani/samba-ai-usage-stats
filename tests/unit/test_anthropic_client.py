"""Unit tests for Anthropic API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
import requests

from src.ingestion.anthropic_client import (
    AnthropicClient, AnthropicAPIError, AnthropicUsageData, AnthropicCostData, _sanitize_sensitive_data
)


@pytest.fixture
def mock_config():
    """Mock configuration with test API key."""
    with patch('src.ingestion.anthropic_client.config') as mock:
        mock.anthropic_api_key = "test-anthropic-api-key"
        yield mock


@pytest.fixture
def anthropic_client(mock_config):
    """Create AnthropicClient instance with mocked config."""
    return AnthropicClient()


@pytest.fixture
def sample_usage_response():
    """Sample usage API response data with real nested structure."""
    return {
        "data": [
            {
                "starting_at": "2022-01-01T00:00:00Z",
                "ending_at": "2022-01-02T00:00:00Z",
                "api_key_id": "key_123",
                "workspace_id": "ws_456",
                "model": "claude-3-sonnet-20240229",
                "results": [
                    {
                        "uncached_input_tokens": 118459752,
                        "cache_creation": {"ephemeral_1h_input_tokens": 200},
                        "cache_read_input_tokens": 100094909,
                        "output_tokens": 5430933
                    }
                ]
            },
            {
                "starting_at": "2022-01-01T00:00:00Z",
                "ending_at": "2022-01-02T00:00:00Z",
                "api_key_id": "key_789",
                "workspace_id": "ws_456",
                "model": "claude-3-haiku-20240307",
                "results": [
                    {
                        "uncached_input_tokens": 800,
                        "cache_creation": {"ephemeral_1h_input_tokens": 100},
                        "cache_read_input_tokens": 50,
                        "output_tokens": 300
                    }
                ]
            }
        ],
        "next_page_token": None
    }


@pytest.fixture
def sample_cost_response():
    """Sample cost API response data with real nested structure."""
    return {
        "data": [
            {
                "starting_at": "2022-01-01T00:00:00Z",
                "ending_at": "2022-01-02T00:00:00Z",
                "api_key_id": "key_123",
                "workspace_id": "ws_456",
                "model": "claude-3-sonnet-20240229",
                "results": [
                    {
                        "currency": "USD",
                        "amount": "187515.353295",
                        "workspace_id": "ws_456"
                    }
                ]
            }
        ],
        "next_page_token": None
    }


class TestAnthropicClient:
    """Test cases for AnthropicClient."""

    def test_init_success(self, mock_config):
        """Test successful client initialization."""
        client = AnthropicClient()
        assert client.api_key == "test-anthropic-api-key"

    def test_init_no_api_key(self):
        """Test initialization fails without API key."""
        with patch('src.ingestion.anthropic_client.config') as mock_config:
            mock_config.anthropic_api_key = None
            with pytest.raises(AnthropicAPIError, match="Anthropic API key not found"):
                AnthropicClient()

    @patch('src.ingestion.anthropic_client.requests.get')
    def test_make_request_success(self, mock_get, anthropic_client, sample_usage_response):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_usage_response
        mock_get.return_value = mock_response

        result = anthropic_client._make_request("/test-endpoint")

        assert result == sample_usage_response
        mock_get.assert_called_once()

    @patch('src.ingestion.anthropic_client.requests.get')
    def test_make_request_rate_limit_retry(self, mock_get, anthropic_client):
        """Test retry logic for rate limiting."""
        # First call returns 429, second call succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}

        mock_get.side_effect = [mock_response_429, mock_response_200]

        with patch('src.ingestion.anthropic_client.time.sleep') as mock_sleep:
            result = anthropic_client._make_request("/test-endpoint")

        assert result == {"success": True}
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(2)  # Exponential backoff: 2^(0+1) = 2

    @patch('src.ingestion.anthropic_client.requests.get')
    def test_make_request_client_error_no_retry(self, mock_get, anthropic_client):
        """Test no retry for client errors."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        with pytest.raises(AnthropicAPIError) as exc_info:
            anthropic_client._make_request("/test-endpoint")

        assert "400" in str(exc_info.value)
        assert mock_get.call_count == 1  # No retry for client errors

    @patch('src.ingestion.anthropic_client.requests.get')
    def test_make_request_api_key_sanitization(self, mock_get, anthropic_client):
        """Test that API keys are sanitized from error messages."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized: Invalid API key sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567_test-key-end"
        mock_get.return_value = mock_response

        with pytest.raises(AnthropicAPIError) as exc_info:
            anthropic_client._make_request("/test-endpoint")

        error_message = str(exc_info.value)
        response_text = exc_info.value.response_text

        # Verify API key is redacted from error message
        assert "sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567_test-key-end" not in error_message
        assert "[REDACTED_CREDENTIAL]" in error_message

        # Verify API key is redacted from stored response text
        assert "sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567_test-key-end" not in response_text
        assert "[REDACTED_CREDENTIAL]" in response_text

        # Verify status code is still preserved
        assert "401" in error_message
        assert exc_info.value.status_code == 401

    def test_validate_date_range_success(self, anthropic_client):
        """Test successful date range validation."""
        start_date = date(2022, 1, 1)
        end_date = date(2022, 1, 7)

        # Should not raise exception
        anthropic_client._validate_date_range(start_date, end_date)

    def test_validate_date_range_invalid_order(self, anthropic_client):
        """Test date range validation with invalid order."""
        start_date = date(2022, 1, 7)
        end_date = date(2022, 1, 1)

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            anthropic_client._validate_date_range(start_date, end_date)

    def test_validate_date_range_too_long(self, anthropic_client):
        """Test date range validation with range too long."""
        start_date = date(2022, 1, 1)
        end_date = date(2022, 2, 1)  # 31 days exactly (should fail with >=)

        with pytest.raises(ValueError, match="Date range cannot exceed 31 days"):
            anthropic_client._validate_date_range(start_date, end_date)

    def test_chunk_date_range_small_range(self, anthropic_client):
        """Test date range chunking with small range."""
        start_date = date(2022, 1, 1)
        end_date = date(2022, 1, 7)

        chunks = list(anthropic_client._chunk_date_range(start_date, end_date))

        assert len(chunks) == 1
        assert chunks[0] == (start_date, end_date)

    def test_chunk_date_range_large_range(self, anthropic_client):
        """Test date range chunking with large range."""
        start_date = date(2022, 1, 1)
        end_date = date(2022, 3, 1)  # 59 days

        chunks = list(anthropic_client._chunk_date_range(start_date, end_date))

        assert len(chunks) == 2
        assert chunks[0][0] == start_date
        assert chunks[1][1] == end_date

    @patch.object(AnthropicClient, '_paginate_request')
    def test_get_usage_data_success(self, mock_paginate, anthropic_client, sample_usage_response):
        """Test successful usage data retrieval."""
        mock_paginate.return_value = [sample_usage_response]

        start_date = date(2022, 1, 1)
        end_date = date(2022, 1, 2)

        result = anthropic_client.get_usage_data(start_date, end_date)

        assert len(result) == 2
        assert isinstance(result[0], AnthropicUsageData)
        assert result[0].api_key_id == "key_123"
        assert result[0].model == "claude-3-sonnet-20240229"
        assert result[0].uncached_input_tokens == 118459752  # Real API numbers
        assert result[0].cached_input_tokens == 200  # From cache_creation
        assert result[0].cache_read_input_tokens == 100094909
        assert result[0].output_tokens == 5430933
        assert result[1].api_key_id == "key_789"
        assert result[1].uncached_input_tokens == 800

    @patch.object(AnthropicClient, '_paginate_request')
    def test_get_cost_data_success(self, mock_paginate, anthropic_client, sample_cost_response):
        """Test successful cost data retrieval."""
        mock_paginate.return_value = [sample_cost_response]

        start_date = date(2022, 1, 1)
        end_date = date(2022, 1, 2)

        result = anthropic_client.get_cost_data(start_date, end_date)

        assert len(result) == 1  # Real API provides total cost, not breakdown
        assert isinstance(result[0], AnthropicCostData)
        assert result[0].api_key_id == "key_123"
        assert result[0].model == "claude-3-sonnet-20240229"
        assert result[0].cost_usd == 187515.353295  # Real API amount
        assert result[0].cost_type == "total_cost"  # Real API structure
        assert result[0].workspace_id == "ws_456"

    @patch.object(AnthropicClient, '_make_request')
    def test_paginate_request_single_page(self, mock_make_request, anthropic_client):
        """Test pagination with single page."""
        mock_make_request.return_value = {"data": ["item1"], "next_page_token": None}

        result = list(anthropic_client._paginate_request("/test", {}))

        assert len(result) == 1
        assert result[0]["data"] == ["item1"]
        mock_make_request.assert_called_once()

    @patch.object(AnthropicClient, '_make_request')
    def test_paginate_request_multiple_pages(self, mock_make_request, anthropic_client):
        """Test pagination with multiple pages."""
        # First page has next_page_token, second page doesn't
        mock_make_request.side_effect = [
            {"data": ["item1"], "next_page_token": "token123"},
            {"data": ["item2"], "next_page_token": None}
        ]

        result = list(anthropic_client._paginate_request("/test", {}))

        assert len(result) == 2
        assert result[0]["data"] == ["item1"]
        assert result[1]["data"] == ["item2"]
        assert mock_make_request.call_count == 2

    @patch.object(AnthropicClient, 'get_usage_data')
    def test_get_recent_usage(self, mock_get_usage, anthropic_client):
        """Test get_recent_usage method."""
        mock_data = [Mock(spec=AnthropicUsageData)]
        mock_get_usage.return_value = mock_data

        result = anthropic_client.get_recent_usage(days=3)

        assert result == mock_data
        mock_get_usage.assert_called_once()

        # Check that date range is approximately correct
        call_args = mock_get_usage.call_args[0]
        start_date, end_date = call_args
        date_diff = (end_date - start_date).days
        assert date_diff == 3

    @patch.object(AnthropicClient, 'get_cost_data')
    def test_get_recent_costs(self, mock_get_cost, anthropic_client):
        """Test get_recent_costs method."""
        mock_data = [Mock(spec=AnthropicCostData)]
        mock_get_cost.return_value = mock_data

        result = anthropic_client.get_recent_costs(days=5)

        assert result == mock_data
        mock_get_cost.assert_called_once()

        # Check that date range is approximately correct
        call_args = mock_get_cost.call_args[0]
        start_date, end_date = call_args
        date_diff = (end_date - start_date).days
        assert date_diff == 5

    @patch.object(AnthropicClient, 'get_recent_usage')
    def test_health_check_success(self, mock_get_recent, anthropic_client):
        """Test successful health check."""
        mock_get_recent.return_value = [Mock()]

        result = anthropic_client.health_check()

        assert result is True
        mock_get_recent.assert_called_once_with(days=1)

    @patch.object(AnthropicClient, 'get_recent_usage')
    def test_health_check_failure(self, mock_get_recent, anthropic_client):
        """Test health check failure."""
        mock_get_recent.side_effect = AnthropicAPIError("API Error")

        result = anthropic_client.health_check()

        assert result is False

    def test_get_supported_models(self, anthropic_client):
        """Test getting supported models."""
        models = anthropic_client.get_supported_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "claude-3-sonnet-20240229" in models
        assert "claude-3-haiku-20240307" in models


class TestAnthropicUsageData:
    """Test cases for AnthropicUsageData dataclass."""

    def test_usage_data_creation(self):
        """Test AnthropicUsageData creation."""
        usage_date = date.today()
        data = AnthropicUsageData(
            api_key_id="key_123",
            workspace_id="ws_456",
            model="claude-3-sonnet-20240229",
            uncached_input_tokens=1000,
            cached_input_tokens=200,
            cache_read_input_tokens=150,
            output_tokens=500,
            usage_date=usage_date,
            usage_hour=12
        )

        assert data.api_key_id == "key_123"
        assert data.workspace_id == "ws_456"
        assert data.model == "claude-3-sonnet-20240229"
        assert data.uncached_input_tokens == 1000
        assert data.cached_input_tokens == 200
        assert data.cache_read_input_tokens == 150
        assert data.output_tokens == 500
        assert data.usage_date == usage_date
        assert data.usage_hour == 12


class TestAnthropicCostData:
    """Test cases for AnthropicCostData dataclass."""

    def test_cost_data_creation(self):
        """Test AnthropicCostData creation."""
        cost_date = date.today()
        data = AnthropicCostData(
            api_key_id="key_123",
            workspace_id="ws_456",
            model="claude-3-sonnet-20240229",
            cost_usd=0.015,
            cost_type="input_tokens",
            cost_date=cost_date,
            cost_hour=14
        )

        assert data.api_key_id == "key_123"
        assert data.workspace_id == "ws_456"
        assert data.model == "claude-3-sonnet-20240229"
        assert data.cost_usd == 0.015
        assert data.cost_type == "input_tokens"
        assert data.cost_date == cost_date
        assert data.cost_hour == 14


class TestAnthropicAPIError:
    """Test cases for AnthropicAPIError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = AnthropicAPIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.response_text is None

    def test_error_with_details(self):
        """Test error with status code and response text."""
        error = AnthropicAPIError("API Error", status_code=400, response_text="Bad Request")
        assert str(error) == "API Error"
        assert error.status_code == 400
        assert error.response_text == "Bad Request"


class TestSanitizeSensitiveData:
    """Test cases for sensitive data sanitization function."""

    def test_sanitize_anthropic_api_key(self):
        """Test sanitization of Anthropic API keys."""
        text = "Error: Invalid API key sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
        result = _sanitize_sensitive_data(text)
        assert "sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567" not in result
        assert "[REDACTED_CREDENTIAL]" in result
        assert "Error: Invalid API key" in result

    def test_sanitize_generic_api_key_patterns(self):
        """Test sanitization of generic API key patterns."""
        test_cases = [
            'api_key=abc123def456ghi789jkl012mno345',
            '"api-key": "test-key-1234567890abcdef"',
            'authorization=Bearer sk-test1234567890abcdef',
            'token: "jwt-token-abc123def456ghi789"'
        ]

        for text in test_cases:
            result = _sanitize_sensitive_data(text)
            assert "[REDACTED_CREDENTIAL]" in result
            # Verify key parts are removed but structure remains
            assert "api" in result.lower() or "auth" in result.lower() or "token" in result.lower()

    def test_sanitize_multiple_credentials(self):
        """Test sanitization when multiple credentials are present."""
        text = "Error: api_key=secret123456789abcdef and token=another_secret456789abcdef failed"
        result = _sanitize_sensitive_data(text)
        assert "secret123456789abcdef" not in result
        assert "another_secret456789abcdef" not in result
        assert result.count("[REDACTED_CREDENTIAL]") == 2

    def test_sanitize_empty_or_none_text(self):
        """Test sanitization handles empty/None input."""
        assert _sanitize_sensitive_data("") == ""
        assert _sanitize_sensitive_data(None) is None

    def test_sanitize_text_without_credentials(self):
        """Test that normal text passes through unchanged."""
        text = "This is a normal error message with no sensitive data."
        result = _sanitize_sensitive_data(text)
        assert result == text
        assert "[REDACTED_CREDENTIAL]" not in result

    def test_sanitize_preserves_context(self):
        """Test that sanitization preserves error context while removing credentials."""
        text = "Authentication failed: Invalid API key sk-ant-test123456789abcdef. Please check your credentials."
        result = _sanitize_sensitive_data(text)
        assert "Authentication failed" in result
        assert "Invalid API key" in result
        assert "Please check your credentials" in result
        assert "sk-ant-test123456789abcdef" not in result
        assert "[REDACTED_CREDENTIAL]" in result