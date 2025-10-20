#!/usr/bin/env python3
"""
Simple validation script - runs key queries and shows results
"""

from google.cloud import bigquery

def run_validation():
    client = bigquery.Client(project="ai-workflows-459123")

    print("="*80)
    print("BIGQUERY DATA VALIDATION")
    print("="*80)

    # Query 1: Cursor Total Cost
    print("\n[1] Cursor Total Cost (Expected: ~$691.50)")
    print("-" * 80)
    query1 = """
    SELECT
      SUM(total_spend_cents) / 100.0 AS total_cost_usd,
      SUM(spend_cents) / 100.0 AS actual_spend_usd,
      SUM(included_spend_cents) / 100.0 AS included_spend_usd,
      COUNT(DISTINCT user_email) AS unique_users
    FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
    WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
    """
    for row in client.query(query1).result():
        print(f"Total Cost: ${row.total_cost_usd:.2f}")
        print(f"Actual Spend: ${row.actual_spend_usd:.2f}")
        print(f"Included Spend: ${row.included_spend_usd:.2f}")
        print(f"Unique Users: {row.unique_users}")

    # Query 2: Claude Total Cost
    print("\n[2] Claude Total Cost")
    print("-" * 80)
    query2 = """
    SELECT
      SUM(amount_usd) AS total_cost_usd,
      COUNT(DISTINCT organization_id) AS unique_orgs,
      COUNT(DISTINCT model) AS unique_models
    FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
    WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
    """
    for row in client.query(query2).result():
        print(f"Total Cost: ${row.total_cost_usd:.2f}")
        print(f"Unique Orgs: {row.unique_orgs}")
        print(f"Unique Models: {row.unique_models}")

    # Query 3: Data Completeness Check
    print("\n[3] Data Completeness (Missing Dates)")
    print("-" * 80)
    query3 = """
    WITH date_range AS (
      SELECT date
      FROM UNNEST(GENERATE_DATE_ARRAY('2025-10-03', '2025-11-03')) AS date
    ),
    cursor_dates AS (
      SELECT DISTINCT snapshot_date AS date
      FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
      WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
    ),
    claude_dates AS (
      SELECT DISTINCT activity_date AS date
      FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
      WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
    )
    SELECT
      dr.date,
      CASE WHEN cd.date IS NOT NULL THEN TRUE ELSE FALSE END AS has_cursor,
      CASE WHEN cld.date IS NOT NULL THEN TRUE ELSE FALSE END AS has_claude
    FROM date_range dr
    LEFT JOIN cursor_dates cd ON dr.date = cd.date
    LEFT JOIN claude_dates cld ON dr.date = cld.date
    WHERE cd.date IS NULL OR cld.date IS NULL
    ORDER BY dr.date
    """
    missing = list(client.query(query3).result())
    if missing:
        print(f"Found {len(missing)} dates with missing data:")
        for row in missing:
            cursor_status = "✓" if row.has_cursor else "✗"
            claude_status = "✓" if row.has_claude else "✗"
            print(f"  {row.date}: Cursor {cursor_status}, Claude {claude_status}")
    else:
        print("✓ All dates have complete data")

    # Query 4: Data Quality Issues
    print("\n[4] Data Quality Check")
    print("-" * 80)
    query4 = """
    SELECT
      'cursor_usage_stats' AS table_name,
      COUNT(*) AS total_records,
      COUNTIF(user_email IS NULL) AS null_emails,
      COUNTIF(activity_date > CURRENT_DATE()) AS future_dates,
      COUNTIF(total_accepts < 0 OR total_rejects < 0) AS negative_values
    FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
    WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
    """
    for row in client.query(query4).result():
        issues = row.null_emails + row.future_dates + row.negative_values
        if issues > 0:
            print(f"✗ {row.table_name}: {issues} quality issues found")
            print(f"  - Null emails: {row.null_emails}")
            print(f"  - Future dates: {row.future_dates}")
            print(f"  - Negative values: {row.negative_values}")
        else:
            print(f"✓ {row.table_name}: No quality issues ({row.total_records} records)")

    print("\n" + "="*80)
    print("Validation Complete")
    print("="*80)

if __name__ == "__main__":
    run_validation()
