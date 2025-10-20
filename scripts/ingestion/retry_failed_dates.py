#!/usr/bin/env python3
"""
Retry Failed Dates from Backfill

Retries dates that failed during the main backfill (usually due to rate limiting).
This script should be run AFTER the main backfill completes.

Usage:
    python retry_failed_dates.py 2025-03-27 2025-03-31 2025-04-01 2025-04-09
    python retry_failed_dates.py --from-log /tmp/backfill.log
"""

import argparse
import sys
import os
import time
import logging
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_claude_data import ClaudeDataIngestion

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_failed_dates_from_log(log_file: str) -> list:
    """Extract failed dates from backfill log."""
    failed_dates = []
    with open(log_file, 'r') as f:
        for line in f:
            if '❌ FAILED:' in line:
                # Extract date from: "❌ FAILED: 2025-03-27 - ..."
                match = re.search(r'FAILED: (\d{4}-\d{2}-\d{2})', line)
                if match:
                    failed_dates.append(match.group(1))
    return sorted(set(failed_dates))  # Remove duplicates and sort


def retry_dates(dates: list, sleep_between: int = 30):
    """
    Retry ingestion for failed dates with longer sleep times.

    Args:
        dates: List of dates in YYYY-MM-DD format
        sleep_between: Seconds to wait between dates (default: 30 for rate limiting)
    """
    ingestion = ClaudeDataIngestion()

    total = len(dates)
    success_count = 0
    still_failed = []

    logger.info(f"Retrying {total} failed dates with {sleep_between}s sleep between attempts...")

    for idx, date in enumerate(dates, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"[{idx}/{total}] Retrying {date}...")
        logger.info(f"{'='*60}")

        try:
            ingestion.ingest_daily(date)
            success_count += 1
            logger.info(f"✅ SUCCESS: {date}")
        except Exception as e:
            still_failed.append(date)
            logger.error(f"❌ STILL FAILED: {date} - {str(e)}")

        # Longer sleep to avoid rate limits
        if idx < total:
            logger.info(f"Sleeping {sleep_between}s to avoid rate limits...")
            time.sleep(sleep_between)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("RETRY COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total retried: {total}")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Still failed: {len(still_failed)}")

    if still_failed:
        logger.warning(f"\nStill failing dates (may need manual investigation):")
        for date in still_failed:
            logger.warning(f"  - {date}")
    else:
        logger.info("\n🎉 All failed dates successfully recovered!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Retry failed dates from backfill')
    parser.add_argument('--from-log',
                       help='Extract failed dates from backfill log file')
    parser.add_argument('--sleep',
                       type=int,
                       default=30,
                       help='Seconds to sleep between retries (default: 30)')
    parser.add_argument('dates',
                       nargs='*',
                       help='Specific dates to retry (YYYY-MM-DD format)')

    args = parser.parse_args()

    # Get dates to retry
    if args.from_log:
        dates = extract_failed_dates_from_log(args.from_log)
        if not dates:
            logger.info("No failed dates found in log file!")
            sys.exit(0)
        logger.info(f"Extracted {len(dates)} failed dates from log")
    elif args.dates:
        dates = args.dates
    else:
        logger.error("Must provide either --from-log or specific dates")
        sys.exit(1)

    retry_dates(dates, args.sleep)
