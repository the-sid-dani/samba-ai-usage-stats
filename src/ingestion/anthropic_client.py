"""Anthropic Claude API client for extracting usage and cost data."""

import time
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Iterator
import logging
from dataclasses import dataclass

from ..shared.config import config
from ..shared.logging_setup import get_logger
from ..shared.cloud_monitoring import get_cloud_monitoring
import re


def _sanitize_sensitive_data(text: str) -> str:
    """
    Sanitize sensitive data from text to prevent credential exposure.

    Removes patterns that may contain API keys, tokens, or other sensitive information.
    """
    if not text:
        return text

    # Pattern to match potential API keys (various formats)
    api_key_patterns = [
        r'sk-[a-zA-Z0-9_-]{15,}',  # Anthropic API keys (more specific length)
        r'(["\']?api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{15,})(["\']?)',  # Generic API key patterns
        r'(["\']?authorization["\']?\s*[:=]\s*["\']?(?:Bearer\s+)?)([a-zA-Z0-9_-]{15,})(["\']?)',  # Authorization headers
        r'(["\']?token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{15,})(["\']?)',  # Token patterns
    ]

    sanitized_text = text
    for pattern in api_key_patterns:
        if '(' in pattern:  # Group-based patterns - preserve prefix/suffix
            def replace_func(match):
                return match.group(1) + '[REDACTED_CREDENTIAL]' + match.group(3)
            sanitized_text = re.sub(pattern, replace_func, sanitized_text, flags=re.IGNORECASE)
        else:  # Simple patterns - full replacement
            sanitized_text = re.sub(pattern, '[REDACTED_CREDENTIAL]', sanitized_text, flags=re.IGNORECASE)

    return sanitized_text


@dataclass
class AnthropicUsageData:
    """Structured representation of Anthropic usage data."""
    api_key_id: str
    workspace_id: Optional[str]
    model: str
    uncached_input_tokens: int
    cached_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    usage_date: date
    usage_hour: Optional[int]


@dataclass
class AnthropicCostData:
    """Structured representation of Anthropic cost data."""
    api_key_id: str
    workspace_id: Optional[str]
    model: str
    cost_usd: float
    cost_type: str  # 'input_tokens', 'output_tokens', 'cache_read'
    cost_date: date
    cost_hour: Optional[int]


