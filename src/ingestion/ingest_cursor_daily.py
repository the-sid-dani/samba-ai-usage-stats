#!/usr/bin/env python3
"""
Cursor Daily Ingestion - Unified Usage + Spend

Fetches:
1. Daily usage metrics from /teams/daily-usage-data
2. Current cycle spend from /teams/spend
3. Calculates daily spend deltas
4. Loads to cursor_daily_metrics table
"""

import sys
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from google.cloud import bigquery, secretmanager
from cursor_client import CursorAdminClient

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_cursor_api_key(secret_client: secretmanager.SecretManagerServiceClient) -> str:
    """Fetch Cursor API key from Secret Manager"""
    project = os.getenv('CURSOR_SECRET_PROJECT', 'ai-workflows-459123')
    secret_id = os.getenv('CURSOR_SECRET_ID', 'cursor-api-key')
    version = os.getenv('CURSOR_SECRET_VERSION', 'latest')

    secret_path = f"projects/{project}/secrets/{secret_id}/versions/{version}"
    logger.info(f"Fetching Cursor API key from {secret_path}")

    response = secret_client.access_secret_version(name=secret_path)
    return response.payload.data.decode('UTF-8')


def transform_usage_record(record: Dict[str, Any], activity_date: datetime) -> Dict[str, Any]:
    """Transform API usage record to BigQuery schema"""
    return {
        'activity_date': activity_date.date().isoformat(),
        'user_email': record.get('email'),
        'user_id': record.get('userId'),
        'is_active': record.get('isActive', False),
        'total_lines_added': record.get('totalLinesAdded', 0),
        'total_lines_deleted': record.get('totalLinesDeleted', 0),
        'accepted_lines_added': record.get('acceptedLinesAdded', 0),
        'accepted_lines_deleted': record.get('acceptedLinesDeleted', 0),
        'total_applies': record.get('totalApplies', 0),
        'total_accepts': record.get('totalAccepts', 0),
        'total_rejects': record.get('totalRejects', 0),
        'total_tabs_shown': record.get('totalTabsShown', 0),
        'total_tabs_accepted': record.get('totalTabsAccepted', 0),
        'composer_requests': record.get('composerRequests', 0),
        'chat_requests': record.get('chatRequests', 0),
        'agent_requests': record.get('agentRequests', 0),
        'cmdk_usages': record.get('cmdkUsages', 0),
        'bugbot_usages': record.get('bugbotUsages', 0),
        'subscription_included_reqs': record.get('subscriptionIncludedReqs', 0),
        'usage_based_reqs': record.get('usageBasedReqs', 0),
        'api_key_reqs': record.get('apiKeyReqs', 0),
        'most_used_model': record.get('mostUsedModel', ''),
        'apply_most_used_extension': record.get('applyMostUsedExtension', ''),
        'tab_most_used_extension': record.get('tabMostUsedExtension', ''),
        'client_version': record.get('clientVersion', ''),
        'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
        'daily_spend_usd': None  # Will be calculated separately
    }


def get_previous_cumulative_spend(
    bq_client: bigquery.Client,
    user_email: str,
    current_date: datetime,
    billing_cycle_start: datetime
) -> float:
    """
    Get cumulative spend for user up to (but not including) current_date.

    This sums all daily_spend_usd values in the current billing cycle
    to reconstruct the cumulative total that the API would have shown yesterday.
    """
    query = """
        SELECT
            COALESCE(SUM(daily_spend_usd), 0) as cumulative_spend
        FROM `ai_usage_analytics.cursor_daily_metrics`
        WHERE user_email = @user_email
          AND activity_date < @current_date
          AND activity_date >= DATE(@billing_cycle_start)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
            bigquery.ScalarQueryParameter("current_date", "DATE", current_date.date()),
            bigquery.ScalarQueryParameter(
                "billing_cycle_start",
                "TIMESTAMP",
                billing_cycle_start.isoformat()
            ),
        ]
    )

    result = bq_client.query(query, job_config=job_config).result()
    row = next(iter(result), None)
    return float(row['cumulative_spend']) if row else 0.0


def calculate_daily_spend_deltas(
    bq_client: bigquery.Client,
    spend_members: List[Dict[str, Any]],
    billing_cycle_start: datetime,
    target_date: datetime
) -> Dict[str, float]:
    """
    Calculate daily spend delta for each user.

    Args:
        spend_members: List from /teams/spend API response
        billing_cycle_start: Cycle start timestamp
        target_date: Date being processed

    Returns:
        Dict[user_email, daily_delta_usd]
    """
    daily_deltas = {}

    for member in spend_members:
        user_email = member.get('email')
        if not user_email:
            continue

        # Current cumulative from API
        spend_cents = member.get('spendCents', 0)
        included_cents = member.get('includedSpendCents', 0)
        current_cumulative_usd = (spend_cents + included_cents) / 100

        # Previous cumulative from our database
        previous_cumulative = get_previous_cumulative_spend(
            bq_client,
            user_email,
            target_date,
            billing_cycle_start
        )

        # Calculate delta
        daily_delta = current_cumulative_usd - previous_cumulative

        # Validation
        if daily_delta < -0.01:  # Allow small rounding errors
            logger.warning(
                f"Negative delta for {user_email}: "
                f"current=${current_cumulative_usd:.2f}, "
                f"previous=${previous_cumulative:.2f}, "
                f"delta=${daily_delta:.2f}"
            )
            daily_delta = 0  # Don't store negative deltas

        daily_deltas[user_email] = round(daily_delta, 2)

    return daily_deltas


def load_to_bigquery(
    bq_client: bigquery.Client,
    records: List[Dict[str, Any]],
    table_id: str,
    target_date: datetime
) -> int:
    """Load records to BigQuery with deduplication"""
    if not records:
        logger.warning("No records to load")
        return 0

    # First, delete existing records for this date (deduplication)
    delete_query = """
        DELETE FROM `ai_usage_analytics.cursor_daily_metrics`
        WHERE activity_date = @target_date
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("target_date", "DATE", target_date.date()),
        ]
    )
    delete_job = bq_client.query(delete_query, job_config=job_config)
    delete_job.result()
    logger.info(f"Deleted existing records for {target_date.date()}")

    # Now append new records
    table_ref = bq_client.dataset('ai_usage_analytics').table('cursor_daily_metrics')

    load_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
    )

    job = bq_client.load_table_from_json(
        records,
        table_ref,
        job_config=load_config
    )
    job.result()  # Wait for completion

    logger.info(f"Loaded {len(records)} records to {table_id}")
    return len(records)


