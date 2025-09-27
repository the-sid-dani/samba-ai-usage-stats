#!/usr/bin/env python3
"""Setup Google Sheets template for API key mapping."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.sheets_client import GoogleSheetsClient, SheetsAPIError
from shared.logging_setup import setup_logging


def main():
    """Generate and display Google Sheets template."""
    logger = setup_logging()
    logger.info("Generating Google Sheets template for API key mapping")

    try:
        # Create client instance (will validate config)
        client = GoogleSheetsClient()

        # Generate template
        template = client.create_sample_template()

        print("\n" + "="*60)
        print("GOOGLE SHEETS TEMPLATE FOR API KEY MAPPING")
        print("="*60)
        print()
        print("Copy the content below to your Google Sheets:")
        print()
        print(template)
        print()
        print("="*60)
        print("SETUP INSTRUCTIONS:")
        print("="*60)
        print()
        print("1. Create a new Google Sheets document")
        print("2. Copy the template content above into the first sheet")
        print("3. Replace the sample data with your actual API keys and emails")
        print("4. Share the sheet with your service account email")
        print("5. Copy the sheet ID from the URL and update your .env file")
        print()
        print("Sheet ID format: docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
        print("Update GOOGLE_SHEETS_ID in your .env file with the {SHEET_ID}")
        print()
        print("Required columns (in order):")
        print("  A: api_key_name - Name/ID of the API key")
        print("  B: email - User email address")
        print("  C: description - Description of the key usage")
        print()
        print("Platform detection:")
        print("  - 'cursor' keywords → cursor platform")
        print("  - 'anthropic'/'claude' keywords → anthropic platform")
        print("  - Default → anthropic platform")
        print()

        # Test health check if sheets ID is configured
        if client.sheets_id and client.sheets_id != "your-google-sheets-id-here":
            logger.info("Testing Google Sheets connection...")
            if client.health_check():
                print("✓ Google Sheets connection test: PASSED")

                # Validate current sheet format
                validation = client.validate_sheet_format()
                if validation.get("validation_passed"):
                    print(f"✓ Sheet format validation: PASSED ({validation['total_mappings']} mappings)")
                else:
                    print(f"⚠ Sheet format validation: ISSUES FOUND")
                    for warning in validation.get("warnings", []):
                        print(f"  - {warning}")
            else:
                print("✗ Google Sheets connection test: FAILED")
                print("  Check your service account credentials and sheet permissions")
        else:
            print("ℹ Configure GOOGLE_SHEETS_ID in .env to test connection")

    except SheetsAPIError as e:
        logger.error(f"Google Sheets setup error: {e}")
        print(f"\n✗ Error: {e}")
        print("\nPlease check:")
        print("- Google Cloud credentials are configured")
        print("- Service account has Sheets API access")
        print("- GOOGLE_SHEETS_ID is set in configuration")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()