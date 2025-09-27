"""Cursor API client for extracting team usage data."""

import time
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union
import logging
from dataclasses import dataclass

from ..shared.config import config
from ..shared.logging_setup import get_logger
from ..shared.cloud_monitoring import get_cloud_monitoring


@dataclass
class CursorUsageData:
    """Structured representation of Cursor usage data."""
    email: str
    total_lines_added: int
    accepted_lines_added: int
    total_accepts: int
    subscription_included_reqs: int
    usage_based_reqs: int
    date: datetime


class CursorAPIError(Exception):
    """Custom exception for Cursor API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class CursorClient:
    """Client for Cursor Admin API integration."""

    BASE_URL = "https://api.cursor.com"
    MAX_RETRIES = 3
    BACKOFF_BASE = 2
    MAX_DATE_RANGE_DAYS = 90

    def __init__(self):
        self.logger = get_logger("cursor_client")
        self.api_key = config.cursor_api_key

        if not self.api_key:
            raise CursorAPIError("Cursor API key not found in configuration")

    def _make_request(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated request to Cursor API with retry logic."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Content-Type": "application/json"
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.info(f"Making request to {endpoint} (attempt {attempt + 1})")

                # Record request start time for monitoring
                request_start_time = time.time()

                response = requests.post(
                    url,
                    auth=(self.api_key, ""),  # Basic auth with API key as username
                    headers=headers,
                    json=data,
                    timeout=30
                )

                # Calculate and record response time
                response_time_ms = (time.time() - request_start_time) * 1000

                if response.status_code == 200:
                    # Record successful API response time
                    try:
                        monitoring_client = get_cloud_monitoring()
                        monitoring_client.record_api_response_time("cursor", response_time_ms, endpoint)
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
                raise CursorAPIError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text
                )

            except requests.exceptions.RequestException as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.BACKOFF_BASE ** (attempt + 1)
                    self.logger.warning(f"Request exception: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    raise CursorAPIError(f"Request failed after {self.MAX_RETRIES} attempts: {e}")

        raise CursorAPIError(f"Request failed after {self.MAX_RETRIES} attempts")

    def _convert_timestamp(self, timestamp: int) -> datetime:
        """Convert Unix timestamp to datetime object."""
        return datetime.fromtimestamp(timestamp)

    def _validate_date_range(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> None:
        """Validate date range constraints."""
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")

        date_diff = (end_date - start_date).days
        if date_diff >= self.MAX_DATE_RANGE_DAYS:
            raise ValueError(f"Date range cannot exceed {self.MAX_DATE_RANGE_DAYS} days")

    def get_daily_usage_data(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> List[CursorUsageData]:
        """
        Retrieve daily usage data from Cursor API.

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of CursorUsageData objects

        Raises:
            CursorAPIError: If API request fails
            ValueError: If date range is invalid
        """
        self._validate_date_range(start_date, end_date)

        # Convert to datetime if date objects are provided
        if isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        if isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.min.time())

        # Convert to Unix timestamps in milliseconds (as required by Cursor API)
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)

        data = {
            "startDate": start_timestamp,
            "endDate": end_timestamp
        }

        self.logger.info(f"Fetching Cursor usage data from {start_date} to {end_date}")

        try:
            response_data = self._make_request("/teams/daily-usage-data", data)

            # Parse response into structured data
            usage_records = []

            # Assuming response format: {"data": [{"email": "...", "totalLinesAdded": 123, ...}]}
            data_list = response_data.get("data", [])

            for record in data_list:
                usage_data = CursorUsageData(
                    email=record.get("email", ""),
                    total_lines_added=record.get("totalLinesAdded", 0),
                    accepted_lines_added=record.get("acceptedLinesAdded", 0),
                    total_accepts=record.get("totalAccepts", 0),
                    subscription_included_reqs=record.get("subscriptionIncludedReqs", 0),
                    usage_based_reqs=record.get("usageBasedReqs", 0),
                    date=self._convert_timestamp(record.get("timestamp", start_timestamp))
                )
                usage_records.append(usage_data)

            self.logger.info(f"Successfully retrieved {len(usage_records)} usage records")
            return usage_records

        except Exception as e:
            self.logger.error(f"Failed to retrieve Cursor usage data: {e}")
            raise

    def get_recent_usage(self, days: int = 7) -> List[CursorUsageData]:
        """
        Get usage data for the last N days.

        Args:
            days: Number of days to retrieve (default: 7)

        Returns:
            List of CursorUsageData objects
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.get_daily_usage_data(start_date, end_date)

    def health_check(self) -> bool:
        """
        Perform health check on Cursor API.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try to get recent data (1 day) as health check
            recent_data = self.get_recent_usage(days=1)
            self.logger.info("Cursor API health check passed")
            return True
        except Exception as e:
            self.logger.error(f"Cursor API health check failed: {e}")
            return False