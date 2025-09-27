#!/usr/bin/env python3
"""Deploy BigQuery views with template substitution."""

import os
import sys
from google.cloud import bigquery

def deploy_views(project_id: str, dataset: str):
    """Deploy all analytics views to BigQuery."""
    client = bigquery.Client(project=project_id)

    views = [
        "vw_monthly_finance.sql",
        "vw_productivity_metrics.sql",
        "vw_cost_allocation.sql",
        "vw_executive_summary.sql"
    ]

    for view_file in views:
        view_path = f"sql/views/{view_file}"
        print(f"Deploying view: {view_file}")

        try:
            # Read SQL file
            with open(view_path, 'r') as f:
                sql = f.read()

            # Replace template variables
            sql = sql.replace("${project_id}", project_id)
            sql = sql.replace("${dataset}", dataset)

            # Execute query
            query_job = client.query(sql)
            query_job.result()  # Wait for completion

            print(f"✅ Successfully deployed: {view_file}")

        except Exception as e:
            print(f"❌ Failed to deploy {view_file}: {e}")
            return False

    print("🎉 All views deployed successfully!")
    return True

if __name__ == "__main__":
    project_id = "ai-workflows-459123"
    dataset = "ai_usage_analytics"

    success = deploy_views(project_id, dataset)
    sys.exit(0 if success else 1)