#!/usr/bin/env python3
"""
Cursor Admin API Client

Provides methods to fetch team usage metrics and spending data.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class CursorAPIError(Exception):
    """Cursor API specific errors"""
    def __init__(self, status_code: int, message: str, response_data: Any = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"Cursor API Error {status_code}: {message}")


class CursorAdminClient:
    """Client for Cursor Admin API"""

    def __init__(self, api_key: str, base_url: str = "https://api.cursor.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(api_key, '')
        self.session.headers.update({'Content-Type': 'application/json'})

    def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)

                if response.status_code == 200:
                    return response.json()

                # Handle errors
                if response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue

                # Other errors
                raise CursorAPIError(
                    response.status_code,
                    f"API request failed: {response.text}",
                    response.json() if response.text else None
                )

            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(2 ** attempt)

        raise CursorAPIError(500, "Max retries exceeded")

    def get_daily_usage_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Fetch daily usage metrics.

        Args:
            start_date: Start date (UTC)
            end_date: End date (UTC), defaults to start_date + 1 day

        Returns:
            {
                "period": {"startDate": ms, "endDate": ms},
                "data": [
                    {
                        "email": str,
                        "date": ms,
                        "isActive": bool,
                        "totalLinesAdded": int,
                        "usageBasedReqs": int,
                        ...
                    }
                ]
            }
        """
        if end_date is None:
            from datetime import timedelta
            end_date = start_date + timedelta(days=1)

        # Convert to milliseconds
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)

        # Validate 90-day limit
        days_diff = (end_date - start_date).days
        if days_diff > 90:
            raise ValueError(f"Date range {days_diff} days exceeds 90-day limit")

        url = f"{self.base_url}/teams/daily-usage-data"
        payload = {
            "startDate": start_ms,
            "endDate": end_ms
        }

        logger.info(f"Fetching usage data: {start_date.date()} to {end_date.date()}")
        return self._request_with_retry("POST", url, json=payload)

    def get_spend(
        self,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Fetch current billing cycle spending.

        Returns cumulative spend since cycle start (not daily amounts).

        Returns:
            {
                "teamMemberSpend": [
                    {
                        "email": str,
                        "spendCents": int,  # Overage charges in cents
                        "includedSpendCents": int,  # Free tier value in cents
                        "fastPremiumRequests": int,
                        "name": str,
                        "role": str,
                        "hardLimitOverrideDollars": float,
                        ...
                    }
                ],
                "subscriptionCycleStart": int,  # Timestamp in ms
                "totalMembers": int,
                "totalPages": int
            }
        """
        url = f"{self.base_url}/teams/spend"
        payload = {
            "page": page,
            "pageSize": page_size
        }

        logger.info(f"Fetching spending data (page {page})")
        return self._request_with_retry("POST", url, json=payload)

    def get_all_spend_pages(self) -> List[Dict[str, Any]]:
        """
        Fetch all pages of spending data.

        Returns:
            List of all team member spend records
        """
        all_members = []
        page = 1

        while True:
            response = self.get_spend(page=page)
            members = response.get('teamMemberSpend', [])
            all_members.extend(members)

            total_pages = response.get('totalPages', 1)
            if page >= total_pages:
                break

            page += 1
            time.sleep(0.5)  # Rate limit courtesy

        logger.info(f"Fetched {len(all_members)} team members across {page} pages")
        return all_members, response.get('subscriptionCycleStart')