def update_daily_spend(
    bq_client: bigquery.Client,
    target_date: datetime,
    daily_deltas: Dict[str, float]
) -> int:
    """
    Update daily_spend_usd for users with spend deltas.
    """
    if not daily_deltas:
        logger.info("No spend deltas to update")
        return 0

    # Build UPDATE query with CASE statement (cast to NUMERIC)
    when_clauses = []
    for email, delta in daily_deltas.items():
        when_clauses.append(f"WHEN user_email = '{email}' THEN CAST({delta} AS NUMERIC)")

    when_clause_sql = "\n          ".join(when_clauses)

    query = f"""
        UPDATE `ai_usage_analytics.cursor_daily_metrics`
        SET daily_spend_usd = CASE
          {when_clause_sql}
        END
        WHERE activity_date = @target_date
          AND user_email IN UNNEST(@user_emails)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("target_date", "DATE", target_date.date()),
            bigquery.ArrayQueryParameter("user_emails", "STRING", list(daily_deltas.keys())),
        ]
    )

    job = bq_client.query(query, job_config=job_config)
    result = job.result()

    updated_rows = job.num_dml_affected_rows or 0
    logger.info(f"Updated {updated_rows} rows with daily spend for {target_date.date()}")
    return updated_rows


def main():
    """Main ingestion logic"""
    # Get target date (default: yesterday)
    target_date_str = os.getenv('TARGET_DATE')
    if target_date_str:
        target_date = datetime.fromisoformat(target_date_str).replace(tzinfo=timezone.utc)
    else:
        target_date = datetime.now(timezone.utc) - timedelta(days=1)
        target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    logger.info(f"Starting Cursor ingestion for {target_date.date()}")

    # Initialize clients
    secret_client = secretmanager.SecretManagerServiceClient()
    bq_client = bigquery.Client(
        project=os.getenv('TARGET_GCP_PROJECT', 'ai-workflows-459123')
    )

    cursor_api_key = get_cursor_api_key(secret_client)
    cursor_client = CursorAdminClient(cursor_api_key)

    # STEP 1: Fetch usage metrics
    logger.info("Step 1: Fetching usage metrics")
    end_date = target_date + timedelta(days=1)
    usage_response = cursor_client.get_daily_usage_data(target_date, end_date)

    # Filter to only target date (API returns range, we want single day)
    target_day_str = target_date.strftime('%Y-%m-%d')
    filtered_data = [
        record for record in usage_response.get('data', [])
        if record.get('day') == target_day_str
    ]

    logger.info(
        f"API returned {len(usage_response.get('data', []))} records, "
        f"filtered to {len(filtered_data)} for {target_day_str}"
    )

    usage_records = [
        transform_usage_record(record, target_date)
        for record in filtered_data
    ]

    # STEP 2: Load usage data to BigQuery
    logger.info("Step 2: Loading usage metrics to BigQuery")
    loaded_count = load_to_bigquery(
        bq_client,
        usage_records,
        'cursor_daily_metrics',
        target_date
    )

    # STEP 3: Fetch current cycle spend
    logger.info("Step 3: Fetching current cycle spending")
    spend_members, billing_cycle_start_ms = cursor_client.get_all_spend_pages()

    billing_cycle_start = datetime.fromtimestamp(
        billing_cycle_start_ms / 1000,
        tz=timezone.utc
    )
    logger.info(f"Billing cycle started: {billing_cycle_start}")

    # STEP 4: Calculate daily spend deltas
    logger.info("Step 4: Calculating daily spend deltas")
    daily_deltas = calculate_daily_spend_deltas(
        bq_client,
        spend_members,
        billing_cycle_start,
        target_date
    )

    users_with_spend = len([d for d in daily_deltas.values() if d > 0])
    logger.info(
        f"Calculated deltas for {len(daily_deltas)} users "
        f"({users_with_spend} with non-zero spend)"
    )

    # STEP 5: Update daily_spend_usd in BigQuery
    logger.info("Step 5: Updating daily spend in BigQuery")
    updated_count = update_daily_spend(bq_client, target_date, daily_deltas)

    # Summary
    logger.info("=" * 60)
    logger.info(f"Cursor ingestion complete for {target_date.date()}")
    logger.info(f"  Usage records loaded: {loaded_count}")
    logger.info(f"  Spend records updated: {updated_count}")
    logger.info(f"  Users with spend > $0: {users_with_spend}")
    logger.info(f"  Total daily spend: ${sum(daily_deltas.values()):.2f}")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception(f"Cursor ingestion failed: {e}")
        sys.exit(1)
