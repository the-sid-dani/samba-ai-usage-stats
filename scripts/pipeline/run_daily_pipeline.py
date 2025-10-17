#!/usr/bin/env python3
"""
Standalone Daily Pipeline Execution Script
Runs the AI usage analytics pipeline locally with cron scheduling.
"""

import os
import sys
import argparse
import logging
from datetime import datetime, date, timedelta

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up environment
os.environ['GOOGLE_CLOUD_PROJECT'] = 'ai-workflows-459123'
os.environ['BIGQUERY_DATASET'] = 'ai_usage_analytics'
os.environ['ENVIRONMENT'] = 'production'

def setup_logging():
    """Configure logging for standalone execution."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pipeline_execution.log')
        ]
    )
    return logging.getLogger('daily_pipeline')

def test_components():
    """Test all pipeline components before execution."""
    logger = logging.getLogger('daily_pipeline')

    try:
        # Test imports
        from ingestion.cursor_client import CursorClient
        from ingestion.anthropic_client import AnthropicClient
        from storage.bigquery_client import BigQuerySchemaManager
        from processing.multi_platform_transformer import MultiPlatformTransformer
        from processing.attribution import UserAttributionEngine

        logger.info("✅ All imports successful")

        # Test client initialization
        cursor_client = CursorClient()
        anthropic_client = AnthropicClient()
        bq_client = BigQuerySchemaManager()

        logger.info("✅ All clients initialized")

        # Test health checks
        cursor_health = cursor_client.health_check()
        anthropic_health = anthropic_client.health_check()
        bq_health = bq_client.health_check()

        logger.info(f"Health checks - Cursor: {cursor_health}, Anthropic: {anthropic_health}, BigQuery: {bq_health}")

        if not all([cursor_health, anthropic_health, bq_health]):
            logger.error("❌ Some components failed health checks")
            return False

        logger.info("✅ All components healthy")
        return True

    except Exception as e:
        logger.error(f"❌ Component test failed: {e}")
        return False

def run_data_pipeline(days_back=1, dry_run=False):
    """Execute the daily data pipeline."""
    logger = logging.getLogger('daily_pipeline')

    try:
        from orchestration.daily_job import DailyJobOrchestrator, ExecutionMode

        # Initialize orchestrator
        orchestrator = DailyJobOrchestrator()

        # Set execution mode
        mode = ExecutionMode.DRY_RUN if dry_run else ExecutionMode.PRODUCTION

        logger.info(f"Starting pipeline execution - Mode: {mode.value}, Days: {days_back}")

        # Execute pipeline
        result = orchestrator.run_daily_pipeline(
            mode=mode,
            days_back=days_back,
            force_execution=True
        )

        # Log results
        logger.info(f"Pipeline execution completed - Success: {result.success}")
        logger.info(f"Execution ID: {result.execution_id}")
        logger.info(f"Cursor records: {result.cursor_records}")
        logger.info(f"Anthropic records: {result.anthropic_records}")
        logger.info(f"Storage operations: {result.storage_operations}")

        if result.errors:
            logger.warning(f"Errors encountered: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"  {error.component}: {error.message}")

        return result.success

    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Run AI Usage Analytics Pipeline")
    parser.add_argument("--days", type=int, default=1, help="Number of days to process")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--test-only", action="store_true", help="Test components only")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("🚀 AI Usage Analytics - Daily Pipeline Execution")
    logger.info("=" * 60)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Project: {os.environ['GOOGLE_CLOUD_PROJECT']}")
    logger.info(f"Dataset: {os.environ['BIGQUERY_DATASET']}")
    logger.info(f"Environment: {os.environ['ENVIRONMENT']}")
    logger.info("=" * 60)

    try:
        # Test components first
        logger.info("Testing pipeline components...")
        if not test_components():
            logger.error("❌ Component tests failed")
            sys.exit(1)

        if args.test_only:
            logger.info("✅ Test-only mode completed successfully")
            sys.exit(0)

        # Execute pipeline
        logger.info("Executing data pipeline...")
        success = run_data_pipeline(args.days, args.dry_run)

        if success:
            logger.info("🎉 Pipeline execution completed successfully!")
            logger.info("✅ Data ingested and stored in BigQuery")
            logger.info("✅ Analytics views ready for dashboard access")
        else:
            logger.error("❌ Pipeline execution failed")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⚠️ Pipeline execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()