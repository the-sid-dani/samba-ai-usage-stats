"""Configuration management for AI Usage Analytics Dashboard."""

import os
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from google.cloud import secretmanager
from google.api_core.exceptions import GoogleAPIError


class SecurityError(Exception):
    """Security-related configuration error."""
    pass


class Config:
    """Configuration management with Google Secret Manager integration."""

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "ai-workflows-459123")
        self.dataset = os.getenv("BIGQUERY_DATASET", "ai_usage_dev")
        self.env = os.getenv("ENV", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.sheets_id = os.getenv("GOOGLE_SHEETS_ID")

        # Secret names (production uses Secret Manager exclusively)
        self.anthropic_secret = "anthropic-admin-api-key"
        self.cursor_secret = "cursor-api-key"
        self.sheets_secret = "google-sheets-service-key"

        self._secret_client = None
        self._secret_cache = {}  # Cache secrets for performance
        self._cache_ttl = 300    # 5-minute cache TTL

        # Initialize audit logger
        self.audit_logger = logging.getLogger("security_audit")
        self.audit_logger.setLevel(logging.INFO)

    @property
    def secret_client(self):
        """Lazy initialization of Secret Manager client."""
        if self._secret_client is None:
            self._secret_client = secretmanager.SecretManagerServiceClient()
        return self._secret_client

    def get_secret(self, secret_name: str, version: str = "latest",
                  request_id: str = None) -> Optional[str]:
        """
        Retrieve secret from Google Secret Manager with comprehensive audit logging.

        Args:
            secret_name: Name of the secret to retrieve
            version: Secret version (default: "latest")
            request_id: Request ID for audit correlation

        Returns:
            Secret value or None if not found/accessible
        """
        access_start_time = time.time()
        cache_key = f"{secret_name}:{version}"

        # Check cache first (with TTL)
        if cache_key in self._secret_cache:
            cached_entry = self._secret_cache[cache_key]
            if time.time() - cached_entry["timestamp"] < self._cache_ttl:
                self._log_secret_access("cache_hit", secret_name, version, request_id,
                                      access_start_time, "success")
                return cached_entry["value"]

        try:
            secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

            # Access secret with audit logging
            response = self.secret_client.access_secret_version(request={"name": secret_path})
            secret_value = response.payload.data.decode("UTF-8")

            # Cache the secret
            self._secret_cache[cache_key] = {
                "value": secret_value,
                "timestamp": time.time()
            }

            # Log successful access
            self._log_secret_access("secret_access", secret_name, version, request_id,
                                  access_start_time, "success")

            return secret_value

        except GoogleAPIError as e:
            # Log failed access with details
            self._log_secret_access("secret_access", secret_name, version, request_id,
                                  access_start_time, "failed", str(e))

            if self.env == "production":
                # In production, never fall back to environment variables
                raise SecurityError(f"Failed to access secret {secret_name}: {e}")
            else:
                # Development fallback (with warning)
                self.audit_logger.warning("DEVELOPMENT: Using environment fallback for secret",
                                        extra={
                                            "secret_name": secret_name,
                                            "fallback_reason": str(e),
                                            "security_warning": "Production will require Secret Manager"
                                        })
                return None

        except Exception as e:
            self._log_secret_access("secret_access", secret_name, version, request_id,
                                  access_start_time, "error", str(e))
            raise SecurityError(f"Unexpected error accessing secret {secret_name}: {e}")

    def _log_secret_access(self, event_type: str, secret_name: str, version: str,
                          request_id: str, start_time: float, result: str,
                          error_message: str = None) -> None:
        """Log secret access events for security auditing."""
        access_duration_ms = (time.time() - start_time) * 1000

        audit_entry = {
            "timestamp": datetime.now().isoformat() + "Z",
            "event_type": event_type,
            "resource": f"projects/{self.project_id}/secrets/{secret_name}",
            "resource_name": secret_name,
            "version": version,
            "result": result,
            "access_duration_ms": access_duration_ms,
            "service_name": "ai-usage-analytics",
            "environment": self.env,
            "request_id": request_id,
            "user_agent": "config-service/1.0"
        }

        if error_message:
            audit_entry["error_message"] = error_message

        # Log security event
        if result == "success":
            self.audit_logger.info("Secret accessed successfully", extra=audit_entry)
        else:
            self.audit_logger.error("Secret access failed", extra=audit_entry)

    def rotate_secret(self, secret_name: str, new_value: str,
                     request_id: str = None) -> bool:
        """
        Rotate a secret to a new value with audit logging.

        Args:
            secret_name: Name of secret to rotate
            new_value: New secret value
            request_id: Request ID for audit correlation

        Returns:
            True if rotation successful, False otherwise
        """
        rotation_start_time = time.time()

        try:
            # Create new secret version
            parent = f"projects/{self.project_id}/secrets/{secret_name}"
            payload = {"data": new_value.encode("UTF-8")}

            response = self.secret_client.add_secret_version(
                request={"parent": parent, "payload": payload}
            )

            # Clear cache for this secret
            self._clear_secret_cache(secret_name)

            # Log successful rotation
            self._log_secret_rotation("secret_rotation", secret_name, request_id,
                                    rotation_start_time, "success", response.name)

            return True

        except Exception as e:
            # Log failed rotation
            self._log_secret_rotation("secret_rotation", secret_name, request_id,
                                    rotation_start_time, "failed", error_message=str(e))
            return False

    def _log_secret_rotation(self, event_type: str, secret_name: str, request_id: str,
                           start_time: float, result: str, new_version: str = None,
                           error_message: str = None) -> None:
        """Log secret rotation events for security auditing."""
        rotation_duration_ms = (time.time() - start_time) * 1000

        audit_entry = {
            "timestamp": datetime.now().isoformat() + "Z",
            "event_type": event_type,
            "resource": f"projects/{self.project_id}/secrets/{secret_name}",
            "resource_name": secret_name,
            "result": result,
            "rotation_duration_ms": rotation_duration_ms,
            "service_name": "ai-usage-analytics",
            "environment": self.env,
            "request_id": request_id,
            "user_agent": "config-service/1.0"
        }

        if new_version:
            audit_entry["new_version"] = new_version
        if error_message:
            audit_entry["error_message"] = error_message

        # Log security event
        if result == "success":
            self.audit_logger.info("Secret rotated successfully", extra=audit_entry)
        else:
            self.audit_logger.error("Secret rotation failed", extra=audit_entry)

    def _clear_secret_cache(self, secret_name: str) -> None:
        """Clear cached entries for a secret."""
        keys_to_remove = [key for key in self._secret_cache.keys() if key.startswith(f"{secret_name}:")]
        for key in keys_to_remove:
            del self._secret_cache[key]

    def list_secrets(self, request_id: str = None) -> Dict[str, Any]:
        """List all secrets managed by this configuration with audit logging."""
        try:
            secrets_info = {
                "anthropic_secret": {
                    "name": self.anthropic_secret,
                    "status": "configured",
                    "last_accessed": self._secret_cache.get(f"{self.anthropic_secret}:latest", {}).get("timestamp")
                },
                "cursor_secret": {
                    "name": self.cursor_secret,
                    "status": "configured",
                    "last_accessed": self._secret_cache.get(f"{self.cursor_secret}:latest", {}).get("timestamp")
                },
                "sheets_secret": {
                    "name": self.sheets_secret,
                    "status": "configured",
                    "last_accessed": self._secret_cache.get(f"{self.sheets_secret}:latest", {}).get("timestamp")
                }
            }

            # Log security inventory request
            self.audit_logger.info("Secret inventory requested", extra={
                "event_type": "secret_inventory",
                "request_id": request_id,
                "secrets_count": len(secrets_info),
                "timestamp": datetime.now().isoformat() + "Z"
            })

            return secrets_info

        except Exception as e:
            self.audit_logger.error("Failed to list secrets", extra={
                "event_type": "secret_inventory",
                "request_id": request_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat() + "Z"
            })
            return {}

    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from Secret Manager with security hardening."""
        if self.env == "production":
            # Production: Secret Manager only
            return self.get_secret(self.anthropic_secret)
        else:
            # Development: Allow environment fallback with security warning
            direct_key = os.getenv("ANTHROPIC_ADMIN_KEY_SECRET")
            if direct_key and direct_key.startswith("sk-"):
                self.audit_logger.warning("DEVELOPMENT: Using environment variable for API key",
                                        extra={
                                            "secret_name": self.anthropic_secret,
                                            "security_warning": "Production requires Secret Manager",
                                            "environment": self.env
                                        })
                return direct_key
            # Fall back to Secret Manager
            return self.get_secret(self.anthropic_secret)

    @property
    def cursor_api_key(self) -> Optional[str]:
        """Get Cursor API key from Secret Manager with security hardening."""
        if self.env == "production":
            # Production: Secret Manager only
            return self.get_secret(self.cursor_secret)
        else:
            # Development: Allow environment fallback with security warning
            direct_key = os.getenv("CURSOR_API_KEY_SECRET")
            if direct_key and direct_key.startswith("key_"):
                self.audit_logger.warning("DEVELOPMENT: Using environment variable for API key",
                                        extra={
                                            "secret_name": self.cursor_secret,
                                            "security_warning": "Production requires Secret Manager",
                                            "environment": self.env
                                        })
                return direct_key
            # Fall back to Secret Manager
            return self.get_secret(self.cursor_secret)

    @property
    def sheets_service_key(self) -> Optional[str]:
        """Get Google Sheets service account key from Secret Manager."""
        return self.get_secret(self.sheets_secret)


# Global config instance
config = Config()