#!/usr/bin/env python3
"""
Claude Data Historical Backfill Script

Backfills historical data from Jan 1, 2025 to Oct 18, 2025 in daily increments.

Usage:
    python backfill_claude_data.py --start-date 2025-01-01 --end-date 2025-10-18
    python backfill_claude_data.py  # defaults to Jan 1 - yesterday
"""

from datetime import datetime, timedelta
import time
import argparse
import logging
import sys
import os

# Add parent directory to path to import ingest_claude_data
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_claude_data import ClaudeDataIngestion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_date_range(start_date: str, end_date: str, sleep_between_days: int = 2):
    """
    Backfill historical data in daily increments.

    Args:
        start_date: YYYY-MM-DD format (inclusive)
        end_date: YYYY-MM-DD format (inclusive)
        sleep_between_days: Seconds to wait between days (for rate limiting)
    """
    ingestion = ClaudeDataIngestion()

    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    total_days = (end - current).days + 1
    success_count = 0
    failure_count = 0
    failed_dates = []

    logger.info(f"Starting backfill: {start_date} to {end_date} ({total_days} days)")

    day_num = 0
    while current <= end:
        day_num += 1
        date_str = current.strftime('%Y-%m-%d')

        logger.info(f"\n{'='*60}")
        logger.info(f"[{day_num}/{total_days}] Processing {date_str}...")
        logger.info(f"{'='*60}")

        try:
            ingestion.ingest_daily(date_str)
            success_count += 1
            logger.info(f"✅ SUCCESS: {date_str}")
        except Exception as e:
            failure_count += 1
            failed_dates.append(date_str)
            logger.error(f"❌ FAILED: {date_str} - {str(e)}")
            # Continue with next date instead of stopping

        current += timedelta(days=1)

        # Progress update every 10 days
        if day_num % 10 == 0:
            logger.info(f"\nProgress: {day_num}/{total_days} days | ✅ {success_count} success | ❌ {failure_count} failed")

        # Rate limiting - sleep between requests
        if current <= end:  # Don't sleep after last day
            time.sleep(sleep_between_days)

    # Final summary
    logger.info(f"\n{'='*60}")
    logger.info("BACKFILL COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total days processed: {total_days}")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed: {failure_count}")

    if failed_dates:
        logger.warning(f"\nFailed dates (retry manually):")
        for date in failed_dates:
            logger.warning(f"  - {date}")
    else:
        logger.info("\n🎉 All days successfully backfilled!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill Claude historical data')
    parser.add_argument('--start-date',
                       default='2025-01-01',
                       help='Start date (YYYY-MM-DD), defaults to 2025-01-01')
    parser.add_argument('--end-date',
                       default=(datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='End date (YYYY-MM-DD), defaults to yesterday')
    parser.add_argument('--sleep',
                       type=int,
                       default=2,
                       help='Seconds to sleep between days (default: 2)')
    args = parser.parse_args()

    backfill_date_range(args.start_date, args.end_date, args.sleep)
