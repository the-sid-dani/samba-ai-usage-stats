"""Unit tests for BigQuery client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from google.cloud.exceptions import NotFound

from src.storage.bigquery_client import BigQuerySchemaManager


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('src.storage.bigquery_client.config') as mock:
        mock.project_id = "test-project"
        mock.dataset = "test_dataset"
        yield mock


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client."""
    with patch('src.storage.bigquery_client.bigquery.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def schema_manager(mock_config, mock_bigquery_client):
    """Create BigQuerySchemaManager with mocked dependencies."""
    return BigQuerySchemaManager()


class TestBigQuerySchemaManager:
    """Test cases for BigQuerySchemaManager."""

    def test_init(self, mock_config, mock_bigquery_client, schema_manager):
        """Test initialization."""
        assert schema_manager.dataset_id == "test_dataset"
        assert schema_manager.client == mock_bigquery_client

    def test_create_dataset_already_exists(self, schema_manager, mock_bigquery_client):
        """Test dataset creation when dataset already exists."""
        # Mock dataset already exists
        mock_dataset = Mock()
        mock_bigquery_client.get_dataset.return_value = mock_dataset

        result = schema_manager.create_dataset()

        assert result is True
        mock_bigquery_client.get_dataset.assert_called_once()

    def test_create_dataset_new(self, schema_manager, mock_bigquery_client):
        """Test creating new dataset."""
        # Mock dataset doesn't exist
        mock_bigquery_client.get_dataset.side_effect = NotFound("Dataset not found")

        # Mock successful creation
        mock_created_dataset = Mock()
        mock_bigquery_client.create_dataset.return_value = mock_created_dataset

        result = schema_manager.create_dataset("US")

        assert result is True
        mock_bigquery_client.create_dataset.assert_called_once()

    def test_create_dataset_failure(self, schema_manager, mock_bigquery_client):
        """Test dataset creation failure."""
        # Mock dataset doesn't exist
        mock_bigquery_client.get_dataset.side_effect = NotFound("Dataset not found")

        # Mock creation failure
        mock_bigquery_client.create_dataset.side_effect = Exception("Permission denied")

        result = schema_manager.create_dataset()

        assert result is False

    def test_execute_sql_file_success(self, schema_manager, mock_bigquery_client, tmp_path):
        """Test successful SQL file execution."""
        # Create temporary SQL file
        sql_file = tmp_path / "test.sql"
        sql_content = """
        CREATE TABLE ai_usage.test_table (
            id STRING,
            name STRING
        );
        CREATE TABLE ai_usage.another_table (
            id INT64
        );
        """
        sql_file.write_text(sql_content)

        # Mock query execution
        mock_job = Mock()
        mock_bigquery_client.query.return_value = mock_job

        result = schema_manager.execute_sql_file(str(sql_file))

        assert result is True
        assert mock_bigquery_client.query.call_count == 2  # Two CREATE statements

    def test_execute_sql_file_not_found(self, schema_manager):
        """Test SQL file execution with non-existent file."""
        result = schema_manager.execute_sql_file("/non/existent/file.sql")
        assert result is False

    def test_table_exists_true(self, schema_manager, mock_bigquery_client):
        """Test table exists check when table exists."""
        mock_table = Mock()
        mock_bigquery_client.get_table.return_value = mock_table

        result = schema_manager.table_exists("test_table")

        assert result is True

    def test_table_exists_false(self, schema_manager, mock_bigquery_client):
        """Test table exists check when table doesn't exist."""
        mock_bigquery_client.get_table.side_effect = NotFound("Table not found")

        result = schema_manager.table_exists("test_table")

        assert result is False

    def test_get_table_info_success(self, schema_manager, mock_bigquery_client):
        """Test getting table information."""
        mock_table = Mock()
        mock_table.table_id = "test_table"
        mock_table.created = "2022-01-01"
        mock_table.modified = "2022-01-02"
        mock_table.num_rows = 100
        mock_table.num_bytes = 1024
        mock_table.description = "Test table"

        # Mock schema
        mock_field = Mock()
        mock_field.name = "id"
        mock_field.field_type = "STRING"
        mock_field.mode = "REQUIRED"
        mock_table.schema = [mock_field]

        mock_bigquery_client.get_table.return_value = mock_table

        result = schema_manager.get_table_info("test_table")

        assert result is not None
        assert result["table_id"] == "test_table"
        assert result["num_rows"] == 100
        assert len(result["schema"]) == 1

    def test_get_table_info_not_found(self, schema_manager, mock_bigquery_client):
        """Test getting table info for non-existent table."""
        mock_bigquery_client.get_table.side_effect = NotFound("Table not found")

        result = schema_manager.get_table_info("test_table")

        assert result is None

    def test_list_tables_success(self, schema_manager, mock_bigquery_client):
        """Test listing tables."""
        mock_table1 = Mock()
        mock_table1.table_id = "table1"
        mock_table2 = Mock()
        mock_table2.table_id = "table2"

        mock_bigquery_client.list_tables.return_value = [mock_table1, mock_table2]

        result = schema_manager.list_tables()

        assert result == ["table1", "table2"]

    def test_list_tables_failure(self, schema_manager, mock_bigquery_client):
        """Test listing tables failure."""
        mock_bigquery_client.list_tables.side_effect = Exception("Access denied")

        result = schema_manager.list_tables()

        assert result == []

    def test_health_check_success(self, schema_manager, mock_bigquery_client):
        """Test successful health check."""
        mock_dataset = Mock()
        mock_bigquery_client.get_dataset.return_value = mock_dataset

        mock_job = Mock()
        mock_job.result.return_value = [{"health_check": 1}]
        mock_bigquery_client.query.return_value = mock_job

        result = schema_manager.health_check()

        assert result is True

    def test_health_check_failure(self, schema_manager, mock_bigquery_client):
        """Test health check failure."""
        mock_bigquery_client.get_dataset.side_effect = Exception("Connection failed")

        result = schema_manager.health_check()

        assert result is False

    @patch('src.storage.bigquery_client.Path')
    def test_create_all_tables_success(self, mock_path, schema_manager, mock_bigquery_client):
        """Test creating all tables successfully."""
        # Mock file system
        mock_sql_dir = Mock()
        mock_path.return_value.parent.parent.parent = Mock()
        mock_path.return_value.parent.parent.parent.__truediv__ = Mock(return_value=mock_sql_dir)
        mock_sql_dir.__truediv__ = Mock(return_value=mock_sql_dir)

        # Mock file existence and execution
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_sql_dir.__truediv__.return_value = mock_file

        # Mock dataset creation and SQL execution
        mock_dataset = Mock()
        mock_bigquery_client.get_dataset.return_value = mock_dataset

        # Mock successful SQL execution
        with patch.object(schema_manager, 'execute_sql_file', return_value=True):
            result = schema_manager.create_all_tables()

        assert result is True

    @patch('src.storage.bigquery_client.Path')
    def test_create_all_tables_missing_file(self, mock_path, schema_manager, mock_bigquery_client):
        """Test creating tables with missing SQL file."""
        # Mock file system with missing file
        mock_sql_dir = Mock()
        mock_path.return_value.parent.parent.parent = Mock()
        mock_path.return_value.parent.parent.parent.__truediv__ = Mock(return_value=mock_sql_dir)
        mock_sql_dir.__truediv__ = Mock(return_value=mock_sql_dir)

        mock_file = Mock()
        mock_file.exists.return_value = False  # File doesn't exist
        mock_sql_dir.__truediv__.return_value = mock_file

        # Mock dataset creation
        mock_dataset = Mock()
        mock_bigquery_client.get_dataset.return_value = mock_dataset

        result = schema_manager.create_all_tables()

        assert result is False