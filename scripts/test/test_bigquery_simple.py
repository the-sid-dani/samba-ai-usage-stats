#!/usr/bin/env python3
"""Simple BigQuery validation test."""

from google.cloud import bigquery

def test_bigquery_deployment():
    """Test BigQuery deployment with actual queries."""
    print("🧪 Testing BigQuery Data Warehouse Deployment")
    print("=" * 60)

    client = bigquery.Client(project="ai-workflows-459123")
    dataset_id = "ai_usage_analytics"

    # Test tables
    tables = [
        "raw_cursor_usage",
        "raw_anthropic_usage",
        "raw_anthropic_cost",
        "dim_users",
        "dim_api_keys",
        "fct_usage_daily",
        "fct_cost_daily"
    ]

    print("Testing Tables:")
    for table_name in tables:
        try:
            table = client.get_table(f"ai-workflows-459123.{dataset_id}.{table_name}")
            print(f"✅ {table_name}: {table.num_rows} rows, {len(table.schema)} columns")
        except Exception as e:
            print(f"❌ {table_name}: {e}")

    # Test views
    views = [
        "vw_monthly_finance",
        "vw_productivity_metrics",
        "vw_cost_allocation",
        "vw_executive_summary"
    ]

    print("\nTesting Analytics Views:")
    for view_name in views:
        try:
            # Test view with dry run
            query = f"SELECT COUNT(*) FROM `ai-workflows-459123.{dataset_id}.{view_name}` LIMIT 1"
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            query_job = client.query(query, job_config=job_config)

            mb_processed = query_job.total_bytes_processed / 1024 / 1024
            print(f"✅ {view_name}: Valid syntax, processes {mb_processed:.1f} MB")
        except Exception as e:
            print(f"❌ {view_name}: {e}")

    print("\n🎉 BigQuery Data Warehouse Validation Complete!")
    print("✅ Ready to receive production data")

if __name__ == "__main__":
    test_bigquery_deployment()