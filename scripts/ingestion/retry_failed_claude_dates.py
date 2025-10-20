#!/usr/bin/env python3
"""
Retry Failed Claude Data Ingestion Dates

Retries only the dates that failed during previous backfill attempts.
Uses conservative rate limiting (5-10 second delays) to avoid 429 errors.

Usage:
    python retry_failed_claude_dates.py /tmp/missing_june_oct_dates.txt
    python retry_failed_claude_dates.py --all-missing  # Auto-detect from BigQuery
"""

import sys
import os
import time
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import bigquery

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_claude_data import ClaudeDataIngestion

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_missing_dates_from_bigquery(start_date: str = '2025-06-01', end_date: str = '2025-10-18'):
    """Query BigQuery to find missing dates in range"""
    bq_client = bigquery.Client(project='ai-workflows-459123')

    query = f"""
    WITH expected_dates AS (
      SELECT date
      FROM UNNEST(GENERATE_DATE_ARRAY('{start_date}', '{end_date}')) as date
    ),
    actual_dates AS (
      SELECT DISTINCT activity_date as date
      FROM ai_usage_analytics.claude_costs
    )
    SELECT e.date
    FROM expected_dates e
    LEFT JOIN actual_dates a ON e.date = a.date
    WHERE a.date IS NULL
    ORDER BY e.date
    """

    result = bq_client.query(query).result()
    return [row.date.isoformat() for row in result]


def retry_failed_dates(dates_file: str = None, auto_detect: bool = False, delay_seconds: int = 5):
    """
    Retry ingestion for failed dates with conservative rate limiting.

    Args:
        dates_file: Path to file with one date per line (YYYY-MM-DD)
        auto_detect: Auto-detect missing dates from BigQuery
        delay_seconds: Seconds to wait between requests (default: 5)
    """

    # Get list of dates to retry
    if auto_detect:
        logger.info("Auto-detecting missing dates from BigQuery...")
        dates_to_retry = get_missing_dates_from_bigquery()
    elif dates_file:
        logger.info(f"Loading dates from {dates_file}...")
        with open(dates_file, 'r') as f:
            dates_to_retry = [line.strip() for line in f if line.strip()]
    else:
        raise ValueError("Must provide either dates_file or --all-missing flag")

    total_dates = len(dates_to_retry)
    logger.info(f"Found {total_dates} missing dates to retry")

    if total_dates == 0:
        logger.info("No missing dates! Backfill is complete.")
        return

    # Initialize ingestion
    ingestion = ClaudeDataIngestion()

    # Track results
    success_count = 0
    failure_count = 0
    failed_dates = []

    # Process each date
    for idx, date_str in enumerate(dates_to_retry, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"[{idx}/{total_dates}] Retrying {date_str}...")
        logger.info(f"{'='*60}")

        try:
            ingestion.ingest_daily(date_str)
            success_count += 1
            logger.info(f"✅ SUCCESS: {date_str}")

        except Exception as e:
            failure_count += 1
            failed_dates.append(date_str)
            error_msg = str(e)

            if '429' in error_msg or 'rate_limit' in error_msg.lower():
                logger.error(f"❌ RATE LIMITED: {date_str}")
                logger.warning(f"Increasing delay to {delay_seconds * 2}s to recover...")
                time.sleep(delay_seconds * 2)  # Extra delay after rate limit
            else:
                logger.error(f"❌ FAILED: {date_str} - {error_msg}")

        # Progress update every 10 dates
        if idx % 10 == 0:
            pct_complete = (idx / total_dates) * 100
            logger.info(f"\n⏱️  Progress: {idx}/{total_dates} ({pct_complete:.1f}%) | ✅ {success_count} | ❌ {failure_count}")

        # Conservative rate limiting between ALL requests
        if idx < total_dates:
            logger.debug(f"Waiting {delay_seconds}s before next request...")
            time.sleep(delay_seconds)

    # Final summary
    logger.info(f"\n{'='*60}")
    logger.info("RETRY COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total dates attempted: {total_dates}")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed: {failure_count}")

    if success_count > 0:
        success_rate = (success_count / total_dates) * 100
        logger.info(f"Success rate: {success_rate:.1f}%")

    if failed_dates:
        logger.warning(f"\n⚠️  Failed dates (retry manually with longer delays):")
        for date in failed_dates:
            logger.warning(f"  - {date}")

        # Save failed dates to file
        failed_file = '/tmp/claude_still_failed.txt'
        with open(failed_file, 'w') as f:
            f.write('\n'.join(failed_dates))
        logger.info(f"\nFailed dates saved to: {failed_file}")
    else:
        logger.info("\n🎉 All dates successfully retried!")

    return success_count, failure_count


def main():
    parser = argparse.ArgumentParser(description='Retry failed Claude ingestion dates')
    parser.add_argument('dates_file', nargs='?', help='File with dates to retry (one per line)')
    parser.add_argument('--all-missing', action='store_true',
                       help='Auto-detect missing dates from BigQuery (Jun-Oct)')
    parser.add_argument('--delay', type=int, default=5,
                       help='Seconds to wait between requests (default: 5, recommend 10 for safety)')

    args = parser.parse_args()

    if not args.dates_file and not args.all_missing:
        parser.print_help()
        print("\nExample:")
        print("  python retry_failed_claude_dates.py /tmp/missing_june_oct_dates.txt")
        print("  python retry_failed_claude_dates.py --all-missing --delay 10")
        sys.exit(1)

    try:
        success, failed = retry_failed_dates(
            dates_file=args.dates_file,
            auto_detect=args.all_missing,
            delay_seconds=args.delay
        )

        if failed == 0:
            logger.info("✅ All retries successful!")
            sys.exit(0)
        else:
            logger.warning(f"⚠️  {failed} dates still failed - may need longer delays or manual retry")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"Retry script failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
