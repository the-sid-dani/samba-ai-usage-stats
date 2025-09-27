#!/usr/bin/env python3
"""
Comprehensive End-to-End Production Validation Script

Validates the complete AI Usage Analytics system with real production data.
Tests all components from API ingestion through BigQuery storage to dashboard readiness.

Usage:
    python scripts/validate_production_deployment.py [--project-id PROJECT_ID] [--service-url SERVICE_URL]
"""

import sys
import os
import json
import time
import argparse
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.logging_setup import setup_logging, get_logger
from shared.config import config
from google.cloud import bigquery
from google.cloud import secretmanager


class ProductionValidator:
    """Comprehensive production validation for AI Usage Analytics."""

    def __init__(self, project_id: str, service_url: Optional[str] = None):
        """Initialize validator with project configuration."""
        self.project_id = project_id
        self.service_url = service_url
        self.logger = get_logger("production_validator")
        self.bq_client = bigquery.Client(project=project_id)
        self.secret_client = secretmanager.SecretManagerServiceClient()

        # Test results storage
        self.test_results = []
        self.start_time = time.time()

    def log_test_result(self, test_name: str, success: bool, details: str = "",
                       metrics: Optional[Dict[str, Any]] = None):
        """Log test result for summary reporting."""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "metrics": metrics or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        self.logger.info(f"{status} {test_name}: {details}")

    def validate_secret_manager_setup(self) -> bool:
        """Validate that all required secrets are configured in Secret Manager."""
        self.logger.info("=" * 60)
        self.logger.info("VALIDATING SECRET MANAGER CONFIGURATION")
        self.logger.info("=" * 60)

        required_secrets = [
            "cursor-api-key",
            "anthropic-api-key",
            "sheets-service-account-key"
        ]

        all_secrets_valid = True

        for secret_name in required_secrets:
            try:
                secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                response = self.secret_client.access_secret_version(request={"name": secret_path})
                secret_value = response.payload.data.decode("UTF-8")

                if secret_value and len(secret_value) > 10:
                    self.log_test_result(
                        f"Secret Manager - {secret_name}",
                        True,
                        f"Secret configured (length: {len(secret_value)} chars)"
                    )
                else:
                    self.log_test_result(
                        f"Secret Manager - {secret_name}",
                        False,
                        "Secret value too short or empty"
                    )
                    all_secrets_valid = False

            except Exception as e:
                self.log_test_result(
                    f"Secret Manager - {secret_name}",
                    False,
                    f"Failed to access secret: {str(e)}"
                )
                all_secrets_valid = False

        return all_secrets_valid

    def validate_cloud_run_service(self) -> bool:
        """Validate Cloud Run service is healthy and responding."""
        self.logger.info("=" * 60)
        self.logger.info("VALIDATING CLOUD RUN SERVICE")
        self.logger.info("=" * 60)

        if not self.service_url:
            self.log_test_result(
                "Cloud Run Service",
                False,
                "Service URL not provided"
            )
            return False

        try:
            # Test health endpoint
            health_url = f"{self.service_url}/health"
            start_time = time.time()
            response = requests.get(health_url, timeout=30)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                health_data = response.json()
                self.log_test_result(
                    "Cloud Run Health Check",
                    health_data.get("status") == "healthy",
                    f"Status: {health_data.get('status', 'unknown')}",
                    {"response_time_ms": response_time}
                )

                # Test readiness
                ready_response = requests.get(f"{self.service_url}/ready", timeout=10)
                self.log_test_result(
                    "Cloud Run Readiness",
                    ready_response.status_code == 200,
                    f"HTTP {ready_response.status_code}"
                )

                # Test status endpoint
                status_response = requests.get(f"{self.service_url}/status", timeout=10)
                self.log_test_result(
                    "Cloud Run Status Endpoint",
                    status_response.status_code == 200,
                    f"HTTP {status_response.status_code}"
                )

                return health_data.get("status") == "healthy"
            else:
                self.log_test_result(
                    "Cloud Run Health Check",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                return False

        except Exception as e:
            self.log_test_result(
                "Cloud Run Service",
                False,
                f"Connection failed: {str(e)}"
            )
            return False

    def validate_bigquery_schema(self) -> bool:
        """Validate BigQuery dataset and table schema is correctly deployed."""
        self.logger.info("=" * 60)
        self.logger.info("VALIDATING BIGQUERY SCHEMA")
        self.logger.info("=" * 60)

        dataset_id = "ai_usage_analytics"

        try:
            # Check dataset exists
            dataset = self.bq_client.get_dataset(f"{self.project_id}.{dataset_id}")
            self.log_test_result(
                "BigQuery Dataset",
                True,
                f"Dataset exists: {dataset.dataset_id}"
            )

            # Expected tables and views
            expected_tables = [
                "raw_cursor_usage",
                "raw_anthropic_usage",
                "raw_anthropic_cost",
                "dim_users",
                "dim_api_keys",
                "fct_usage_daily",
                "fct_cost_daily"
            ]

            expected_views = [
                "vw_monthly_finance",
                "vw_productivity_metrics",
                "vw_cost_allocation",
                "vw_executive_summary"
            ]

            # Validate tables
            tables_valid = True
            for table_name in expected_tables:
                try:
                    table = self.bq_client.get_table(f"{self.project_id}.{dataset_id}.{table_name}")
                    self.log_test_result(
                        f"BigQuery Table - {table_name}",
                        True,
                        f"Rows: {table.num_rows}, Columns: {len(table.schema)}"
                    )
                except Exception as e:
                    self.log_test_result(
                        f"BigQuery Table - {table_name}",
                        False,
                        f"Table not found: {str(e)}"
                    )
                    tables_valid = False

            # Validate views
            views_valid = True
            for view_name in expected_views:
                try:
                    view = self.bq_client.get_table(f"{self.project_id}.{dataset_id}.{view_name}")

                    # Test view syntax with dry run
                    query = f"SELECT COUNT(*) FROM `{self.project_id}.{dataset_id}.{view_name}` LIMIT 1"
                    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
                    query_job = self.bq_client.query(query, job_config=job_config)

                    self.log_test_result(
                        f"BigQuery View - {view_name}",
                        True,
                        f"View valid, processes {query_job.total_bytes_processed} bytes"
                    )
                except Exception as e:
                    self.log_test_result(
                        f"BigQuery View - {view_name}",
                        False,
                        f"View error: {str(e)}"
                    )
                    views_valid = False

            return tables_valid and views_valid

        except Exception as e:
            self.log_test_result(
                "BigQuery Schema",
                False,
                f"Schema validation failed: {str(e)}"
            )
            return False

    def execute_end_to_end_pipeline_test(self) -> bool:
        """Execute end-to-end pipeline test with real API data."""
        self.logger.info("=" * 60)
        self.logger.info("EXECUTING END-TO-END PIPELINE TEST")
        self.logger.info("=" * 60)

        if not self.service_url:
            self.log_test_result(
                "End-to-End Pipeline Test",
                False,
                "Service URL not provided"
            )
            return False

        try:
            # Trigger pipeline execution
            pipeline_url = f"{self.service_url}/run-daily-job"
            payload = {
                "mode": "production",
                "days": 1,
                "force": True
            }

            self.logger.info("Triggering pipeline execution...")
            start_time = time.time()

            response = requests.post(
                pipeline_url,
                json=payload,
                timeout=7200  # 2 hour timeout
            )

            execution_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                # Check execution success
                success = result.get("status") == "success"
                metrics = result.get("metrics", {})

                self.log_test_result(
                    "Pipeline Execution",
                    success,
                    f"Execution ID: {result.get('execution_id', 'unknown')}",
                    {
                        "execution_time_seconds": execution_time,
                        "cursor_records": metrics.get("cursor_records", 0),
                        "anthropic_records": metrics.get("anthropic_records", 0),
                        "storage_operations": metrics.get("storage_operations", 0),
                        "errors": metrics.get("errors", 0)
                    }
                )

                # Validate expected data volumes
                cursor_records = metrics.get("cursor_records", 0)
                anthropic_records = metrics.get("anthropic_records", 0)

                self.log_test_result(
                    "Cursor Data Volume",
                    cursor_records >= 76,  # Expected 76+ users
                    f"Retrieved {cursor_records} records (expected 76+)"
                )

                # Note: Anthropic volume validation depends on recent activity
                self.log_test_result(
                    "Anthropic Data Volume",
                    anthropic_records > 0,
                    f"Retrieved {anthropic_records} records"
                )

                return success

            else:
                self.log_test_result(
                    "Pipeline Execution",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                return False

        except Exception as e:
            self.log_test_result(
                "End-to-End Pipeline Test",
                False,
                f"Pipeline execution failed: {str(e)}"
            )
            return False

    def validate_analytics_views_performance(self) -> bool:
        """Validate analytics views performance with real data."""
        self.logger.info("=" * 60)
        self.logger.info("VALIDATING ANALYTICS VIEWS PERFORMANCE")
        self.logger.info("=" * 60)

        dataset_id = "ai_usage_analytics"
        views_to_test = [
            "vw_monthly_finance",
            "vw_productivity_metrics",
            "vw_cost_allocation",
            "vw_executive_summary"
        ]

        all_views_performant = True

        for view_name in views_to_test:
            try:
                # Performance test query
                query = f"""
                SELECT COUNT(*) as record_count,
                       MIN(cost_month) as earliest_month,
                       MAX(cost_month) as latest_month
                FROM `{self.project_id}.{dataset_id}.{view_name}`
                LIMIT 100
                """

                start_time = time.time()
                query_job = self.bq_client.query(query)
                results = list(query_job.result())
                execution_time = time.time() - start_time

                # Performance target: < 5 seconds
                performance_target_met = execution_time < 5.0

                if results:
                    row = results[0]
                    record_count = row.record_count

                    self.log_test_result(
                        f"View Performance - {view_name}",
                        performance_target_met,
                        f"Query time: {execution_time:.2f}s, Records: {record_count}",
                        {
                            "execution_time_seconds": execution_time,
                            "record_count": record_count,
                            "bytes_processed": query_job.total_bytes_processed
                        }
                    )

                    # Data availability check
                    self.log_test_result(
                        f"View Data Availability - {view_name}",
                        record_count > 0,
                        f"Contains {record_count} records"
                    )
                else:
                    self.log_test_result(
                        f"View Performance - {view_name}",
                        False,
                        "No results returned"
                    )
                    all_views_performant = False

                if not performance_target_met:
                    all_views_performant = False

            except Exception as e:
                self.log_test_result(
                    f"View Performance - {view_name}",
                    False,
                    f"Query failed: {str(e)}"
                )
                all_views_performant = False

        return all_views_performant

    def validate_user_attribution(self) -> bool:
        """Validate user attribution coverage meets 90% target."""
        self.logger.info("=" * 60)
        self.logger.info("VALIDATING USER ATTRIBUTION")
        self.logger.info("=" * 60)

        try:
            # Query attribution coverage
            query = f"""
            WITH attribution_stats AS (
                SELECT
                    platform,
                    COUNT(*) as total_records,
                    COUNT(user_email) as attributed_records,
                    SAFE_DIVIDE(COUNT(user_email), COUNT(*)) as attribution_rate
                FROM `{self.project_id}.ai_usage_analytics.fct_cost_daily`
                WHERE cost_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAYS)
                GROUP BY platform
            )
            SELECT
                platform,
                total_records,
                attributed_records,
                attribution_rate,
                CASE WHEN attribution_rate >= 0.9 THEN true ELSE false END as meets_target
            FROM attribution_stats
            ORDER BY attribution_rate DESC
            """

            query_job = self.bq_client.query(query)
            results = list(query_job.result())

            overall_attribution_met = True
            total_records = 0
            total_attributed = 0

            for row in results:
                platform = row.platform
                attribution_rate = row.attribution_rate or 0
                meets_target = attribution_rate >= 0.9

                self.log_test_result(
                    f"Attribution Coverage - {platform}",
                    meets_target,
                    f"Rate: {attribution_rate:.1%} ({row.attributed_records}/{row.total_records})"
                )

                total_records += row.total_records
                total_attributed += row.attributed_records

                if not meets_target:
                    overall_attribution_met = False

            # Overall attribution rate
            overall_rate = total_attributed / total_records if total_records > 0 else 0
            overall_meets_target = overall_rate >= 0.9

            self.log_test_result(
                "Overall Attribution Coverage",
                overall_meets_target,
                f"Rate: {overall_rate:.1%} ({total_attributed}/{total_records})"
            )

            return overall_meets_target

        except Exception as e:
            self.log_test_result(
                "User Attribution Validation",
                False,
                f"Attribution check failed: {str(e)}"
            )
            return False

    def validate_cloud_scheduler(self) -> bool:
        """Validate Cloud Scheduler is configured and operational."""
        self.logger.info("=" * 60)
        self.logger.info("VALIDATING CLOUD SCHEDULER")
        self.logger.info("=" * 60)

        try:
            from google.cloud import scheduler
            client = scheduler.CloudSchedulerClient()

            # List scheduler jobs
            parent = f"projects/{self.project_id}/locations/us-central1"
            jobs = list(client.list_jobs(request={"parent": parent}))

            # Look for our daily job
            daily_job = None
            for job in jobs:
                if "daily-usage-analytics" in job.name:
                    daily_job = job
                    break

            if daily_job:
                self.log_test_result(
                    "Cloud Scheduler Job",
                    True,
                    f"Job found: {daily_job.name}, Schedule: {daily_job.schedule}"
                )

                # Validate job configuration
                http_target = daily_job.http_target
                if http_target and self.service_url and self.service_url in http_target.uri:
                    self.log_test_result(
                        "Scheduler Configuration",
                        True,
                        f"Target URL correctly configured: {http_target.uri}"
                    )
                else:
                    self.log_test_result(
                        "Scheduler Configuration",
                        False,
                        f"Target URL mismatch. Expected: {self.service_url}, Got: {http_target.uri if http_target else 'None'}"
                    )
                    return False

                return True
            else:
                self.log_test_result(
                    "Cloud Scheduler Job",
                    False,
                    "Daily analytics job not found"
                )
                return False

        except Exception as e:
            self.log_test_result(
                "Cloud Scheduler Validation",
                False,
                f"Scheduler check failed: {str(e)}"
            )
            return False

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        validation_time = time.time() - self.start_time

        report = {
            "validation_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "validation_time_seconds": validation_time,
                "timestamp": datetime.now().isoformat(),
                "project_id": self.project_id,
                "service_url": self.service_url
            },
            "test_results": self.test_results,
            "production_readiness": {
                "ready_for_production": failed_tests == 0,
                "critical_issues": [
                    result for result in self.test_results
                    if not result["success"] and any(keyword in result["test_name"].lower()
                    for keyword in ["pipeline", "health", "schema"])
                ],
                "recommendations": self._generate_recommendations()
            }
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []

        failed_tests = [result for result in self.test_results if not result["success"]]

        if not failed_tests:
            recommendations.append("✅ All validation tests passed - system is production ready")
            recommendations.append("🚀 Proceed with finance team handoff and go-live")
            return recommendations

        # Categorize failures and provide specific recommendations
        secret_failures = [r for r in failed_tests if "Secret Manager" in r["test_name"]]
        if secret_failures:
            recommendations.append("🔑 Configure missing API keys in Google Secret Manager")
            recommendations.append("📋 Verify all secret names match expected values")

        schema_failures = [r for r in failed_tests if "BigQuery" in r["test_name"]]
        if schema_failures:
            recommendations.append("🗄️  Re-run BigQuery schema deployment script")
            recommendations.append("🔍 Verify BigQuery dataset permissions")

        pipeline_failures = [r for r in failed_tests if "Pipeline" in r["test_name"]]
        if pipeline_failures:
            recommendations.append("⚙️  Check Cloud Run service configuration and permissions")
            recommendations.append("🔗 Verify API connectivity and authentication")

        performance_failures = [r for r in failed_tests if "Performance" in r["test_name"]]
        if performance_failures:
            recommendations.append("🚀 Optimize BigQuery table partitioning and clustering")
            recommendations.append("📊 Review analytics view query complexity")

        attribution_failures = [r for r in failed_tests if "Attribution" in r["test_name"]]
        if attribution_failures:
            recommendations.append("👥 Configure Google Sheets API key mapping")
            recommendations.append("📋 Verify user email attribution data completeness")

        return recommendations


def main():
    """Main validation execution function."""
    parser = argparse.ArgumentParser(description="Validate AI Usage Analytics production deployment")
    parser.add_argument("--project-id", required=True, help="GCP project ID")
    parser.add_argument("--service-url", help="Cloud Run service URL")
    parser.add_argument("--output-file", help="JSON output file for results")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(level="DEBUG" if args.verbose else "INFO")

    logger.info("🧪 AI USAGE ANALYTICS - PRODUCTION VALIDATION")
    logger.info("=" * 70)
    logger.info(f"Project ID: {args.project_id}")
    logger.info(f"Service URL: {args.service_url or 'Not provided'}")
    logger.info(f"Validation Time: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    # Initialize validator
    validator = ProductionValidator(args.project_id, args.service_url)

    try:
        # Execute validation steps
        validation_steps = [
            ("Secret Manager Setup", validator.validate_secret_manager_setup),
            ("BigQuery Schema", validator.validate_bigquery_schema),
            ("Cloud Run Service", validator.validate_cloud_run_service),
            ("Cloud Scheduler", validator.validate_cloud_scheduler),
            ("End-to-End Pipeline", validator.execute_end_to_end_pipeline_test),
            ("Analytics Views Performance", validator.validate_analytics_views_performance),
            ("User Attribution", validator.validate_user_attribution)
        ]

        overall_success = True
        for step_name, step_function in validation_steps:
            logger.info(f"\n🔍 Starting: {step_name}")
            try:
                step_success = step_function()
                if not step_success:
                    overall_success = False
            except Exception as e:
                logger.error(f"❌ {step_name} failed with exception: {e}")
                validator.log_test_result(step_name, False, f"Exception: {str(e)}")
                overall_success = False

        # Generate final report
        report = validator.generate_validation_report()

        # Output report
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"\n📄 Validation report saved to: {args.output_file}")

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("PRODUCTION VALIDATION SUMMARY")
        logger.info("=" * 70)

        summary = report["validation_summary"]
        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Passed: {summary['passed_tests']}")
        logger.info(f"Failed: {summary['failed_tests']}")
        logger.info(f"Success Rate: {summary['success_rate']:.1%}")
        logger.info(f"Validation Time: {summary['validation_time_seconds']:.1f}s")

        # Production readiness
        if report["production_readiness"]["ready_for_production"]:
            logger.info("\n🎉 PRODUCTION VALIDATION PASSED!")
            logger.info("✅ System is ready for production use")
            logger.info("🚀 Proceed with finance team handoff")
        else:
            logger.info("\n⚠️  PRODUCTION VALIDATION FAILED")
            logger.info("❌ System requires fixes before production use")

            # Show recommendations
            logger.info("\n📋 Recommendations:")
            for rec in report["production_readiness"]["recommendations"]:
                logger.info(f"  {rec}")

        return overall_success

    except Exception as e:
        logger.error(f"\n❌ Validation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation script failed: {e}")
        sys.exit(1)