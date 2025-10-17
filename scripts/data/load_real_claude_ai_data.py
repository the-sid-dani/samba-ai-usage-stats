#!/usr/bin/env python3
"""Process real claude.ai audit logs and upload to BigQuery."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import csv
import json
import uuid
from datetime import datetime, date
from google.cloud import bigquery

def parse_audit_logs_csv(file_path: str):
    """Parse the actual claude.ai audit logs CSV format with robust JSON handling."""
    print("🔍 Processing claude.ai audit logs CSV...")

    events = []
    parsing_stats = {"total": 0, "success": 0, "failures": 0}

    # Create a temporary client for robust parsing
    import sys
    sys.path.append('src')
    from src.ingestion.claude_ai_client import ClaudeAiClient

    # Mock config for temporary client
    class MockConfig:
        def get(self, key, default=None):
            return default

    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for i, row in enumerate(reader):
            parsing_stats["total"] += 1

            try:
                # Create temporary client for robust parsing
                temp_client = ClaudeAiClient.__new__(ClaudeAiClient)
                temp_client.parsing_stats = {"total_rows": 0, "successful_parses": 0, "parsing_failures": 0, "fallback_successes": 0}

                # Use robust JSON parsing
                actor_info = temp_client._parse_json_robust(row.get('actor_info', '{}'))
                event_info = temp_client._parse_json_robust(row.get('event_info', '{}'))
                entity_info = temp_client._parse_json_robust(row.get('entity_info', '{}'))

                parsing_stats["success"] += 1

                # Extract core data
                actor_email = actor_info.get('metadata', {}).get('email_address', '')
                actor_name = actor_info.get('name', '')
                event_type = row['event']
                created_at = row['created_at']
                client_platform = row['client_platform']

                # Parse timestamp
                event_timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                event_date = event_timestamp.date()

                # Extract entity metadata
                conversation_id = None
                project_id = None
                file_id = None

                if entity_info.get('type') == 'chat_conversation':
                    conversation_id = entity_info.get('uuid')
                    if 'metadata' in entity_info and 'project_uuid' in entity_info['metadata']:
                        project_id = entity_info['metadata']['project_uuid']
                elif entity_info.get('type') == 'chat_project':
                    project_id = entity_info.get('uuid')
                elif entity_info.get('type') == 'file':
                    file_id = entity_info.get('uuid')

                # Derive interaction type
                interaction_type = derive_interaction_type(event_type, client_platform)

                # Create processed event
                processed_event = {
                    'actor_email': actor_email,
                    'actor_name': actor_name,
                    'event_type': event_type,
                    'event_timestamp': event_timestamp.isoformat(),
                    'event_date': event_date.isoformat(),
                    'conversation_id': conversation_id,
                    'project_id': project_id,
                    'file_name': file_id,  # Using file_id as file_name for now
                    'file_size': None,
                    'message_count': None,
                    'estimated_session_minutes': estimate_session_minutes(event_type),
                    'interaction_type': interaction_type,
                    'ingest_date': date.today().isoformat(),
                    'ingest_timestamp': datetime.utcnow().isoformat() + 'Z',
                    'request_id': str(uuid.uuid4()),
                    'raw_response': json.dumps(row)
                }

                events.append(processed_event)

                if i % 10 == 0:
                    print(f"  Processed {i+1} events...")

            except Exception as e:
                parsing_stats["failures"] += 1
                print(f"Warning: Failed to parse row {i+1}: {e}")
                continue

    print(f"✅ Successfully processed {len(events)} events")
    print(f"📊 Parsing Quality: {parsing_stats['success']}/{parsing_stats['total']} successful ({parsing_stats['success']/parsing_stats['total']*100:.1f}%)")
    print(f"❌ Parse Failures: {parsing_stats['failures']} rows")

    return events

def derive_interaction_type(event_type: str, client_platform: str) -> str:
    """Derive interaction type from event and platform data."""
    if 'conversation' in event_type.lower():
        if client_platform == 'desktop_app':
            return 'coding_assistance'
        elif client_platform == 'web_claude_ai':
            return 'chat'
        else:
            return 'general'
    elif 'file' in event_type.lower():
        return 'document_review'
    elif 'project' in event_type.lower():
        return 'analysis'
    else:
        return 'general'

def estimate_session_minutes(event_type: str) -> int:
    """Estimate session time based on event type."""
    if 'conversation_created' in event_type:
        return 15  # Average conversation length
    elif 'file_uploaded' in event_type:
        return 5   # File upload interaction
    elif 'project' in event_type:
        return 30  # Project work
    elif 'sign' in event_type:
        return 1   # Login/logout
    else:
        return 2   # Other interactions

def upload_to_bigquery(events):
    """Upload processed events to BigQuery."""
    print("📤 Uploading to BigQuery...")

    client = bigquery.Client(project='ai-workflows-459123')
    table_id = 'ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events'

    # Get table reference
    table = client.get_table(table_id)

    # Insert data in batches
    batch_size = 1000
    total_inserted = 0

    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]

        errors = client.insert_rows_json(table, batch)

        if errors:
            print(f"❌ Batch {i//batch_size + 1} errors: {errors[:3]}...")
        else:
            total_inserted += len(batch)
            print(f"✅ Batch {i//batch_size + 1}: {len(batch)} records inserted")

    print(f"🎉 Total inserted: {total_inserted}/{len(events)} events")
    return total_inserted

def analyze_data_summary(events):
    """Analyze the processed data for summary."""
    print("\n📊 DATA ANALYSIS SUMMARY:")
    print("=" * 40)

    # Event type distribution
    event_types = {}
    users = set()
    platforms = {}
    interaction_types = {}
    dates = set()

    for event in events:
        event_type = event['event_type']
        user = event['actor_email']
        platform = event.get('interaction_type', 'unknown')
        event_date = event['event_date']

        event_types[event_type] = event_types.get(event_type, 0) + 1
        users.add(user)
        platforms[platform] = platforms.get(platform, 0) + 1
        dates.add(event_date)

    print(f"📅 Date Range: {min(dates)} to {max(dates)}")
    print(f"👥 Unique Users: {len(users)}")
    print(f"📊 Total Events: {len(events)}")

    print(f"\n🎯 Top Event Types:")
    for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {event_type}: {count}")

    print(f"\n🖥️ Interaction Types:")
    for interaction_type, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
        print(f"  {interaction_type}: {count}")

    print(f"\n👤 Top Users:")
    user_counts = {}
    for event in events:
        user = event['actor_email']
        user_counts[user] = user_counts.get(user, 0) + 1

    for user, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {user}: {count} events")

def main():
    """Main processing function."""
    audit_file = "sql/tables/audit_logs 3.csv"

    if not os.path.exists(audit_file):
        print(f"❌ Audit file not found: {audit_file}")
        return

    print("🚀 Claude.ai Audit Logs Processing Pipeline")
    print("=" * 50)

    # Process CSV
    events = parse_audit_logs_csv(audit_file)

    if not events:
        print("❌ No events processed")
        return

    # Analyze data
    analyze_data_summary(events)

    # Upload to BigQuery
    try:
        uploaded_count = upload_to_bigquery(events)
        print(f"\n🎉 SUCCESS: {uploaded_count} claude.ai audit events uploaded to BigQuery!")

        # Verify in BigQuery
        print("\n🔍 Verifying data in BigQuery...")
        client = bigquery.Client(project='ai-workflows-459123')

        verify_query = f"""
        SELECT
          event_date,
          COUNT(*) as event_count,
          COUNT(DISTINCT actor_email) as unique_users,
          COUNT(DISTINCT event_type) as event_types
        FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
        WHERE ingest_date = '{date.today().isoformat()}'
        GROUP BY event_date
        ORDER BY event_date DESC
        LIMIT 5
        """

        results = client.query(verify_query).result()

        print("📋 BigQuery Verification:")
        for row in results:
            print(f"  {row.event_date}: {row.event_count} events, {row.unique_users} users, {row.event_types} event types")

    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    main()