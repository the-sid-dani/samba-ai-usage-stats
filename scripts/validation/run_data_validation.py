#!/usr/bin/env python3
"""
Data Validation Script for BigQuery AI Usage Analytics
Runs validation queries and compares results against expected dashboard values
"""

import os
from google.cloud import bigquery
from datetime import datetime
from typing import Dict, List, Any
import json

# Expected values from dashboards (Oct 3 - Nov 3, 2025)
EXPECTED_VALUES = {
    "cursor": {
        "total_tokens_millions": 950.2,
        "total_cost_usd": 691.50,
        "model_breakdown": {
            "Auto": {"tokens_millions": 412.2, "cost": 151.53},
            "claude-4.5-sonnet-thinking": {"tokens_millions": 146.4, "cost": 150.84},
            "claude-4-sonnet": {"tokens_millions": 155.7, "cost": 133.64},
            "claude-4-sonnet-1m-thinking": {"tokens_millions": 95.1, "cost": 113.13},
            "gpt-5": {"tokens_millions": 106.0, "cost": 96.00},
            "claude-4-sonnet-thinking": {"tokens_millions": 29.1, "cost": 41.43},
            "gemini-2.5-pro": {"tokens_millions": 2.9, "cost": 3.02},
            "gpt-5-fast": {"tokens_millions": 0.628, "cost": 0.61},
            "claude-4.5-sonnet": {"tokens_millions": 0.2597, "cost": 0.45},
            "gpt-5-codex": {"tokens_millions": 0.5972, "cost": 0.44},
        }
    },
    "claude": {
        "active_users": 39,
        "user_growth_percent": 15.0
    }
}

# Tolerance thresholds for validation
TOLERANCE = {
    "tokens_percent": 2.0,  # 2% tolerance for token counts
    "cost_percent": 1.0,    # 1% tolerance for cost amounts
    "count_absolute": 2     # Absolute tolerance for user counts
}


