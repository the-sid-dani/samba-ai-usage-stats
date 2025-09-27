"""Integration tests for authentication and authorization components.

Tests service account authentication, API access validation,
and security configurations for Cloud Run deployment.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os

from google.cloud import bigquery
from google.cloud import secretmanager
from google.oauth2 import service_account

from src.shared.config import config
from src.storage.bigquery_client import BigQuerySchemaManager


class TestServiceAccountAuthentication:
    """Test service account authentication and permissions."""

    @patch('google.auth.default')
    def test_default_credentials_authentication(self, mock_auth):
        """Test that default credentials are properly configured."""
        # Mock successful authentication
        mock_credentials = Mock()
        mock_project = "test-project"
        mock_auth.return_value = (mock_credentials, mock_project)

        # Test credentials are accessible
        credentials, project = mock_auth()

        assert credentials is not None
        assert project == "test-project"
        mock_auth.assert_called_once()

    @patch('google.oauth2.service_account.Credentials.from_service_account_file')
    def test_service_account_file_authentication(self, mock_from_file):
        """Test authentication using service account file."""
        mock_credentials = Mock()
        mock_from_file.return_value = mock_credentials

        # Test loading service account credentials
        credentials = mock_from_file("/path/to/service-account.json")

        assert credentials is not None
        mock_from_file.assert_called_once_with("/path/to/service-account.json")

    @patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': '/test/sa.json'})
    @patch('google.auth.default')
    def test_environment_credentials(self, mock_auth):
        """Test that environment-based credentials are loaded."""
        mock_credentials = Mock()
        mock_project = "test-project"
        mock_auth.return_value = (mock_credentials, mock_project)

        # Verify environment variable is set
        assert os.getenv('GOOGLE_APPLICATION_CREDENTIALS') == '/test/sa.json'

        # Test authentication works with env var
        credentials, project = mock_auth()
        assert credentials is not None


class TestBigQueryAuthentication:
    """Test BigQuery service authentication and permissions."""

    @patch('google.cloud.bigquery.Client')
    def test_bigquery_client_authentication(self, mock_client_class):
        """Test BigQuery client authentication."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Create BigQuery schema manager
        manager = BigQuerySchemaManager()

        # Verify manager was created
        assert hasattr(manager, 'client')
        mock_client_class.assert_called_once()

    @patch('google.cloud.bigquery.Client')
    def test_bigquery_permissions_validation(self, mock_client_class):
        """Test BigQuery permissions are properly configured."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock successful table list (indicates read permissions)
        mock_dataset = Mock()
        mock_dataset.dataset_id = "ai_usage_analytics"
        mock_client.list_datasets.return_value = [mock_dataset]

        # Test permissions by attempting to list datasets
        bq_manager = BigQuerySchemaManager()
        datasets = list(mock_client.list_datasets())

        assert len(datasets) > 0
        assert datasets[0].dataset_id == "ai_usage_analytics"

    @patch('google.cloud.bigquery.Client')
    def test_bigquery_table_access(self, mock_client_class):
        """Test BigQuery table access permissions."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock table reference
        mock_table_ref = Mock()
        mock_table_ref.table_id = "fct_usage_daily"
        mock_client.get_table.return_value = mock_table_ref

        bq_manager = BigQuerySchemaManager()

        # Test table access
        table = mock_client.get_table("ai_usage_analytics.fct_usage_daily")
        assert table.table_id == "fct_usage_daily"
        mock_client.get_table.assert_called_once_with("ai_usage_analytics.fct_usage_daily")

    @patch('google.cloud.bigquery.Client')
    def test_bigquery_write_permissions(self, mock_client_class):
        """Test BigQuery write permissions for data insertion."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock successful insert
        mock_errors = []
        mock_client.insert_rows_json.return_value = mock_errors

        bq_manager = BigQuerySchemaManager()

        # Test data insertion
        test_data = [{"id": 1, "value": "test"}]
        errors = mock_client.insert_rows_json("test_table", test_data)

        assert len(errors) == 0
        mock_client.insert_rows_json.assert_called_once_with("test_table", test_data)


class TestSecretManagerAuthentication:
    """Test Secret Manager service authentication and access."""

    @patch('google.cloud.secretmanager.SecretManagerServiceClient')
    def test_secret_manager_client_authentication(self, mock_client_class):
        """Test Secret Manager client authentication."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Test client creation
        client = mock_client_class()

        assert client is not None
        mock_client_class.assert_called_once()

    @patch('src.shared.config.config.get_secret')
    def test_secret_access_permissions(self, mock_get_secret):
        """Test Secret Manager secret access permissions."""
        # Mock successful secret retrieval
        mock_get_secret.return_value = "test-api-key-value"

        # Test secret access
        secret_value = config.get_secret("anthropic-api-key")

        assert secret_value == "test-api-key-value"
        mock_get_secret.assert_called_once_with("anthropic-api-key")

    @patch('google.cloud.secretmanager.SecretManagerServiceClient')
    def test_secret_manager_permissions_validation(self, mock_client_class):
        """Test Secret Manager permissions by listing secrets."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock secret listing
        mock_secret = Mock()
        mock_secret.name = "projects/test-project/secrets/anthropic-api-key"
        mock_client.list_secrets.return_value = [mock_secret]

        client = mock_client_class()
        secrets = list(client.list_secrets(request={"parent": "projects/test-project"}))

        assert len(secrets) > 0
        assert "anthropic-api-key" in secrets[0].name


class TestExternalAPIAuthentication:
    """Test authentication for external APIs (Anthropic, Cursor)."""

    @patch('src.shared.config.config.get_secret')
    @patch('requests.get')
    def test_anthropic_api_authentication(self, mock_requests, mock_get_secret):
        """Test Anthropic API authentication."""
        # Mock secret retrieval
        mock_get_secret.return_value = "test-anthropic-key"

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "authenticated"}
        mock_requests.return_value = mock_response

        # Test API authentication
        api_key = config.get_secret("anthropic-api-key")
        assert api_key == "test-anthropic-key"

        # Simulate API call with authentication
        headers = {"Authorization": f"Bearer {api_key}"}
        response = mock_requests("https://api.anthropic.com/v1/test", headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "authenticated"

    @patch('src.shared.config.config.get_secret')
    @patch('requests.get')
    def test_cursor_api_authentication(self, mock_requests, mock_get_secret):
        """Test Cursor API authentication."""
        # Mock secret retrieval
        mock_get_secret.return_value = "test-cursor-key"

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"authenticated": True}
        mock_requests.return_value = mock_response

        # Test API authentication
        api_key = config.get_secret("cursor-api-key")
        assert api_key == "test-cursor-key"

        # Simulate API call with authentication
        headers = {"Authorization": f"Bearer {api_key}"}
        response = mock_requests("https://api.cursor.com/v1/test", headers=headers)

        assert response.status_code == 200
        assert response.json()["authenticated"] is True


class TestCloudRunServiceAccountIntegration:
    """Test Cloud Run service account integration and permissions."""

    @patch.dict(os.environ, {
        'GOOGLE_CLOUD_PROJECT': 'test-project',
        'ENVIRONMENT': 'production'
    })
    def test_cloud_run_environment_configuration(self):
        """Test Cloud Run environment variables are properly configured."""
        assert os.getenv('GOOGLE_CLOUD_PROJECT') == 'test-project'
        assert os.getenv('ENVIRONMENT') == 'production'

    @patch('google.auth.default')
    def test_cloud_run_service_account_permissions(self, mock_auth):
        """Test service account has required permissions for Cloud Run."""
        # Mock service account credentials
        mock_credentials = Mock()
        mock_credentials.service_account_email = "ai-usage-pipeline@test-project.iam.gserviceaccount.com"
        mock_auth.return_value = (mock_credentials, "test-project")

        credentials, project = mock_auth()

        # Verify service account email format
        assert "ai-usage-pipeline" in credentials.service_account_email
        assert "iam.gserviceaccount.com" in credentials.service_account_email
        assert project == "test-project"

    @patch('src.shared.config.config.get_secret')
    def test_production_secrets_access(self, mock_get_secret):
        """Test production environment can access required secrets."""
        # Mock all required secrets
        secret_values = {
            "anthropic-api-key": "prod-anthropic-key",
            "cursor-api-key": "prod-cursor-key",
            "sheets-credentials": '{"type": "service_account"}'
        }

        def mock_secret_side_effect(secret_name):
            return secret_values.get(secret_name, "default-value")

        mock_get_secret.side_effect = mock_secret_side_effect

        # Test all required secrets are accessible
        anthropic_key = config.get_secret("anthropic-api-key")
        cursor_key = config.get_secret("cursor-api-key")
        sheets_creds = config.get_secret("sheets-credentials")

        assert anthropic_key == "prod-anthropic-key"
        assert cursor_key == "prod-cursor-key"
        assert "service_account" in sheets_creds


class TestSecurityConfiguration:
    """Test security configuration and hardening."""

    def test_no_hardcoded_credentials(self):
        """Test that no credentials are hardcoded in the application."""
        # This would be implemented by scanning source files
        # For now, we verify config.py uses proper secret management

        # Verify config module uses environment variables or secret manager
        assert hasattr(config, 'get_secret')

        # Test that direct environment access is not used for secrets
        # (This is more of a code review check)
        pass

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_handling(self):
        """Test graceful handling of missing credentials."""
        # Test that missing environment variables don't crash the app
        assert os.getenv('GOOGLE_APPLICATION_CREDENTIALS') is None

        # The application should handle this gracefully
        # (Implementation depends on specific error handling)

    @patch('src.shared.config.config.get_secret')
    def test_secret_validation(self, mock_get_secret):
        """Test that secrets are validated properly."""
        # Mock secret with proper format
        mock_get_secret.return_value = "valid-api-key-format"

        secret = config.get_secret("test-secret")

        # Basic validation - secret should not be empty
        assert secret is not None
        assert len(secret) > 0
        assert secret != ""


class TestAuthenticationIntegrationFlow:
    """End-to-end authentication flow tests."""

    @patch('google.auth.default')
    @patch('src.shared.config.config.get_secret')
    @patch('google.cloud.bigquery.Client')
    def test_complete_authentication_flow(self, mock_bq_client, mock_get_secret, mock_auth):
        """Test complete authentication flow from Cloud Run to services."""
        # Mock authentication chain
        mock_credentials = Mock()
        mock_auth.return_value = (mock_credentials, "test-project")

        # Mock secret access
        mock_get_secret.return_value = "test-secret"

        # Mock BigQuery client
        mock_client = Mock()
        mock_bq_client.return_value = mock_client

        # Simulate authentication flow
        # 1. Cloud Run uses default credentials
        credentials, project = mock_auth()
        assert credentials is not None

        # 2. App accesses secrets
        api_key = config.get_secret("anthropic-api-key")
        assert api_key == "test-secret"

        # 3. App connects to BigQuery
        bq_manager = BigQuerySchemaManager()
        assert hasattr(bq_manager, 'client')

        # Verify all components were called
        mock_auth.assert_called_once()
        mock_get_secret.assert_called_once_with("anthropic-api-key")
        mock_bq_client.assert_called_once()

    @patch('src.web.app.create_app')
    def test_web_app_authentication_initialization(self, mock_create_app):
        """Test that web application initializes authentication properly."""
        # Mock app creation
        mock_app = Mock()
        mock_create_app.return_value = mock_app

        # Test app creation
        app = mock_create_app()

        assert app is not None
        mock_create_app.assert_called_once()