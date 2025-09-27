"""Unit tests for Cursor API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests

from src.ingestion.cursor_client import CursorClient, CursorAPIError, CursorUsageData


@pytest.fixture
def mock_config():
    """Mock configuration with test API key."""
    with patch('src.ingestion.cursor_client.config') as mock:
        mock.cursor_api_key = "test-cursor-api-key"
        yield mock


@pytest.fixture
def cursor_client(mock_config):
    """Create CursorClient instance with mocked config."""
    return CursorClient()


@pytest.fixture
def sample_api_response():
    """Sample API response data."""
    return {
        "data": [
            {
                "email": "user1@example.com",
                "totalLinesAdded": 1500,
                "acceptedLinesAdded": 1200,
                "totalAccepts": 45,
                "subscriptionIncludedReqs": 100,
                "usageBasedReqs": 25,
                "timestamp": 1640995200  # 2022-01-01 00:00:00 UTC
            },
            {
                "email": "user2@example.com",
                "totalLinesAdded": 800,
                "acceptedLinesAdded": 600,
                "totalAccepts": 22,
                "subscriptionIncludedReqs": 50,
                "usageBasedReqs": 10,
                "timestamp": 1640995200
            }
        ]
    }


class TestCursorClient:
    """Test cases for CursorClient."""

    def test_init_success(self, mock_config):
        """Test successful client initialization."""
        client = CursorClient()
        assert client.api_key == "test-cursor-api-key"

    def test_init_no_api_key(self):
        """Test initialization fails without API key."""
        with patch('src.ingestion.cursor_client.config') as mock_config:
            mock_config.cursor_api_key = None
            with pytest.raises(CursorAPIError, match="Cursor API key not found"):
                CursorClient()

    @patch('src.ingestion.cursor_client.requests.post')
    def test_make_request_success(self, mock_post, cursor_client, sample_api_response):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_api_response
        mock_post.return_value = mock_response

        data = {"startDate": 1640995200000, "endDate": 1641081600000}
        result = cursor_client._make_request("/test-endpoint", data)

        assert result == sample_api_response
        mock_post.assert_called_once_with(
            "https://api.cursor.com/test-endpoint",
            auth=("test-cursor-api-key", ""),
            headers={"Content-Type": "application/json"},
            json=data,
            timeout=30
        )

    @patch('src.ingestion.cursor_client.requests.post')
    def test_make_request_rate_limit_retry(self, mock_post, cursor_client):
        """Test retry logic for rate limiting."""
        # First call returns 429, second call succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}

        mock_post.side_effect = [mock_response_429, mock_response_200]

        with patch('src.ingestion.cursor_client.time.sleep') as mock_sleep:
            result = cursor_client._make_request("/test-endpoint")

        assert result == {"success": True}
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(2)  # Exponential backoff: 2^(0+1) = 2

    @patch('src.ingestion.cursor_client.requests.post')
    def test_make_request_server_error_retry(self, mock_post, cursor_client):
        """Test retry logic for server errors."""
        # First call returns 500, second call succeeds
        mock_response_500 = Mock()
        mock_response_500.status_code = 500

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}

        mock_post.side_effect = [mock_response_500, mock_response_200]

        with patch('src.ingestion.cursor_client.time.sleep') as mock_sleep:
            result = cursor_client._make_request("/test-endpoint")

        assert result == {"success": True}
        assert mock_post.call_count == 2

    @patch('src.ingestion.cursor_client.requests.post')
    def test_make_request_client_error_no_retry(self, mock_post, cursor_client):
        """Test no retry for client errors."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        with pytest.raises(CursorAPIError) as exc_info:
            cursor_client._make_request("/test-endpoint")

        assert "400" in str(exc_info.value)
        assert mock_post.call_count == 1  # No retry for client errors

    @patch('src.ingestion.cursor_client.requests.post')
    def test_make_request_max_retries_exceeded(self, mock_post, cursor_client):
        """Test behavior when max retries exceeded."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with patch('src.ingestion.cursor_client.time.sleep'):
            with pytest.raises(CursorAPIError) as exc_info:
                cursor_client._make_request("/test-endpoint")

        assert "API request failed with status 500" in str(exc_info.value)
        assert mock_post.call_count == 3

    def test_convert_timestamp(self, cursor_client):
        """Test timestamp conversion."""
        timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
        result = cursor_client._convert_timestamp(timestamp)
        expected = datetime.fromtimestamp(timestamp)
        assert result == expected

    def test_validate_date_range_success(self, cursor_client):
        """Test successful date range validation."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 7)

        # Should not raise exception
        cursor_client._validate_date_range(start_date, end_date)

    def test_validate_date_range_invalid_order(self, cursor_client):
        """Test date range validation with invalid order."""
        start_date = datetime(2022, 1, 7)
        end_date = datetime(2022, 1, 1)

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            cursor_client._validate_date_range(start_date, end_date)

    def test_validate_date_range_too_long(self, cursor_client):
        """Test date range validation with range too long."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 4, 1)  # 90 days exactly (should fail with >=)

        with pytest.raises(ValueError, match="Date range cannot exceed 90 days"):
            cursor_client._validate_date_range(start_date, end_date)

    @patch.object(CursorClient, '_make_request')
    def test_get_daily_usage_data_success(self, mock_make_request, cursor_client, sample_api_response):
        """Test successful daily usage data retrieval."""
        mock_make_request.return_value = sample_api_response

        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 2)

        result = cursor_client.get_daily_usage_data(start_date, end_date)

        assert len(result) == 2
        assert isinstance(result[0], CursorUsageData)
        assert result[0].email == "user1@example.com"
        assert result[0].total_lines_added == 1500
        assert result[1].email == "user2@example.com"

        # Verify API call parameters
        mock_make_request.assert_called_once()
        call_args = mock_make_request.call_args
        assert call_args[0][0] == "/teams/daily-usage-data"
        # Check data payload with millisecond timestamps
        data = call_args[0][1]
        assert "startDate" in data
        assert "endDate" in data
        # Verify timestamps are in milliseconds (should be 13 digits)
        assert len(str(data["startDate"])) == 13
        assert len(str(data["endDate"])) == 13
        assert data["startDate"] == int(start_date.timestamp() * 1000)
        assert data["endDate"] == int(end_date.timestamp() * 1000)

    @patch.object(CursorClient, 'get_daily_usage_data')
    def test_get_recent_usage(self, mock_get_daily, cursor_client):
        """Test get_recent_usage method."""
        mock_data = [Mock(spec=CursorUsageData)]
        mock_get_daily.return_value = mock_data

        result = cursor_client.get_recent_usage(days=3)

        assert result == mock_data
        mock_get_daily.assert_called_once()

        # Check that date range is approximately correct
        call_args = mock_get_daily.call_args[0]
        start_date, end_date = call_args
        date_diff = (end_date - start_date).days
        assert date_diff == 3

    @patch.object(CursorClient, 'get_recent_usage')
    def test_health_check_success(self, mock_get_recent, cursor_client):
        """Test successful health check."""
        mock_get_recent.return_value = [Mock()]

        result = cursor_client.health_check()

        assert result is True
        mock_get_recent.assert_called_once_with(days=1)

    @patch.object(CursorClient, 'get_recent_usage')
    def test_health_check_failure(self, mock_get_recent, cursor_client):
        """Test health check failure."""
        mock_get_recent.side_effect = CursorAPIError("API Error")

        result = cursor_client.health_check()

        assert result is False

    def test_cursor_usage_data_creation(self):
        """Test CursorUsageData dataclass creation."""
        date = datetime.now()
        data = CursorUsageData(
            email="test@example.com",
            total_lines_added=100,
            accepted_lines_added=80,
            total_accepts=5,
            subscription_included_reqs=10,
            usage_based_reqs=2,
            date=date
        )

        assert data.email == "test@example.com"
        assert data.total_lines_added == 100
        assert data.accepted_lines_added == 80
        assert data.total_accepts == 5
        assert data.subscription_included_reqs == 10
        assert data.usage_based_reqs == 2
        assert data.date == date


class TestCursorAPIError:
    """Test cases for CursorAPIError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = CursorAPIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.response_text is None

    def test_error_with_details(self):
        """Test error with status code and response text."""
        error = CursorAPIError("API Error", status_code=400, response_text="Bad Request")
        assert str(error) == "API Error"
        assert error.status_code == 400
        assert error.response_text == "Bad Request"