class DataValidator:
    def __init__(self, project_id: str = "ai-workflows-459123"):
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
        self.validation_results = []

    def run_query(self, query: str, query_name: str) -> List[Dict]:
        """Execute a BigQuery query and return results"""
        print(f"\n{'='*80}")
        print(f"Running: {query_name}")
        print(f"{'='*80}")

        try:
            query_job = self.client.query(query)
            results = query_job.result()

            rows = [dict(row) for row in results]
            print(f"✓ Query completed successfully. Rows returned: {len(rows)}")

            # Print results
            if rows:
                for row in rows:
                    print(f"  {row}")

            return rows

        except Exception as e:
            print(f"✗ Query failed: {str(e)}")
            return []

    def validate_cursor_totals(self) -> Dict[str, Any]:
        """Validate Cursor total token usage and cost"""
        query = """
        SELECT
          SUM(total_tokens) AS total_tokens,
          ROUND(SUM(total_tokens) / 1000000, 2) AS total_tokens_millions,
          COUNT(DISTINCT user_email) AS unique_users,
          MIN(activity_date) AS earliest_date,
          MAX(activity_date) AS latest_date
        FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
        WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
        """

        results = self.run_query(query, "Cursor Total Usage Validation")

        if not results:
            return {"status": "FAILED", "reason": "No data returned"}

        actual = results[0]
        expected_tokens = EXPECTED_VALUES["cursor"]["total_tokens_millions"]

        # Calculate variance
        variance_percent = abs(actual["total_tokens_millions"] - expected_tokens) / expected_tokens * 100

        status = "PASSED" if variance_percent <= TOLERANCE["tokens_percent"] else "FAILED"

        return {
            "status": status,
            "metric": "Cursor Total Tokens",
            "expected": expected_tokens,
            "actual": actual["total_tokens_millions"],
            "variance_percent": round(variance_percent, 2),
            "tolerance": TOLERANCE["tokens_percent"],
            "details": actual
        }

    def validate_cursor_cost(self) -> Dict[str, Any]:
        """Validate Cursor total cost"""
        query = """
        SELECT
          SUM(total_cost) AS total_cost_usd,
          COUNT(DISTINCT user_email) AS unique_users,
          MIN(snapshot_date) AS earliest_date,
          MAX(snapshot_date) AS latest_date
        FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
        WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
        """

        results = self.run_query(query, "Cursor Total Cost Validation")

        if not results:
            return {"status": "FAILED", "reason": "No data returned"}

        actual = results[0]
        expected_cost = EXPECTED_VALUES["cursor"]["total_cost_usd"]

        # Calculate variance
        variance_percent = abs(actual["total_cost_usd"] - expected_cost) / expected_cost * 100

        status = "PASSED" if variance_percent <= TOLERANCE["cost_percent"] else "FAILED"

        return {
            "status": status,
            "metric": "Cursor Total Cost",
            "expected": expected_cost,
            "actual": round(actual["total_cost_usd"], 2),
            "variance_percent": round(variance_percent, 2),
            "tolerance": TOLERANCE["cost_percent"],
            "details": actual
        }

    def validate_cursor_model_breakdown(self) -> List[Dict[str, Any]]:
        """Validate Cursor cost breakdown by model"""
        query = """
        SELECT
          model,
          SUM(total_cost) AS model_cost_usd,
          ROUND(SUM(total_cost), 2) AS model_cost_rounded,
          SUM(total_tokens) AS total_tokens,
          ROUND(SUM(total_tokens) / 1000000, 2) AS tokens_millions
        FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
        WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
        GROUP BY model
        ORDER BY model_cost_usd DESC
        """

        results = self.run_query(query, "Cursor Model Breakdown Validation")

        validations = []
        expected_models = EXPECTED_VALUES["cursor"]["model_breakdown"]

        for result in results:
            model = result["model"]
            actual_cost = result["model_cost_rounded"]
            actual_tokens = result["tokens_millions"]

            if model in expected_models:
                expected = expected_models[model]
                cost_variance = abs(actual_cost - expected["cost"]) / expected["cost"] * 100
                token_variance = abs(actual_tokens - expected["tokens_millions"]) / expected["tokens_millions"] * 100

                status = "PASSED" if (cost_variance <= TOLERANCE["cost_percent"] and
                                     token_variance <= TOLERANCE["tokens_percent"]) else "FAILED"

                validations.append({
                    "status": status,
                    "metric": f"Cursor Model: {model}",
                    "expected_cost": expected["cost"],
                    "actual_cost": actual_cost,
                    "cost_variance_percent": round(cost_variance, 2),
                    "expected_tokens": expected["tokens_millions"],
                    "actual_tokens": actual_tokens,
                    "token_variance_percent": round(token_variance, 2)
                })
            else:
                validations.append({
                    "status": "WARNING",
                    "metric": f"Cursor Model: {model}",
                    "reason": "Model not in expected dashboard data",
                    "actual_cost": actual_cost,
                    "actual_tokens": actual_tokens
                })

        return validations

    def validate_data_quality(self) -> Dict[str, Any]:
        """Check for data quality issues"""
        cursor_quality_query = """
        SELECT
          'Cursor Data Quality' AS table_name,
          COUNTIF(user_email IS NULL) AS null_user_emails,
          COUNTIF(model IS NULL) AS null_models,
          COUNTIF(total_tokens IS NULL OR total_tokens < 0) AS invalid_tokens,
          COUNTIF(activity_date IS NULL) AS null_dates,
          COUNTIF(activity_date > CURRENT_DATE()) AS future_dates,
          COUNT(*) AS total_records
        FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
        WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
        """

        claude_quality_query = """
        SELECT
          'Claude Data Quality' AS table_name,
          COUNTIF(user_email IS NULL) AS null_user_emails,
          COUNTIF(event_type IS NULL) AS null_event_types,
          COUNTIF(activity_date IS NULL) AS null_dates,
          COUNTIF(activity_date > CURRENT_DATE()) AS future_dates,
          COUNT(*) AS total_records
        FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
        WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
        """

        cursor_results = self.run_query(cursor_quality_query, "Cursor Data Quality Check")
        claude_results = self.run_query(claude_quality_query, "Claude Data Quality Check")

        quality_issues = []

        for result in cursor_results + claude_results:
            has_issues = any([
                result.get("null_user_emails", 0) > 0,
                result.get("null_models", 0) > 0,
                result.get("null_event_types", 0) > 0,
                result.get("invalid_tokens", 0) > 0,
                result.get("null_dates", 0) > 0,
                result.get("future_dates", 0) > 0
            ])

            quality_issues.append({
                "table": result.get("table_name", "Unknown"),
                "status": "FAILED" if has_issues else "PASSED",
                "issues": result,
                "total_records": result.get("total_records", 0)
            })

        return quality_issues

    def check_missing_partitions(self) -> Dict[str, Any]:
        """Check for missing daily partitions"""
        query = """
        WITH date_range AS (
          SELECT date
          FROM UNNEST(GENERATE_DATE_ARRAY('2025-10-03', '2025-11-03')) AS date
        ),
        cursor_dates AS (
          SELECT DISTINCT activity_date AS date
          FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
          WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
        ),
        claude_dates AS (
          SELECT DISTINCT activity_date AS date
          FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
          WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
        )
        SELECT
          dr.date,
          CASE WHEN cd.date IS NOT NULL THEN TRUE ELSE FALSE END AS has_cursor_data,
          CASE WHEN cld.date IS NOT NULL THEN TRUE ELSE FALSE END AS has_claude_data
        FROM date_range dr
        LEFT JOIN cursor_dates cd ON dr.date = cd.date
        LEFT JOIN claude_dates cld ON dr.date = cld.date
        ORDER BY dr.date
        """

        results = self.run_query(query, "Missing Partitions Check")

        missing_cursor = [r["date"] for r in results if not r["has_cursor_data"]]
        missing_claude = [r["date"] for r in results if not r["has_claude_data"]]

        status = "PASSED" if not (missing_cursor or missing_claude) else "WARNING"

        return {
            "status": status,
            "metric": "Partition Completeness",
            "missing_cursor_dates": [str(d) for d in missing_cursor],
            "missing_claude_dates": [str(d) for d in missing_claude],
            "total_days_expected": len(results),
            "cursor_days_present": len([r for r in results if r["has_cursor_data"]]),
            "claude_days_present": len([r for r in results if r["has_claude_data"]])
        }

    def generate_report(self) -> str:
        """Generate a comprehensive validation report"""
        print("\n" + "="*80)
        print("DATA VALIDATION REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Run all validations
        print("\n[1/6] Validating Cursor Total Tokens...")
        cursor_tokens = self.validate_cursor_totals()
        self.validation_results.append(cursor_tokens)

        print("\n[2/6] Validating Cursor Total Cost...")
        cursor_cost = self.validate_cursor_cost()
        self.validation_results.append(cursor_cost)

        print("\n[3/6] Validating Cursor Model Breakdown...")
        cursor_models = self.validate_cursor_model_breakdown()
        self.validation_results.extend(cursor_models)

        print("\n[4/6] Checking Data Quality...")
        quality_checks = self.validate_data_quality()
        self.validation_results.extend(quality_checks)

        print("\n[5/6] Checking Missing Partitions...")
        partition_check = self.check_missing_partitions()
        self.validation_results.append(partition_check)

        # Generate summary
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)

        passed = sum(1 for r in self.validation_results if r.get("status") == "PASSED")
        failed = sum(1 for r in self.validation_results if r.get("status") == "FAILED")
        warnings = sum(1 for r in self.validation_results if r.get("status") == "WARNING")

        print(f"\nTotal Validations: {len(self.validation_results)}")
        print(f"  ✓ PASSED:  {passed}")
        print(f"  ✗ FAILED:  {failed}")
        print(f"  ⚠ WARNING: {warnings}")

        # Show critical failures
        if failed > 0:
            print("\n" + "="*80)
            print("CRITICAL FAILURES")
            print("="*80)
            for result in self.validation_results:
                if result.get("status") == "FAILED":
                    print(f"\n✗ {result.get('metric', result.get('table', 'Unknown'))}")
                    if 'reason' in result:
                        print(f"  Reason: {result['reason']}")
                    if 'expected' in result and 'actual' in result:
                        print(f"  Expected: {result['expected']}")
                        print(f"  Actual: {result['actual']}")
                        print(f"  Variance: {result.get('variance_percent', 'N/A')}%")

        # Save detailed report
        report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(os.path.dirname(__file__), report_file)

        with open(report_path, 'w') as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.validation_results),
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings
                },
                "expected_values": EXPECTED_VALUES,
                "tolerances": TOLERANCE,
                "results": self.validation_results
            }, f, indent=2, default=str)

        print(f"\n📄 Detailed report saved to: {report_path}")

        return report_path


def main():
    """Main execution function"""
    print("Starting BigQuery Data Validation...")
    print(f"Project: ai-workflows-459123")
    print(f"Date Range: 2025-10-03 to 2025-11-03")

    validator = DataValidator()
    report_path = validator.generate_report()

    print("\n" + "="*80)
    print("Validation Complete!")
    print("="*80)
    print(f"\nNext steps:")
    print(f"1. Review the detailed report: {report_path}")
    print(f"2. Investigate any FAILED validations")
    print(f"3. Check WARNING items for potential data gaps")
    print(f"4. Re-run ingestion pipelines if critical failures found")


if __name__ == "__main__":
    main()
