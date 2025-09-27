#!/usr/bin/env python3
"""Setup BigQuery schema for AI Usage Analytics Dashboard."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.bigquery_client import BigQuerySchemaManager
from shared.logging_setup import setup_logging


def main():
    """Setup BigQuery schema."""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting BigQuery schema setup")

    # Create schema manager
    schema_manager = BigQuerySchemaManager()

    # Perform health check first
    if not schema_manager.health_check():
        logger.error("BigQuery health check failed. Please check your credentials and project configuration.")
        sys.exit(1)

    # Create all tables
    logger.info("Creating BigQuery tables...")
    if schema_manager.create_all_tables():
        logger.info("✓ All BigQuery tables created successfully")

        # List created tables
        tables = schema_manager.list_tables()
        logger.info(f"Created tables: {', '.join(tables)}")

        # Show table info for verification
        for table in tables:
            info = schema_manager.get_table_info(table)
            if info:
                logger.info(f"  {table}: {info['num_rows']} rows, created {info['created']}")

        logger.info("BigQuery schema setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("✗ Failed to create some BigQuery tables")
        sys.exit(1)


if __name__ == "__main__":
    main()