# Google Sheets API Key Mapping Setup

This document explains how to set up Google Sheets integration for API key to user email mapping.

## Overview

The system uses Google Sheets to maintain a mapping between API keys and user emails. This enables accurate cost attribution across different AI platforms (Anthropic Claude API, Cursor, etc.).

## Setup Steps

### 1. Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create a service account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the details and create
5. Generate a key for the service account:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Select JSON format and download

### 2. Configure Authentication

Set up Application Default Credentials:

```bash
# Set the environment variable to point to your service account key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"

# Or use gcloud auth
gcloud auth application-default login
```

### 3. Create Google Sheets Document

1. Create a new Google Sheets document
2. Use the template provided:

```bash
# Generate template
python scripts/setup_sheets_template.py
```

3. Copy the template content to your sheet
4. Replace sample data with your actual API keys and emails

### 4. Share the Sheet

1. Share the Google Sheets document with your service account email
2. Grant "Viewer" permissions (read-only access)
3. Copy the sheet ID from the URL:
   - Format: `docs.google.com/spreadsheets/d/{SHEET_ID}/edit`

### 5. Update Configuration

Add the sheet ID to your environment configuration:

```bash
# In your .env file
GOOGLE_SHEETS_ID=your-google-sheets-id-here
```

## Sheet Format

The spreadsheet must have exactly 3 columns in this order:

| Column A | Column B | Column C |
|----------|----------|----------|
| api_key_name | email | description |
| cursor-dev-key-1 | john.doe@company.com | Development Cursor key |
| anthropic-prod-key-2 | jane.smith@company.com | Production Claude API |

### Column Specifications

- **api_key_name**: Unique identifier for the API key
- **email**: Valid user email address (will be normalized to lowercase)
- **description**: Human-readable description of the key usage

### Platform Detection

The system automatically detects platforms based on keywords:

- **Cursor**: Keys with "cursor" in name or description
- **Anthropic**: Keys with "anthropic" or "claude" in name or description
- **Default**: Falls back to "anthropic" for unclear cases

## Validation

The system performs comprehensive validation:

- **Email Format**: Must be valid email addresses
- **Duplicate Detection**: Warns about duplicate API key names
- **Data Quality**: Checks for missing required fields
- **Platform Consistency**: Ensures reasonable platform distribution

## Testing Connection

Test your Google Sheets integration:

```bash
# Run the setup script to test connection
python scripts/setup_sheets_template.py

# Run health check
python -c "
from src.ingestion.sheets_client import GoogleSheetsClient
client = GoogleSheetsClient()
print('Health check:', client.health_check())
print('Validation:', client.validate_sheet_format())
"
```

## Maintenance

### Adding New API Keys

1. Add new rows to the Google Sheets document
2. Follow the 3-column format
3. The system will automatically pick up changes on next sync

### Updating User Emails

1. Update the email column in Google Sheets
2. Changes take effect on next data processing cycle

### Deactivating Keys

To deactivate an API key mapping:
1. Delete the row from Google Sheets, OR
2. Clear the email field (key will be flagged as unmapped)

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Check service account credentials
   - Verify Google Sheets API is enabled
   - Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set

2. **Permission Denied**
   - Share the sheet with service account email
   - Grant at least "Viewer" permissions

3. **No Data Found**
   - Check sheet ID in configuration
   - Verify sheet has data in correct format
   - Ensure columns A, B, C contain the mapping data

4. **Validation Errors**
   - Check email format in column B
   - Ensure no duplicate API key names
   - Verify required fields are not empty

### Debug Commands

```bash
# Test API key lookup
python -c "
from src.ingestion.sheets_client import GoogleSheetsClient
client = GoogleSheetsClient()
mappings = client.get_api_key_mappings()
print(f'Found {len(mappings)} mappings')
for m in mappings[:5]:  # Show first 5
    print(f'{m.api_key_name} -> {m.user_email} ({m.platform})')
"

# Validate sheet format
python scripts/setup_sheets_template.py
```

## Security Considerations

- Service account key should be kept secure
- Use least-privilege access (Viewer permissions only)
- Regularly rotate service account keys
- Monitor sheet access logs
- Consider using Google Cloud Secret Manager for key storage

## API Reference

The `GoogleSheetsClient` provides these key methods:

- `get_api_key_mappings()`: Get all mappings
- `get_mapping_by_api_key(key_name)`: Find specific mapping
- `get_mappings_by_platform(platform)`: Filter by platform
- `validate_sheet_format()`: Check data quality
- `health_check()`: Test connection