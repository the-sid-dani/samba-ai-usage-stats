#!/usr/bin/env python3
"""Sample queries to test three-platform data before creating BigQuery views."""

from google.cloud import bigquery
from datetime import date, timedelta

def test_platform_data():
    """Test queries across all three platforms."""
    client = bigquery.Client(project='ai-workflows-459123')

    print("🔍 THREE-PLATFORM DATA TESTING")
    print("=" * 50)

    # Query 1: Platform coverage check
    print("1️⃣ PLATFORM COVERAGE CHECK")
    print("-" * 30)

    coverage_query = """
    -- Check what platforms we have data for
    SELECT
      'cursor' as platform,
      COUNT(*) as records,
      COUNT(DISTINCT email) as unique_users,
      MIN(usage_date) as earliest_date,
      MAX(usage_date) as latest_date
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'

    UNION ALL

    SELECT
      CONCAT('anthropic_',
        CASE
          WHEN workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR' THEN 'claude_code'
          WHEN workspace_id IS NULL THEN 'claude_api'
          ELSE 'unknown'
        END
      ) as platform,
      COUNT(*) as records,
      COUNT(DISTINCT api_key_id) as unique_users,
      MIN(usage_date) as earliest_date,
      MAX(usage_date) as latest_date
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
    GROUP BY platform

    UNION ALL

    SELECT
      'claude_ai' as platform,
      COUNT(*) as records,
      COUNT(DISTINCT actor_email) as unique_users,
      MIN(event_date) as earliest_date,
      MAX(event_date) as latest_date
    FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
    WHERE event_date >= '2025-09-27'

    ORDER BY platform
    """

    try:
        results = client.query(coverage_query).result()

        for row in results:
            print(f"  {row.platform}: {row.records} records, {row.unique_users} users")
            print(f"    Date range: {row.earliest_date} to {row.latest_date}")

    except Exception as e:
        print(f"❌ Coverage query error: {e}")

    # Query 2: User activity across platforms
    print("\n2️⃣ CROSS-PLATFORM USER ACTIVITY")
    print("-" * 35)

    user_activity_query = """
    -- Find users active across multiple platforms
    WITH cursor_users AS (
      SELECT DISTINCT
        email as user_email,
        'cursor' as platform,
        usage_date
      FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
      WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
    ),

    claude_ai_users AS (
      SELECT DISTINCT
        actor_email as user_email,
        'claude_ai' as platform,
        event_date as usage_date
      FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
      WHERE event_date >= '2025-09-27'
        AND actor_email LIKE '%samba.tv'
    ),

    all_platform_users AS (
      SELECT user_email, platform, usage_date FROM cursor_users
      UNION ALL
      SELECT user_email, platform, usage_date FROM claude_ai_users
    )

    SELECT
      user_email,
      COUNT(DISTINCT platform) as platforms_used,
      ARRAY_AGG(DISTINCT platform) as platforms,
      COUNT(DISTINCT usage_date) as active_days,
      MIN(usage_date) as first_activity,
      MAX(usage_date) as last_activity
    FROM all_platform_users
    GROUP BY user_email
    HAVING COUNT(DISTINCT platform) > 1  -- Multi-platform users only
    ORDER BY platforms_used DESC, active_days DESC
    LIMIT 10
    """

    try:
        results = client.query(user_activity_query).result()

        print("Multi-platform users:")
        for row in results:
            platforms_str = ', '.join(row.platforms)
            print(f"  {row.user_email}: {row.platforms_used} platforms ({platforms_str})")
            print(f"    {row.active_days} active days ({row.first_activity} to {row.last_activity})")

    except Exception as e:
        print(f"❌ User activity error: {e}")

    # Query 3: Daily activity patterns
    print("\n3️⃣ DAILY ACTIVITY PATTERNS")
    print("-" * 28)

    daily_pattern_query = """
    -- Daily activity across platforms for recent dates
    WITH daily_activity AS (
      SELECT
        usage_date,
        'cursor' as platform,
        COUNT(*) as activity_count,
        COUNT(DISTINCT email) as unique_users
      FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
      WHERE ingest_date >= '2025-09-27'
        AND usage_date >= '2025-09-25'
        AND email LIKE '%samba.tv'
      GROUP BY usage_date

      UNION ALL

      SELECT
        event_date as usage_date,
        'claude_ai' as platform,
        COUNT(*) as activity_count,
        COUNT(DISTINCT actor_email) as unique_users
      FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
      WHERE event_date >= '2025-09-25'
        AND actor_email LIKE '%samba.tv'
      GROUP BY event_date
    )

    SELECT
      usage_date,
      SUM(CASE WHEN platform = 'cursor' THEN activity_count ELSE 0 END) as cursor_activity,
      SUM(CASE WHEN platform = 'claude_ai' THEN activity_count ELSE 0 END) as claude_ai_activity,
      SUM(CASE WHEN platform = 'cursor' THEN unique_users ELSE 0 END) as cursor_users,
      SUM(CASE WHEN platform = 'claude_ai' THEN unique_users ELSE 0 END) as claude_ai_users,
      SUM(activity_count) as total_activity,
      COUNT(DISTINCT platform) as active_platforms
    FROM daily_activity
    GROUP BY usage_date
    ORDER BY usage_date DESC
    """

    try:
        results = client.query(daily_pattern_query).result()

        print("Recent daily activity:")
        for row in results:
            print(f"  {row.usage_date}: {row.total_activity} total events")
            print(f"    Cursor: {row.cursor_activity} events, {row.cursor_users} users")
            print(f"    Claude.ai: {row.claude_ai_activity} events, {row.claude_ai_users} users")
            print(f"    Active platforms: {row.active_platforms}")

    except Exception as e:
        print(f"❌ Daily pattern error: {e}")

    # Query 4: Top users by platform
    print("\n4️⃣ TOP USERS BY PLATFORM")
    print("-" * 25)

    top_users_query = """
    -- Top users on each platform
    WITH cursor_top AS (
      SELECT
        'cursor' as platform,
        email as user_email,
        COUNT(*) as sessions,
        SUM(total_lines_added) as lines_added,
        SUM(accepted_lines_added) as lines_accepted,
        SAFE_DIVIDE(SUM(accepted_lines_added), SUM(total_lines_added)) as acceptance_rate
      FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
      WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
      GROUP BY email
      ORDER BY sessions DESC
      LIMIT 5
    ),

    claude_ai_top AS (
      SELECT
        'claude_ai' as platform,
        actor_email as user_email,
        COUNT(*) as sessions,
        NULL as lines_added,
        NULL as lines_accepted,
        NULL as acceptance_rate
      FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
      WHERE event_date >= '2025-09-27'
        AND actor_email LIKE '%samba.tv'
      GROUP BY actor_email
      ORDER BY sessions DESC
      LIMIT 5
    )

    SELECT * FROM cursor_top
    UNION ALL
    SELECT * FROM claude_ai_top
    ORDER BY platform, sessions DESC
    """

    try:
        results = client.query(top_users_query).result()

        current_platform = None
        for row in results:
            if row.platform != current_platform:
                print(f"\n{row.platform.upper()} Top Users:")
                current_platform = row.platform

            if row.platform == 'cursor':
                print(f"  {row.user_email}: {row.sessions} sessions, {row.lines_added:,} lines ({row.acceptance_rate:.1%} accepted)")
            else:
                print(f"  {row.user_email}: {row.sessions} events")

    except Exception as e:
        print(f"❌ Top users error: {e}")

    # Query 5: Data quality check
    print("\n5️⃣ DATA QUALITY CHECK")
    print("-" * 20)

    quality_query = """
    -- Check data completeness and quality
    SELECT
      'cursor' as source,
      COUNT(*) as total_records,
      COUNT(CASE WHEN email IS NOT NULL AND email != '' THEN 1 END) as has_user_email,
      COUNT(CASE WHEN total_lines_added > 0 THEN 1 END) as has_productivity_data,
      COUNT(CASE WHEN usage_date IS NOT NULL THEN 1 END) as has_date
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'

    UNION ALL

    SELECT
      'claude_ai' as source,
      COUNT(*) as total_records,
      COUNT(CASE WHEN actor_email IS NOT NULL AND actor_email != '' THEN 1 END) as has_user_email,
      COUNT(CASE WHEN event_type IN ('conversation_created', 'project_created') THEN 1 END) as has_productivity_data,
      COUNT(CASE WHEN event_date IS NOT NULL THEN 1 END) as has_date
    FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
    WHERE event_date >= '2025-09-27'

    UNION ALL

    SELECT
      'anthropic' as source,
      COUNT(*) as total_records,
      COUNT(CASE WHEN api_key_id IS NOT NULL AND api_key_id != 'unknown' THEN 1 END) as has_user_email,
      COUNT(CASE WHEN uncached_input_tokens > 0 OR output_tokens > 0 THEN 1 END) as has_productivity_data,
      COUNT(CASE WHEN usage_date IS NOT NULL THEN 1 END) as has_date
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
    """

    try:
        results = client.query(quality_query).result()

        print("Data quality metrics:")
        for row in results:
            email_pct = (row.has_user_email / row.total_records) * 100 if row.total_records > 0 else 0
            data_pct = (row.has_productivity_data / row.total_records) * 100 if row.total_records > 0 else 0
            date_pct = (row.has_date / row.total_records) * 100 if row.total_records > 0 else 0

            print(f"  {row.source}: {row.total_records} records")
            print(f"    User attribution: {email_pct:.1f}%")
            print(f"    Productivity data: {data_pct:.1f}%")
            print(f"    Date completeness: {date_pct:.1f}%")

    except Exception as e:
        print(f"❌ Quality check error: {e}")

if __name__ == "__main__":
    test_platform_data()