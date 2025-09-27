"""BigQuery client for schema management and data operations."""

import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from ..shared.config import config
from ..shared.logging_setup import get_logger
from ..shared.cloud_monitoring import get_cloud_monitoring


class BigQuerySchemaManager:
    """Manages BigQuery schema creation and operations."""

    def __init__(self):
        self.logger = get_logger("bigquery_client")
        self.client = bigquery.Client(project=config.project_id)
        self.dataset_id = config.dataset

    def create_dataset(self, location: str = "US") -> bool:
        """
        Create BigQuery dataset if it doesn't exist.

        Args:
            location: BigQuery location (default: US)

        Returns:
            True if dataset was created or already exists
        """
        dataset_ref = self.client.dataset(self.dataset_id)

        try:
            self.client.get_dataset(dataset_ref)
            self.logger.info(f"Dataset {self.dataset_id} already exists")
            return True
        except NotFound:
            self.logger.info(f"Creating dataset {self.dataset_id}")

        # Create the dataset
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        dataset.description = "AI Usage Analytics Dashboard - Multi-platform usage and cost data"

        try:
            dataset = self.client.create_dataset(dataset, timeout=30)
            self.logger.info(f"Created dataset {self.dataset_id} in {location}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create dataset {self.dataset_id}: {e}")
            return False

    def execute_sql_file(self, sql_file_path: str) -> bool:
        """
        Execute SQL commands from a file.

        Args:
            sql_file_path: Path to SQL file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(sql_file_path, 'r') as file:
                sql_content = file.read()

            # Replace dataset placeholder with actual dataset
            sql_content = sql_content.replace('ai_usage.', f'{config.project_id}.{self.dataset_id}.')

            # Split on semicolons and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

            for statement in statements:
                if statement:
                    self.logger.info(f"Executing SQL: {statement[:100]}...")
                    query_job = self.client.query(statement)
                    query_job.result()  # Wait for completion

            self.logger.info(f"Successfully executed SQL file: {sql_file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to execute SQL file {sql_file_path}: {e}")
            return False

    def create_all_tables(self) -> bool:
        """
        Create all tables from SQL scripts.

        Returns:
            True if all tables created successfully
        """
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent
        sql_tables_dir = project_root / "sql" / "tables"

        # List of table creation files in order
        table_files = [
            "01_raw_cursor_usage.sql",
            "02_raw_anthropic_usage.sql",
            "03_raw_anthropic_cost.sql",
            "04_dim_users.sql",
            "05_dim_api_keys.sql",
            "06_fct_usage_daily.sql",
            "07_fct_cost_daily.sql"
        ]

        success = True

        # First ensure dataset exists
        if not self.create_dataset():
            return False

        # Execute each table creation script
        for table_file in table_files:
            file_path = sql_tables_dir / table_file
            if file_path.exists():
                if not self.execute_sql_file(str(file_path)):
                    success = False
            else:
                self.logger.error(f"SQL file not found: {file_path}")
                success = False

        return success

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the dataset.

        Args:
            table_name: Name of the table

        Returns:
            True if table exists, False otherwise
        """
        try:
            table_ref = self.client.dataset(self.dataset_id).table(table_name)
            self.client.get_table(table_ref)
            return True
        except NotFound:
            return False

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a table.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table information or None if not found
        """
        try:
            table_ref = self.client.dataset(self.dataset_id).table(table_name)
            table = self.client.get_table(table_ref)

            return {
                "table_id": table.table_id,
                "created": table.created,
                "modified": table.modified,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "description": table.description,
                "schema": [{"name": field.name, "type": field.field_type, "mode": field.mode}
                          for field in table.schema]
            }
        except NotFound:
            return None

    def list_tables(self) -> List[str]:
        """
        List all tables in the dataset.

        Returns:
            List of table names
        """
        try:
            tables = self.client.list_tables(self.dataset_id)
            return [table.table_id for table in tables]
        except Exception as e:
            self.logger.error(f"Failed to list tables: {e}")
            return []

    def health_check(self) -> bool:
        """
        Perform health check on BigQuery connection.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Try to access the dataset
            dataset_ref = self.client.dataset(self.dataset_id)
            self.client.get_dataset(dataset_ref)

            # Try a simple query
            query = f"SELECT 1 as health_check"
            query_job = self.client.query(query)
            result = list(query_job.result())

            self.logger.info("BigQuery health check passed")
            return True

        except Exception as e:
            self.logger.error(f"BigQuery health check failed: {e}")
            return False

    def insert_usage_data(self, usage_records: List, batch_size: int = 1000) -> bool:
        """
        Insert usage data records to BigQuery.

        Args:
            usage_records: List of usage fact records
            batch_size: Number of records per batch

        Returns:
            True if insertion successful, False otherwise
        """
        if not usage_records:
            self.logger.info("No usage records to insert")
            return True

        self.logger.info(f"Preparing to insert {len(usage_records)} usage records")
        try:
            table_id = "fct_usage_daily"
            table_ref = self.client.dataset(self.dataset_id).table(table_id)
            table = self.client.get_table(table_ref)

            # Convert records to BigQuery format
            rows_to_insert = []
            for record in usage_records:
                if hasattr(record, '__dict__'):
                    # Handle dataclass or object with attributes
                    row = {
                        'usage_date': record.usage_date.isoformat() if hasattr(record.usage_date, 'isoformat') else str(record.usage_date),
                        'platform': getattr(record, 'platform', ''),
                        'user_email': getattr(record, 'user_email', ''),
                        'user_id': getattr(record, 'user_id', None),
                        'api_key_id': getattr(record, 'api_key_id', None),
                        'model': getattr(record, 'model', None),
                        'workspace_id': getattr(record, 'workspace_id', None),
                        'input_tokens': getattr(record, 'input_tokens', 0),
                        'output_tokens': getattr(record, 'output_tokens', 0),
                        'cached_input_tokens': getattr(record, 'cached_input_tokens', 0),
                        'cache_read_tokens': getattr(record, 'cache_read_tokens', 0),
                        'sessions': getattr(record, 'sessions', 0),
                        'lines_of_code_added': getattr(record, 'lines_of_code_added', 0),
                        'lines_of_code_accepted': getattr(record, 'lines_of_code_accepted', 0),
                        'acceptance_rate': getattr(record, 'acceptance_rate', None),
                        'total_accepts': getattr(record, 'total_accepts', 0),
                        'subscription_requests': getattr(record, 'subscription_requests', 0),
                        'usage_based_requests': getattr(record, 'usage_based_requests', 0),
                        'ingest_date': record.ingest_date.isoformat() if hasattr(record, 'ingest_date') and hasattr(record.ingest_date, 'isoformat') else str(record.ingest_date) if hasattr(record, 'ingest_date') else None,
                        'request_id': getattr(record, 'request_id', None)
                    }
                else:
                    # Handle dictionary format
                    row = record

                rows_to_insert.append(row)

            # Insert in batches with timing
            total_insert_start = time.time()
            for i in range(0, len(rows_to_insert), batch_size):
                batch = rows_to_insert[i:i + batch_size]

                batch_start_time = time.time()
                errors = self.client.insert_rows_json(table, batch)
                batch_time = time.time() - batch_start_time

                if errors:
                    self.logger.error(f"Failed to insert usage data batch: {errors}")
                    return False

                self.logger.debug(f"Inserted batch of {len(batch)} records in {batch_time:.2f}s")

            # Record total BigQuery load time
            total_load_time = time.time() - total_insert_start
            try:
                monitoring_client = get_cloud_monitoring()
                monitoring_client.record_bigquery_load_time("fct_usage_daily", total_load_time, len(usage_records))
            except Exception as e:
                self.logger.warning(f"Failed to record BigQuery load time: {e}")

            self.logger.info(f"Successfully inserted {len(usage_records)} usage records")
            return True

        except Exception as e:
            self.logger.error(f"Failed to insert usage data: {e}")
            return False

    def insert_cost_data(self, cost_records: List, batch_size: int = 1000) -> bool:
        """
        Insert cost data records to BigQuery.

        Args:
            cost_records: List of cost fact records
            batch_size: Number of records per batch

        Returns:
            True if insertion successful, False otherwise
        """
        if not cost_records:
            self.logger.info("No cost records to insert")
            return True

        self.logger.info(f"Preparing to insert {len(cost_records)} cost records")
        try:
            table_id = "fct_cost_daily"
            table_ref = self.client.dataset(self.dataset_id).table(table_id)
            table = self.client.get_table(table_ref)

            # Convert records to BigQuery format
            rows_to_insert = []
            for record in cost_records:
                if hasattr(record, '__dict__'):
                    # Handle dataclass or object with attributes
                    row = {
                        'cost_date': record.cost_date.isoformat() if hasattr(record.cost_date, 'isoformat') else str(record.cost_date),
                        'platform': getattr(record, 'platform', ''),
                        'user_email': getattr(record, 'user_email', ''),
                        'user_id': getattr(record, 'user_id', None),
                        'api_key_id': getattr(record, 'api_key_id', None),
                        'model': getattr(record, 'model', None),
                        'workspace_id': getattr(record, 'workspace_id', None),
                        'cost_usd': getattr(record, 'cost_usd', 0.0),
                        'cost_type': getattr(record, 'cost_type', ''),
                        'cost_hour': getattr(record, 'cost_hour', None),
                        'ingest_date': record.ingest_date.isoformat() if hasattr(record, 'ingest_date') and hasattr(record.ingest_date, 'isoformat') else str(record.ingest_date) if hasattr(record, 'ingest_date') else None,
                        'request_id': getattr(record, 'request_id', None)
                    }
                else:
                    # Handle dictionary format
                    row = record

                rows_to_insert.append(row)

            # Insert in batches with timing
            total_insert_start = time.time()
            for i in range(0, len(rows_to_insert), batch_size):
                batch = rows_to_insert[i:i + batch_size]

                batch_start_time = time.time()
                errors = self.client.insert_rows_json(table, batch)
                batch_time = time.time() - batch_start_time

                if errors:
                    self.logger.error(f"Failed to insert cost data batch: {errors}")
                    return False

                self.logger.debug(f"Inserted batch of {len(batch)} records in {batch_time:.2f}s")

            # Record total BigQuery load time
            total_load_time = time.time() - total_insert_start
            try:
                monitoring_client = get_cloud_monitoring()
                monitoring_client.record_bigquery_load_time("fct_cost_daily", total_load_time, len(cost_records))
            except Exception as e:
                self.logger.warning(f"Failed to record BigQuery load time: {e}")

            self.logger.info(f"Successfully inserted {len(cost_records)} cost records")
            return True

        except Exception as e:
            self.logger.error(f"Failed to insert cost data: {e}")
            return False