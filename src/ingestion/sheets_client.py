"""Google Sheets API client for API key to user email mapping."""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from googleapiclient.discovery import build
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

from ..shared.config import config
from ..shared.logging_setup import get_logger


@dataclass
class APIKeyMapping:
    """Represents an API key to user mapping."""
    api_key_name: str
    user_email: str
    description: str
    platform: str
    is_active: bool = True


class SheetsAPIError(Exception):
    """Custom exception for Google Sheets API errors."""
    pass


class GoogleSheetsClient:
    """Client for Google Sheets API integration."""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    RANGE_NAME = 'Sheet1!A:C'  # Default range: A=api_key_name, B=email, C=description

    def __init__(self):
        self.logger = get_logger("sheets_client")
        self.sheets_id = config.sheets_id
        self.service = None

        if not self.sheets_id:
            raise SheetsAPIError("Google Sheets ID not found in configuration")

        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Sheets API service with authentication."""
        try:
            # Use application default credentials
            credentials, project = default(scopes=self.SCOPES)
            self.service = build('sheets', 'v4', credentials=credentials)
            self.logger.info("Google Sheets API service initialized successfully")
        except DefaultCredentialsError as e:
            self.logger.error(f"Failed to authenticate with Google Sheets API: {e}")
            raise SheetsAPIError(f"Authentication failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Sheets service: {e}")
            raise SheetsAPIError(f"Service initialization failed: {e}")

    def _validate_email(self, email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if email is valid, False otherwise
        """
        if not email or not email.strip():
            return False

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))

    def _determine_platform(self, api_key_name: str, description: str) -> str:
        """
        Determine platform based on API key name and description.

        Args:
            api_key_name: Name of the API key
            description: Description of the API key

        Returns:
            Platform identifier
        """
        # Convert to lowercase for matching
        key_lower = api_key_name.lower()
        desc_lower = description.lower()

        # Platform detection rules
        if any(term in key_lower or term in desc_lower for term in ['cursor']):
            return 'cursor'
        elif any(term in key_lower or term in desc_lower for term in ['anthropic', 'claude']):
            return 'anthropic'
        else:
            # Default to anthropic if unclear
            return 'anthropic'

    def get_api_key_mappings(self) -> List[APIKeyMapping]:
        """
        Retrieve API key mappings from Google Sheets.

        Returns:
            List of APIKeyMapping objects

        Raises:
            SheetsAPIError: If API request fails
        """
        try:
            self.logger.info(f"Fetching API key mappings from Google Sheets: {self.sheets_id}")

            # Call the Sheets API
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.sheets_id,
                range=self.RANGE_NAME
            ).execute()

            values = result.get('values', [])

            if not values:
                self.logger.warning("No data found in the spreadsheet")
                return []

            mappings = []
            invalid_rows = []

            # Skip header row if it exists
            data_rows = values[1:] if len(values) > 1 and self._is_header_row(values[0]) else values

            for row_idx, row in enumerate(data_rows, start=2):  # Start at 2 for Excel-like numbering
                try:
                    # Ensure row has at least 3 columns
                    while len(row) < 3:
                        row.append('')

                    api_key_name = row[0].strip() if row[0] else ''
                    user_email = row[1].strip() if row[1] else ''
                    description = row[2].strip() if row[2] else ''

                    # Skip empty rows
                    if not api_key_name and not user_email:
                        continue

                    # Validate required fields
                    if not api_key_name:
                        invalid_rows.append(f"Row {row_idx}: Missing API key name")
                        continue

                    if not self._validate_email(user_email):
                        invalid_rows.append(f"Row {row_idx}: Invalid email format: {user_email}")
                        continue

                    # Determine platform
                    platform = self._determine_platform(api_key_name, description)

                    mapping = APIKeyMapping(
                        api_key_name=api_key_name,
                        user_email=user_email.lower(),  # Normalize email
                        description=description,
                        platform=platform,
                        is_active=True
                    )
                    mappings.append(mapping)

                except Exception as e:
                    invalid_rows.append(f"Row {row_idx}: Error processing row: {e}")

            # Log validation issues
            if invalid_rows:
                self.logger.warning(f"Found {len(invalid_rows)} invalid rows:")
                for issue in invalid_rows[:10]:  # Log first 10 issues
                    self.logger.warning(f"  {issue}")
                if len(invalid_rows) > 10:
                    self.logger.warning(f"  ... and {len(invalid_rows) - 10} more issues")

            self.logger.info(f"Successfully loaded {len(mappings)} API key mappings")
            return mappings

        except Exception as e:
            self.logger.error(f"Failed to fetch API key mappings: {e}")
            raise SheetsAPIError(f"Failed to fetch mappings: {e}")

    def _is_header_row(self, row: List[str]) -> bool:
        """
        Check if a row appears to be a header row.

        Args:
            row: Row data to check

        Returns:
            True if row appears to be a header
        """
        if not row:
            return False

        # Common header patterns
        header_patterns = [
            'api_key_name', 'api_key', 'api key', 'email', 'description', 'user', 'name', 'key'
        ]

        first_cell = row[0].lower().strip()

        # Check for exact matches or substring matches for common headers
        return any(pattern in first_cell for pattern in header_patterns)

    def get_mapping_by_api_key(self, api_key_name: str) -> Optional[APIKeyMapping]:
        """
        Get user mapping for a specific API key.

        Args:
            api_key_name: Name of the API key to look up

        Returns:
            APIKeyMapping object if found, None otherwise
        """
        mappings = self.get_api_key_mappings()

        for mapping in mappings:
            if mapping.api_key_name == api_key_name:
                return mapping

        return None

    def get_mappings_by_platform(self, platform: str) -> List[APIKeyMapping]:
        """
        Get all mappings for a specific platform.

        Args:
            platform: Platform to filter by

        Returns:
            List of APIKeyMapping objects for the platform
        """
        mappings = self.get_api_key_mappings()
        return [mapping for mapping in mappings if mapping.platform == platform]

    def validate_sheet_format(self) -> Dict[str, Any]:
        """
        Validate the Google Sheets format and data quality.

        Returns:
            Dictionary with validation results
        """
        try:
            mappings = self.get_api_key_mappings()

            # Count mappings by platform
            platform_counts = {}
            email_counts = {}
            duplicate_keys = set()
            seen_keys = set()

            for mapping in mappings:
                # Platform counts
                platform_counts[mapping.platform] = platform_counts.get(mapping.platform, 0) + 1

                # Email counts
                email_counts[mapping.user_email] = email_counts.get(mapping.user_email, 0) + 1

                # Duplicate key detection
                if mapping.api_key_name in seen_keys:
                    duplicate_keys.add(mapping.api_key_name)
                seen_keys.add(mapping.api_key_name)

            validation_result = {
                "total_mappings": len(mappings),
                "platform_counts": platform_counts,
                "email_counts": email_counts,
                "duplicate_keys": list(duplicate_keys),
                "unique_users": len(email_counts),
                "validation_passed": len(duplicate_keys) == 0,
                "warnings": []
            }

            # Add warnings
            if duplicate_keys:
                validation_result["warnings"].append(f"Found {len(duplicate_keys)} duplicate API keys")

            # Check for users with many keys (potential data issues)
            heavy_users = [(email, count) for email, count in email_counts.items() if count > 5]
            if heavy_users:
                validation_result["warnings"].append(f"Found {len(heavy_users)} users with >5 API keys")

            return validation_result

        except Exception as e:
            return {
                "total_mappings": 0,
                "validation_passed": False,
                "error": str(e)
            }

    def health_check(self) -> bool:
        """
        Perform health check on Google Sheets integration.

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            # Try to access the spreadsheet metadata
            sheet = self.service.spreadsheets()
            result = sheet.get(spreadsheetId=self.sheets_id).execute()

            title = result.get('properties', {}).get('title', 'Unknown')
            self.logger.info(f"Google Sheets health check passed - accessed sheet: {title}")
            return True

        except Exception as e:
            self.logger.error(f"Google Sheets health check failed: {e}")
            return False

    def create_sample_template(self) -> str:
        """
        Generate sample template content for the API key mapping spreadsheet.

        Returns:
            Sample spreadsheet content as CSV format
        """
        template = """api_key_name,email,description
cursor-dev-key-1,john.doe@company.com,Development environment Cursor key
anthropic-prod-key-2,jane.smith@company.com,Production Claude API key
cursor-team-key-3,team-lead@company.com,Team shared Cursor key
anthropic-test-key-4,developer@company.com,Testing Claude integration
claude-code-key-5,sarah.jones@company.com,Claude Code IDE integration"""

        return template