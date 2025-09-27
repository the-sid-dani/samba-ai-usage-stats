"""Unit tests for schema drift detection and monitoring."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import json

from src.processing.schema_monitor import (
    SchemaMonitor, SchemaFingerprint, SchemaDriftReport, SchemaChange,
    SchemaChangeType, SchemaChangeImpact
)


@pytest.fixture
def schema_monitor():
    """Create SchemaMonitor instance with mocked dependencies."""
    with patch('src.processing.schema_monitor.bigquery.Client'), \
         patch('src.processing.schema_monitor.config') as mock_config:
        mock_config.project_id = "test-project"
        mock_config.dataset = "test_dataset"

        return SchemaMonitor()


class TestSchemaMonitor:
    """Test cases for SchemaMonitor."""

    def test_initialization(self, schema_monitor):
        """Test schema monitor initialization."""
        assert schema_monitor.project_id == "test-project"
        assert schema_monitor.dataset_id == "test_dataset"
        assert "schema_fingerprints" in schema_monitor.fingerprint_table

    def test_create_schema_fingerprint_simple_object(self, schema_monitor):
        """Test schema fingerprint creation for simple object (AC 3)."""
        # Given: Simple API response structure
        response_data = {
            "email": "user@example.com",
            "total_lines_added": 1500,
            "cost": 25.50,
            "active": True
        }

        # When: Creating fingerprint
        fingerprint = schema_monitor.create_schema_fingerprint("cursor", "/usage", response_data)

        # Then: Should create valid fingerprint
        assert fingerprint.source == "cursor"
        assert fingerprint.endpoint == "/usage"
        assert fingerprint.field_count == 4
        assert fingerprint.fingerprint_hash is not None
        assert len(fingerprint.fingerprint_hash) == 32  # MD5 hash length

        # Verify structure analysis
        structure = fingerprint.schema_structure
        assert structure["type"] == "object"
        assert "fields" in structure
        assert "email" in structure["fields"]
        assert structure["fields"]["email"]["type"] == "string"
        assert structure["fields"]["email"]["format"] == "email"

    def test_create_schema_fingerprint_nested_structure(self, schema_monitor):
        """Test schema fingerprint for nested response structure (AC 3)."""
        # Given: Nested API response (like Anthropic API)
        response_data = {
            "data": [
                {
                    "starting_at": "2025-09-19T00:00:00Z",
                    "results": [
                        {
                            "uncached_input_tokens": 118459752,
                            "output_tokens": 5430933
                        }
                    ]
                }
            ]
        }

        # When: Creating fingerprint
        fingerprint = schema_monitor.create_schema_fingerprint("anthropic", "/usage", response_data)

        # Then: Should analyze nested structure correctly
        assert fingerprint.source == "anthropic"
        assert fingerprint.endpoint == "/usage"
        assert fingerprint.field_count > 4  # Should count nested fields

        structure = fingerprint.schema_structure
        assert structure["type"] == "object"
        assert "data" in structure["fields"]
        assert structure["fields"]["data"]["type"] == "array"

    def test_analyze_response_structure_email_detection(self, schema_monitor):
        """Test email format detection in response analysis."""
        # Given: String that looks like email
        email_value = "user@samba.tv"

        # When: Analyzing structure
        result = schema_monitor._analyze_response_structure(email_value)

        # Then: Should detect email format
        assert result["type"] == "string"
        assert result["format"] == "email"

    def test_analyze_response_structure_datetime_detection(self, schema_monitor):
        """Test datetime format detection in response analysis."""
        # Given: String that looks like datetime
        datetime_value = "2025-09-19T00:00:00Z"

        # When: Analyzing structure
        result = schema_monitor._analyze_response_structure(datetime_value)

        # Then: Should detect datetime format
        assert result["type"] == "string"
        assert result["format"] == "datetime"

    def test_compare_schema_fingerprints_no_change(self, schema_monitor):
        """Test schema comparison with no changes (AC 3)."""
        # Given: Identical fingerprints
        fingerprint1 = SchemaFingerprint(
            source="cursor",
            endpoint="/usage",
            fingerprint_hash="abc123",
            field_count=4,
            schema_structure={"type": "object", "fields": {"email": {"type": "string"}}}
        )

        fingerprint2 = SchemaFingerprint(
            source="cursor",
            endpoint="/usage",
            fingerprint_hash="abc123",
            field_count=4,
            schema_structure={"type": "object", "fields": {"email": {"type": "string"}}}
        )

        # When: Comparing fingerprints
        changes = schema_monitor.compare_schema_fingerprints(fingerprint1, fingerprint2)

        # Then: Should detect no changes
        assert len(changes) == 1
        assert changes[0].change_type == SchemaChangeType.NO_CHANGE
        assert changes[0].impact == SchemaChangeImpact.INFORMATIONAL

    def test_compare_schema_fingerprints_field_added(self, schema_monitor):
        """Test schema comparison with added field (AC 3)."""
        # Given: Schema with additional field
        old_structure = {"type": "object", "fields": {"email": {"type": "string"}}}
        new_structure = {"type": "object", "fields": {
            "email": {"type": "string"},
            "new_field": {"type": "number"}
        }}

        old_fingerprint = SchemaFingerprint("cursor", "/usage", "old_hash", 1, old_structure)
        new_fingerprint = SchemaFingerprint("cursor", "/usage", "new_hash", 2, new_structure)

        # When: Comparing fingerprints
        changes = schema_monitor.compare_schema_fingerprints(new_fingerprint, old_fingerprint)

        # Then: Should detect field addition
        field_changes = [c for c in changes if c.change_type == SchemaChangeType.FIELD_ADDED]
        assert len(field_changes) >= 1
        assert any("field count changed" in c.description.lower() for c in changes)

    def test_compare_schema_fingerprints_breaking_change(self, schema_monitor):
        """Test schema comparison with breaking changes (AC 3)."""
        # Given: Schema with removed required field
        old_structure = {"type": "object", "fields": {
            "email": {"type": "string"},
            "cost": {"type": "number"}
        }}
        new_structure = {"type": "object", "fields": {"email": {"type": "string"}}}

        old_fingerprint = SchemaFingerprint("anthropic", "/cost", "old_hash", 2, old_structure)
        new_fingerprint = SchemaFingerprint("anthropic", "/cost", "new_hash", 1, new_structure)

        # When: Comparing fingerprints
        changes = schema_monitor.compare_schema_fingerprints(new_fingerprint, old_fingerprint)

        # Then: Should detect field removal (breaking change)
        assert len(changes) >= 1
        field_reduction = any("field count changed" in c.description and c.impact == SchemaChangeImpact.BREAKING for c in changes)
        assert field_reduction

    def test_determine_drift_severity_breaking(self, schema_monitor):
        """Test drift severity determination for breaking changes."""
        # Given: Changes including breaking changes
        changes = [
            SchemaChange(SchemaChangeType.FIELD_REMOVED, SchemaChangeImpact.BREAKING, "cost", description="Field removed"),
            SchemaChange(SchemaChangeType.FIELD_ADDED, SchemaChangeImpact.COMPATIBLE, "new_field", description="Field added")
        ]

        # When: Determining severity
        severity = schema_monitor._determine_drift_severity(changes)

        # Then: Should return breaking (highest priority)
        assert severity == SchemaChangeImpact.BREAKING

    def test_determine_drift_severity_compatible(self, schema_monitor):
        """Test drift severity determination for compatible changes."""
        # Given: Only compatible changes
        changes = [
            SchemaChange(SchemaChangeType.FIELD_ADDED, SchemaChangeImpact.COMPATIBLE, "new_field", description="Field added")
        ]

        # When: Determining severity
        severity = schema_monitor._determine_drift_severity(changes)

        # Then: Should return compatible
        assert severity == SchemaChangeImpact.COMPATIBLE

    def test_create_schema_drift_alert_breaking(self, schema_monitor):
        """Test schema drift alert creation for breaking changes (AC 3, 6)."""
        # Given: Drift report with breaking changes
        current_fingerprint = SchemaFingerprint("cursor", "/usage", "new_hash", 3, {})
        previous_fingerprint = SchemaFingerprint("cursor", "/usage", "old_hash", 4, {})

        report = SchemaDriftReport(
            source="cursor",
            endpoint="/usage",
            analysis_date=datetime.now(),
            current_fingerprint=current_fingerprint,
            previous_fingerprint=previous_fingerprint,
            changes_detected=[
                SchemaChange(SchemaChangeType.FIELD_REMOVED, SchemaChangeImpact.BREAKING, "cost")
            ],
            drift_severity=SchemaChangeImpact.BREAKING,
            requires_action=True
        )

        # When: Creating alert
        alert = schema_monitor.create_schema_drift_alert(report)

        # Then: Should create critical alert
        assert alert["alert_type"] == "schema_drift_detected"
        assert alert["severity"] == "critical"
        assert alert["source"] == "cursor"
        assert alert["endpoint"] == "/usage"
        assert alert["requires_immediate_action"] is True
        assert len(alert["breaking_changes"]) > 0

    def test_create_schema_drift_alert_no_action_needed(self, schema_monitor):
        """Test schema drift alert when no action is needed."""
        # Given: Drift report with no action required
        report = SchemaDriftReport(
            source="cursor",
            endpoint="/usage",
            analysis_date=datetime.now(),
            current_fingerprint=SchemaFingerprint("cursor", "/usage", "same_hash", 3, {}),
            previous_fingerprint=None,
            changes_detected=[],
            drift_severity=SchemaChangeImpact.INFORMATIONAL,
            requires_action=False
        )

        # When: Creating alert
        alert = schema_monitor.create_schema_drift_alert(report)

        # Then: Should return empty alert
        assert alert == {}


class TestSchemaFingerprint:
    """Test cases for SchemaFingerprint dataclass."""

    def test_schema_fingerprint_creation(self):
        """Test SchemaFingerprint creation with all fields."""
        # Given: Complete fingerprint data
        structure = {"type": "object", "fields": {"test": {"type": "string"}}}

        # When: Creating fingerprint
        fingerprint = SchemaFingerprint(
            source="test_source",
            endpoint="/test",
            fingerprint_hash="test_hash_123",
            field_count=5,
            schema_structure=structure
        )

        # Then: Should create valid fingerprint
        assert fingerprint.source == "test_source"
        assert fingerprint.endpoint == "/test"
        assert fingerprint.fingerprint_hash == "test_hash_123"
        assert fingerprint.field_count == 5
        assert fingerprint.schema_structure == structure
        assert fingerprint.created_at is not None


class TestVarianceAnalysis:
    """Test cases for VarianceAnalysis dataclass."""

    def test_variance_analysis_creation(self):
        """Test VarianceAnalysis creation with all fields."""
        # Given: Variance analysis data
        calculated = Decimal('1000.00')
        vendor = Decimal('950.00')
        variance = calculated - vendor

        # When: Creating variance analysis
        analysis = VarianceAnalysis(
            platform="test_platform",
            period="2025-09",
            calculated_cost=calculated,
            vendor_cost=vendor,
            variance_amount=variance,
            variance_percentage=5.26,
            status=ReconciliationStatus.VARIANCE_WARNING,
            threshold_breached=True
        )

        # Then: Should create valid analysis
        assert analysis.platform == "test_platform"
        assert analysis.period == "2025-09"
        assert analysis.calculated_cost == Decimal('1000.00')
        assert analysis.vendor_cost == Decimal('950.00')
        assert analysis.variance_amount == Decimal('50.00')
        assert analysis.variance_percentage == 5.26
        assert analysis.status == ReconciliationStatus.VARIANCE_WARNING
        assert analysis.threshold_breached is True