class AnthropicAPIError(Exception):
    """Custom exception for Anthropic API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class AnthropicClient:
    """Client for Anthropic Admin API integration."""

    BASE_URL = "https://api.anthropic.com/v1"
    MAX_RETRIES = 3
    BACKOFF_BASE = 2
    MAX_DATE_RANGE_DAYS = 31  # Anthropic API limit

    def __init__(self):
        self.logger = get_logger("anthropic_client")
        self.api_key = config.anthropic_api_key

        if not self.api_key:
            raise AnthropicAPIError("Anthropic API key not found in configuration")

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated request to Anthropic API with retry logic."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.info(f"Making request to {endpoint} (attempt {attempt + 1})")

                # Record request start time for monitoring
                request_start_time = time.time()

                response = requests.get(url, headers=headers, params=params, timeout=30)

                # Calculate and record response time
                response_time_ms = (time.time() - request_start_time) * 1000

                if response.status_code == 200:
                    # Record successful API response time
                    try:
                        monitoring_client = get_cloud_monitoring()
                        monitoring_client.record_api_response_time("anthropic", response_time_ms, endpoint)
                    except Exception as e:
                        self.logger.warning(f"Failed to record API response time: {e}")

                    return response.json()

                elif response.status_code == 429:  # Rate limit
                    wait_time = self.BACKOFF_BASE ** (attempt + 1)
                    self.logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue

                elif response.status_code in [500, 502, 503, 504]:  # Server errors
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = self.BACKOFF_BASE ** (attempt + 1)
                        self.logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue

                # Client errors or final server error
                sanitized_response = _sanitize_sensitive_data(response.text)
                raise AnthropicAPIError(
                    f"API request failed with status {response.status_code}: {sanitized_response}",
                    status_code=response.status_code,
                    response_text=sanitized_response
                )

            except requests.exceptions.RequestException as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.BACKOFF_BASE ** (attempt + 1)
                    self.logger.warning(f"Request exception: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    raise AnthropicAPIError(f"Request failed after {self.MAX_RETRIES} attempts: {e}")

        raise AnthropicAPIError(f"Request failed after {self.MAX_RETRIES} attempts")

    def _paginate_request(self, endpoint: str, params: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Handle paginated requests to Anthropic API."""
        page_token = None

        while True:
            current_params = params.copy()
            if page_token:
                current_params["page_token"] = page_token

            response = self._make_request(endpoint, current_params)

            yield response

            # Check for pagination
            page_token = response.get("next_page_token")
            if not page_token:
                break

    def _validate_date_range(self, start_date: date, end_date: date) -> None:
        """Validate date range constraints."""
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")

        date_diff = (end_date - start_date).days
        if date_diff >= self.MAX_DATE_RANGE_DAYS:
            raise ValueError(f"Date range cannot exceed {self.MAX_DATE_RANGE_DAYS} days")

    def _chunk_date_range(self, start_date: date, end_date: date) -> Iterator[tuple[date, date]]:
        """Split large date ranges into API-compliant chunks."""
        current_start = start_date

        while current_start < end_date:
            current_end = min(
                current_start + timedelta(days=self.MAX_DATE_RANGE_DAYS - 1),
                end_date
            )
            yield current_start, current_end
            current_start = current_end + timedelta(days=1)

    def get_usage_data(self, start_date: date, end_date: date) -> List[AnthropicUsageData]:
        """
        Retrieve usage data from Anthropic Admin API.

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of AnthropicUsageData objects

        Raises:
            AnthropicAPIError: If API request fails
            ValueError: If date range is invalid
        """
        usage_records = []

        # Handle large date ranges by chunking
        for chunk_start, chunk_end in self._chunk_date_range(start_date, end_date):
            self.logger.info(f"Fetching Anthropic usage data from {chunk_start} to {chunk_end}")

            params = {
                "starting_at": chunk_start.isoformat(),
                "ending_at": chunk_end.isoformat()
            }

            try:
                # Handle pagination
                for page_response in self._paginate_request("/organizations/usage_report/messages", params):
                    # Parse response data - handle nested results structure
                    data_list = page_response.get("data", [])

                    for period_record in data_list:
                        # Extract date range from period record
                        starting_at = period_record.get("starting_at", "")
                        ending_at = period_record.get("ending_at", "")

                        # Parse date from starting_at
                        usage_date = chunk_start  # fallback
                        usage_hour = None
                        if starting_at:
                            try:
                                if "T" in starting_at:  # ISO timestamp
                                    usage_datetime = datetime.fromisoformat(starting_at.replace("Z", "+00:00"))
                                    usage_date = usage_datetime.date()
                                    usage_hour = usage_datetime.hour
                                else:  # Date only
                                    usage_date = date.fromisoformat(starting_at)
                            except ValueError:
                                self.logger.warning(f"Invalid date format: {starting_at}")

                        # Process nested results array
                        results = period_record.get("results", [])
                        for result in results:
                            # Handle cache creation nested structure
                            cache_creation = result.get("cache_creation", {})
                            cached_input_tokens = cache_creation.get("ephemeral_1h_input_tokens", 0)

                            usage_data = AnthropicUsageData(
                                api_key_id=period_record.get("api_key_id", "unknown"),
                                workspace_id=period_record.get("workspace_id"),
                                model=period_record.get("model", "unknown"),
                                uncached_input_tokens=result.get("uncached_input_tokens", 0),
                                cached_input_tokens=cached_input_tokens,
                                cache_read_input_tokens=result.get("cache_read_input_tokens", 0),
                                output_tokens=result.get("output_tokens", 0),
                                usage_date=usage_date,
                                usage_hour=usage_hour
                            )
                            usage_records.append(usage_data)

            except Exception as e:
                self.logger.error(f"Failed to retrieve Anthropic usage data for {chunk_start}-{chunk_end}: {e}")
                raise

        self.logger.info(f"Successfully retrieved {len(usage_records)} usage records")
        return usage_records

    def get_cost_data(self, start_date: date, end_date: date) -> List[AnthropicCostData]:
        """
        Retrieve cost data from Anthropic Admin API.

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of AnthropicCostData objects

        Raises:
            AnthropicAPIError: If API request fails
            ValueError: If date range is invalid
        """
        cost_records = []

        # Handle large date ranges by chunking
        for chunk_start, chunk_end in self._chunk_date_range(start_date, end_date):
            self.logger.info(f"Fetching Anthropic cost data from {chunk_start} to {chunk_end}")

            params = {
                "starting_at": chunk_start.isoformat(),
                "ending_at": chunk_end.isoformat()
            }

            try:
                # Handle pagination
                for page_response in self._paginate_request("/organizations/cost_report", params):
                    # Parse response data - handle nested results structure
                    data_list = page_response.get("data", [])

                    for period_record in data_list:
                        # Extract date range from period record
                        starting_at = period_record.get("starting_at", "")
                        ending_at = period_record.get("ending_at", "")

                        # Parse date from starting_at
                        cost_date = chunk_start  # fallback
                        cost_hour = None
                        if starting_at:
                            try:
                                if "T" in starting_at:  # ISO timestamp
                                    cost_datetime = datetime.fromisoformat(starting_at.replace("Z", "+00:00"))
                                    cost_date = cost_datetime.date()
                                    cost_hour = cost_datetime.hour
                                else:  # Date only
                                    cost_date = date.fromisoformat(starting_at)
                            except ValueError:
                                self.logger.warning(f"Invalid date format: {starting_at}")

                        # Process nested results array
                        results = period_record.get("results", [])
                        for result in results:
                            # Handle real cost structure - amount is total cost, not breakdown
                            cost_amount_str = result.get("amount", "0")
                            currency = result.get("currency", "USD")

                            try:
                                # Convert string amount to float
                                cost_amount = float(cost_amount_str)

                                if cost_amount > 0:  # Only record non-zero costs
                                    cost_data = AnthropicCostData(
                                        api_key_id=period_record.get("api_key_id", "unknown"),
                                        workspace_id=result.get("workspace_id"),
                                        model=period_record.get("model", "unknown"),
                                        cost_usd=cost_amount,
                                        cost_type="total_cost",  # Real API provides total, not breakdown
                                        cost_date=cost_date,
                                        cost_hour=cost_hour
                                    )
                                    cost_records.append(cost_data)
                            except (ValueError, TypeError):
                                self.logger.warning(f"Invalid cost amount: {cost_amount_str}")
                                continue

            except Exception as e:
                self.logger.error(f"Failed to retrieve Anthropic cost data for {chunk_start}-{chunk_end}: {e}")
                raise

        self.logger.info(f"Successfully retrieved {len(cost_records)} cost records")
        return cost_records

    def get_recent_usage(self, days: int = 7) -> List[AnthropicUsageData]:
        """
        Get usage data for the last N days.

        Args:
            days: Number of days to retrieve (default: 7)

        Returns:
            List of AnthropicUsageData objects
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return self.get_usage_data(start_date, end_date)

    def get_recent_costs(self, days: int = 7) -> List[AnthropicCostData]:
        """
        Get cost data for the last N days.

        Args:
            days: Number of days to retrieve (default: 7)

        Returns:
            List of AnthropicCostData objects
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return self.get_cost_data(start_date, end_date)

    def health_check(self) -> bool:
        """
        Perform health check on Anthropic API.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try to get recent data (1 day) as health check
            recent_data = self.get_recent_usage(days=1)
            self.logger.info("Anthropic API health check passed")
            return True
        except Exception as e:
            self.logger.error(f"Anthropic API health check failed: {e}")
            return False

    def get_supported_models(self) -> List[str]:
        """
        Get list of supported models (if available via API).

        Returns:
            List of model names
        """
        # This would be implementation-specific based on actual Anthropic API
        # For now, return known models from documentation
        return [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ]