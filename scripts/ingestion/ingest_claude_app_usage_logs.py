#!/usr/bin/env python3
"""
Claude App Usage Logs Ingestion

Loads Claude.ai activity export CSV into BigQuery for productivity metrics.

Usage:
    python ingest_claude_app_usage_logs.py <csv_file_path>
    python ingest_claude_app_usage_logs.py production-data/claude-logs.csv
"""

import sys
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
from google.cloud import bigquery

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_json_field(field_str: str) -> Dict:
    """Parse string representation of dict to actual dict"""
    if not field_str or field_str == '{}':
        return {}
    try:
        # Use eval since the format is Python dict notation, not JSON
        return eval(field_str)
    except:
        logger.warning(f"Failed to parse field: {field_str[:100]}")
        return {}


def transform_record(row: Dict[str, str]) -> Dict[str, Any]:
    """Transform CSV row to BigQuery schema"""

    # Parse JSON fields
    actor_info = parse_json_field(row.get('actor_info', '{}'))
    entity_info = parse_json_field(row.get('entity_info', '{}'))
    event_info = parse_json_field(row.get('event_info', '{}'))

    # Extract user information
    user_email = actor_info.get('metadata', {}).get('email_address')
    if not user_email:
        logger.warning(f"Skipping record without email: {row.get('created_at')}")
        return None

    # Parse timestamp
    activity_timestamp = datetime.fromisoformat(
        row['created_at'].replace('Z', '+00:00')
    )

    # Extract entity metadata
    entity_metadata = entity_info.get('metadata', {})
    project_uuid = entity_metadata.get('project_uuid')

    # Determine conversation UUID
    conversation_uuid = None
    if entity_info.get('type') == 'chat_conversation':
        conversation_uuid = entity_info.get('uuid')

    return {
        'activity_timestamp': activity_timestamp.isoformat(),
        'activity_date': activity_timestamp.date().isoformat(),
        'user_email': user_email,
        'user_name': actor_info.get('name'),
        'user_uuid': actor_info.get('uuid'),
        'event_type': row.get('event'),
        'event_info': json.dumps(event_info) if event_info else None,
        'entity_type': entity_info.get('type'),
        'entity_uuid': entity_info.get('uuid'),
        'conversation_uuid': conversation_uuid,
        'project_uuid': project_uuid,
        'client_platform': row.get('client_platform') or None,
        'device_id': row.get('device_id') or None,
        'user_agent': row.get('user_agent') or None,
        'ip_address': row.get('ip_address') or None,
        'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
        'data_source': 'claude_activity_export'
    }


def load_csv_to_bigquery(
    csv_path: str,
    project_id: str = 'ai-workflows-459123',
    dataset_id: str = 'ai_usage_analytics',
    table_id: str = 'claude_app_usage_logs'
):
    """Load CSV file into BigQuery"""

    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info(f"Reading CSV: {csv_path}")

    # Read and transform CSV
    records = []
    skipped = 0

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transformed = transform_record(row)
            if transformed:
                records.append(transformed)
            else:
                skipped += 1

    logger.info(f"Transformed {len(records)} records (skipped {skipped})")

    if not records:
        logger.error("No valid records to load")
        return

    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # Check date range
    dates = [r['activity_date'] for r in records]
    min_date = min(dates)
    max_date = max(dates)
    logger.info(f"Date range: {min_date} to {max_date}")

    # Delete existing data for this date range (deduplication)
    delete_query = f"""
        DELETE FROM `{table_ref}`
        WHERE activity_date BETWEEN '{min_date}' AND '{max_date}'
    """
    logger.info(f"Deleting existing data for {min_date} to {max_date}")
    delete_job = client.query(delete_query)
    delete_job.result()
    deleted_rows = delete_job.num_dml_affected_rows or 0
    logger.info(f"Deleted {deleted_rows} existing rows")

    # Load data using streaming insert (handles JSON fields properly)
    logger.info(f"Loading {len(records)} records to {table_ref}")

    errors = client.insert_rows_json(table_ref, records)

    if errors:
        logger.error(f"Errors during insert: {errors}")
        raise Exception(f"Failed to insert rows: {errors}")

    logger.info(f"✓ Successfully loaded {len(records)} records")

    # Verify
    verify_query = f"""
        SELECT
            activity_date,
            COUNT(*) as records,
            COUNT(DISTINCT user_email) as users,
            COUNT(DISTINCT event_type) as event_types
        FROM `{table_ref}`
        WHERE activity_date BETWEEN '{min_date}' AND '{max_date}'
        GROUP BY activity_date
        ORDER BY activity_date DESC
    """

    logger.info("Verifying data...")
    verify_result = client.query(verify_query).result()

    print("\n" + "="*60)
    print("LOAD SUMMARY")
    print("="*60)
    for row in verify_result:
        print(f"  {row.activity_date}: {row.records} records, "
              f"{row.users} users, {row.event_types} event types")
    print("="*60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_claude_app_usage_logs.py <csv_file_path>")
        print("Example: python ingest_claude_app_usage_logs.py production-data/claude-logs.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    try:
        load_csv_to_bigquery(csv_path)
        logger.info("✓ Ingestion complete")
        return 0
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
