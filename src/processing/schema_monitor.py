"""Schema drift detection and monitoring for AI Usage Analytics Dashboard."""

import time
import json
import hashlib
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from ..shared.logging_setup import get_logger, RequestContextLogger
from ..shared.cloud_monitoring import get_cloud_monitoring
from ..shared.error_tracker import error_tracker, ErrorCategory
from ..shared.config import config

logger = get_logger(__name__)


class SchemaChangeType(Enum):
    """Types of schema changes detected."""
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_CHANGED = "nullable_changed"
    STRUCTURE_CHANGED = "structure_changed"
    NO_CHANGE = "no_change"


class SchemaChangeImpact(Enum):
    """Impact levels of schema changes."""
    BREAKING = "breaking"
    COMPATIBLE = "compatible"
    INFORMATIONAL = "informational"


@dataclass
class SchemaChange:
    """Represents a detected schema change."""
    change_type: SchemaChangeType
    impact: SchemaChangeImpact
    field_path: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaFingerprint:
    """Schema fingerprint for change detection."""
    source: str  # cursor, anthropic, sheets
    endpoint: str
    fingerprint_hash: str
    field_count: int
    schema_structure: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaDriftReport:
    """Comprehensive schema drift analysis report."""
    source: str
    endpoint: str
    analysis_date: datetime
    current_fingerprint: SchemaFingerprint
    previous_fingerprint: Optional[SchemaFingerprint]
    changes_detected: List[SchemaChange]
    drift_severity: SchemaChangeImpact
    requires_action: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaMonitor:
    """Monitors API response schemas for drift and breaking changes."""

    def __init__(self):
        """Initialize schema monitor."""
        self.project_id = config.project_id
        self.dataset_id = config.dataset
        self.client = bigquery.Client(project=self.project_id)
        self.context_logger = RequestContextLogger("schema_monitor")

        # Schema fingerprint storage table
        self.fingerprint_table = f"{self.project_id}.{self.dataset_id}.schema_fingerprints"

        logger.info("Initialized Schema Monitor", extra={
            "project_id": self.project_id,
            "fingerprint_table": self.fingerprint_table
        })

    def create_schema_fingerprint(self, source: str, endpoint: str,
                                 response_data: Dict[str, Any]) -> SchemaFingerprint:
        """Create schema fingerprint from API response data."""
        try:
            # Analyze response structure
            schema_structure = self._analyze_response_structure(response_data)

            # Create deterministic hash
            schema_json = json.dumps(schema_structure, sort_keys=True)
            fingerprint_hash = hashlib.md5(schema_json.encode()).hexdigest()

            fingerprint = SchemaFingerprint(
                source=source,
                endpoint=endpoint,
                fingerprint_hash=fingerprint_hash,
                field_count=self._count_fields(schema_structure),
                schema_structure=schema_structure,
                metadata={
                    "sample_data_size": len(str(response_data)),
                    "analysis_method": "recursive_structure_analysis"
                }
            )

            self.context_logger.debug("Created schema fingerprint",
                                    source=source,
                                    endpoint=endpoint,
                                    fingerprint_hash=fingerprint_hash,
                                    field_count=fingerprint.field_count)

            return fingerprint

        except Exception as e:
            error_tracker.track_exception(e, "schema_monitor", source)
            raise

    def _analyze_response_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Recursively analyze response data structure."""
        if isinstance(data, dict):
            structure = {"type": "object", "fields": {}}
            for key, value in data.items():
                field_path = f"{path}.{key}" if path else key
                structure["fields"][key] = self._analyze_response_structure(value, field_path)
            return structure

        elif isinstance(data, list):
            if not data:
                return {"type": "array", "items": {"type": "unknown"}}

            # Analyze first few items to determine array item structure
            sample_items = data[:3] if len(data) > 3 else data
            item_structures = [self._analyze_response_structure(item, f"{path}[]") for item in sample_items]

            # Find common structure
            common_structure = self._find_common_structure(item_structures)
            return {"type": "array", "items": common_structure, "length": len(data)}

        elif isinstance(data, str):
            # Detect special string patterns
            if self._is_email(data):
                return {"type": "string", "format": "email"}
            elif self._is_datetime(data):
                return {"type": "string", "format": "datetime"}
            elif self._is_uuid(data):
                return {"type": "string", "format": "uuid"}
            else:
                return {"type": "string", "max_length": len(data)}

        elif isinstance(data, (int, float)):
            return {"type": "number", "value_type": type(data).__name__}

        elif isinstance(data, bool):
            return {"type": "boolean"}

        elif data is None:
            return {"type": "null"}

        else:
            return {"type": "unknown", "python_type": type(data).__name__}

    def _find_common_structure(self, structures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find common structure among array items."""
        if not structures:
            return {"type": "unknown"}

        # For simplicity, use the first structure as baseline
        # In production, this would implement proper structure merging
        return structures[0]

    def _count_fields(self, structure: Dict[str, Any]) -> int:
        """Count total fields in a schema structure."""
        count = 0
        if structure.get("type") == "object" and "fields" in structure:
            count += len(structure["fields"])
            for field_structure in structure["fields"].values():
                count += self._count_fields(field_structure)
        elif structure.get("type") == "array" and "items" in structure:
            count += self._count_fields(structure["items"])
        return count

    def _is_email(self, value: str) -> bool:
        """Check if string appears to be an email address."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))

    def _is_datetime(self, value: str) -> bool:
        """Check if string appears to be a datetime."""
        datetime_patterns = [
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',   # SQL format
            r'^\d{4}-\d{2}-\d{2}$'                      # Date only
        ]
        return any(re.match(pattern, value) for pattern in datetime_patterns)

    def _is_uuid(self, value: str) -> bool:
        """Check if string appears to be a UUID."""
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        return bool(re.match(uuid_pattern, value))

    def compare_schema_fingerprints(self, current: SchemaFingerprint,
                                  previous: SchemaFingerprint) -> List[SchemaChange]:
        """Compare two schema fingerprints to detect changes."""
        if current.fingerprint_hash == previous.fingerprint_hash:
            return [SchemaChange(
                change_type=SchemaChangeType.NO_CHANGE,
                impact=SchemaChangeImpact.INFORMATIONAL,
                field_path="",
                description="No schema changes detected"
            )]

        changes = []

        # Compare field counts
        if current.field_count != previous.field_count:
            field_diff = current.field_count - previous.field_count
            change_type = SchemaChangeType.FIELD_ADDED if field_diff > 0 else SchemaChangeType.FIELD_REMOVED
            impact = SchemaChangeImpact.COMPATIBLE if field_diff > 0 else SchemaChangeImpact.BREAKING

            changes.append(SchemaChange(
                change_type=change_type,
                impact=impact,
                field_path="<root>",
                old_value=previous.field_count,
                new_value=current.field_count,
                description=f"Field count changed from {previous.field_count} to {current.field_count}"
            ))

        # Deep structure comparison
        structure_changes = self._compare_structures(
            current.schema_structure,
            previous.schema_structure,
            ""
        )
        changes.extend(structure_changes)

        return changes

    def _compare_structures(self, current: Dict[str, Any], previous: Dict[str, Any],
                           path: str) -> List[SchemaChange]:
        """Recursively compare schema structures."""
        changes = []

        # Compare object fields
        if current.get("type") == "object" and previous.get("type") == "object":
            current_fields = current.get("fields", {})
            previous_fields = previous.get("fields", {})

            # Check for added fields
            for field_name in current_fields:
                field_path = f"{path}.{field_name}" if path else field_name
                if field_name not in previous_fields:
                    changes.append(SchemaChange(
                        change_type=SchemaChangeType.FIELD_ADDED,
                        impact=SchemaChangeImpact.COMPATIBLE,
                        field_path=field_path,
                        new_value=current_fields[field_name],
                        description=f"New field added: {field_path}"
                    ))

            # Check for removed fields
            for field_name in previous_fields:
                field_path = f"{path}.{field_name}" if path else field_name
                if field_name not in current_fields:
                    changes.append(SchemaChange(
                        change_type=SchemaChangeType.FIELD_REMOVED,
                        impact=SchemaChangeImpact.BREAKING,
                        field_path=field_path,
                        old_value=previous_fields[field_name],
                        description=f"Field removed: {field_path}"
                    ))

            # Check for type changes in existing fields
            for field_name in current_fields:
                if field_name in previous_fields:
                    field_path = f"{path}.{field_name}" if path else field_name
                    current_field = current_fields[field_name]
                    previous_field = previous_fields[field_name]

                    if current_field.get("type") != previous_field.get("type"):
                        changes.append(SchemaChange(
                            change_type=SchemaChangeType.TYPE_CHANGED,
                            impact=SchemaChangeImpact.BREAKING,
                            field_path=field_path,
                            old_value=previous_field.get("type"),
                            new_value=current_field.get("type"),
                            description=f"Type changed for {field_path}: "
                                       f"{previous_field.get('type')} → {current_field.get('type')}"
                        ))

        return changes

    def detect_schema_drift(self, source: str, endpoint: str,
                           response_data: Dict[str, Any]) -> SchemaDriftReport:
        """Detect schema drift for an API endpoint."""
        self.context_logger.log_operation_start("detect_schema_drift",
                                               source=source,
                                               endpoint=endpoint)

        try:
            # Create current fingerprint
            current_fingerprint = self.create_schema_fingerprint(source, endpoint, response_data)

            # Get previous fingerprint
            previous_fingerprint = self._get_latest_fingerprint(source, endpoint)

            # Compare fingerprints
            changes = []
            if previous_fingerprint:
                changes = self.compare_schema_fingerprints(current_fingerprint, previous_fingerprint)
            else:
                # First time seeing this schema - not an error, just informational
                changes = [SchemaChange(
                    change_type=SchemaChangeType.STRUCTURE_CHANGED,
                    impact=SchemaChangeImpact.INFORMATIONAL,
                    field_path="<root>",
                    description="Initial schema baseline established"
                )]

            # Determine drift severity
            drift_severity = self._determine_drift_severity(changes)

            # Check if action is required
            requires_action = drift_severity == SchemaChangeImpact.BREAKING

            # Create drift report
            report = SchemaDriftReport(
                source=source,
                endpoint=endpoint,
                analysis_date=datetime.now(),
                current_fingerprint=current_fingerprint,
                previous_fingerprint=previous_fingerprint,
                changes_detected=changes,
                drift_severity=drift_severity,
                requires_action=requires_action,
                metadata={
                    "response_size": len(str(response_data)),
                    "analysis_duration_ms": 0  # Will be set below
                }
            )

            # Store new fingerprint
            self._store_fingerprint(current_fingerprint)

            # Record metrics
            self._record_schema_drift_metrics(report)

            self.context_logger.log_operation_complete("detect_schema_drift",
                                                     changes_detected=len(changes),
                                                     drift_severity=drift_severity.value,
                                                     requires_action=requires_action)

            return report

        except Exception as e:
            error_tracker.track_exception(e, "schema_monitor", source)
            self.context_logger.log_operation_error("detect_schema_drift", error=e)
            raise

    def _get_latest_fingerprint(self, source: str, endpoint: str) -> Optional[SchemaFingerprint]:
        """Get the latest schema fingerprint for a source/endpoint."""
        try:
            query = f"""
            SELECT *
            FROM `{self.fingerprint_table}`
            WHERE source = '{source}' AND endpoint = '{endpoint}'
            ORDER BY created_at DESC
            LIMIT 1
            """

            query_job = self.client.query(query)
            results = list(query_job.result())

            if not results:
                return None

            row = results[0]
            return SchemaFingerprint(
                source=row.source,
                endpoint=row.endpoint,
                fingerprint_hash=row.fingerprint_hash,
                field_count=row.field_count,
                schema_structure=json.loads(row.schema_structure),
                created_at=row.created_at,
                metadata=json.loads(row.metadata) if row.metadata else {}
            )

        except Exception as e:
            logger.warning(f"Failed to retrieve previous fingerprint for {source}/{endpoint}",
                         extra={"error": str(e)})
            return None

    def _store_fingerprint(self, fingerprint: SchemaFingerprint) -> bool:
        """Store schema fingerprint in BigQuery."""
        try:
            # Prepare row for insertion
            row = {
                "source": fingerprint.source,
                "endpoint": fingerprint.endpoint,
                "fingerprint_hash": fingerprint.fingerprint_hash,
                "field_count": fingerprint.field_count,
                "schema_structure": json.dumps(fingerprint.schema_structure),
                "created_at": fingerprint.created_at,
                "metadata": json.dumps(fingerprint.metadata)
            }

            # Insert row
            table_ref = self.client.dataset(self.dataset_id).table("schema_fingerprints")
            errors = self.client.insert_rows_json(table_ref, [row])

            if errors:
                logger.error("Failed to store schema fingerprint", extra={
                    "errors": errors,
                    "source": fingerprint.source,
                    "endpoint": fingerprint.endpoint
                })
                return False

            logger.debug("Stored schema fingerprint", extra={
                "source": fingerprint.source,
                "endpoint": fingerprint.endpoint,
                "fingerprint_hash": fingerprint.fingerprint_hash
            })

            return True

        except Exception as e:
            logger.error("Failed to store schema fingerprint", extra={
                "error": str(e),
                "source": fingerprint.source,
                "endpoint": fingerprint.endpoint
            })
            return False

    def _determine_drift_severity(self, changes: List[SchemaChange]) -> SchemaChangeImpact:
        """Determine overall drift severity from detected changes."""
        if not changes:
            return SchemaChangeImpact.INFORMATIONAL

        # Check for breaking changes
        breaking_changes = [c for c in changes if c.impact == SchemaChangeImpact.BREAKING]
        if breaking_changes:
            return SchemaChangeImpact.BREAKING

        # Check for compatible changes
        compatible_changes = [c for c in changes if c.impact == SchemaChangeImpact.COMPATIBLE]
        if compatible_changes:
            return SchemaChangeImpact.COMPATIBLE

        return SchemaChangeImpact.INFORMATIONAL

    def _record_schema_drift_metrics(self, report: SchemaDriftReport) -> None:
        """Record schema drift metrics to Cloud Monitoring."""
        try:
            monitoring_client = get_cloud_monitoring()

            # Record drift detection event
            drift_score = 0.0
            if report.drift_severity == SchemaChangeImpact.BREAKING:
                drift_score = 100.0  # High drift score for breaking changes
            elif report.drift_severity == SchemaChangeImpact.COMPATIBLE:
                drift_score = 50.0   # Medium drift score for compatible changes
            else:
                drift_score = 0.0    # No drift

            # Use error rate metric for schema drift tracking
            monitoring_client.record_error_rate(
                report.source,
                drift_score,
                "schema_drift"
            )

            logger.debug("Recorded schema drift metrics", extra={
                "source": report.source,
                "endpoint": report.endpoint,
                "drift_score": drift_score,
                "changes_count": len(report.changes_detected)
            })

        except Exception as e:
            logger.warning("Failed to record schema drift metrics", extra={"error": str(e)})

    def monitor_api_schemas(self, api_responses: Dict[str, Dict[str, Any]]) -> List[SchemaDriftReport]:
        """Monitor multiple API responses for schema drift."""
        reports = []

        for api_key, response_data in api_responses.items():
            try:
                # Parse API key to get source and endpoint
                if '/' in api_key:
                    source, endpoint = api_key.split('/', 1)
                else:
                    source, endpoint = api_key, "default"

                # Detect drift
                drift_report = self.detect_schema_drift(source, endpoint, response_data)
                reports.append(drift_report)

                # Log significant changes
                if drift_report.requires_action:
                    logger.warning(f"Schema drift requires action: {source}/{endpoint}",
                                 extra={
                                     "drift_severity": drift_report.drift_severity.value,
                                     "changes_count": len(drift_report.changes_detected)
                                 })

            except Exception as e:
                error_tracker.track_exception(e, "schema_monitor", source if 'source' in locals() else "unknown")
                logger.error(f"Failed to monitor schema for {api_key}", extra={"error": str(e)})

        return reports

    def create_schema_drift_alert(self, report: SchemaDriftReport) -> Dict[str, Any]:
        """Create alert data for schema drift detection."""
        if not report.requires_action:
            return {}

        alert_data = {
            "alert_type": "schema_drift_detected",
            "severity": "critical" if report.drift_severity == SchemaChangeImpact.BREAKING else "warning",
            "source": report.source,
            "endpoint": report.endpoint,
            "changes_count": len(report.changes_detected),
            "drift_severity": report.drift_severity.value,
            "breaking_changes": [
                c.description for c in report.changes_detected
                if c.impact == SchemaChangeImpact.BREAKING
            ],
            "message": f"Schema drift detected for {report.source}/{report.endpoint}: "
                      f"{len(report.changes_detected)} changes found "
                      f"(severity: {report.drift_severity.value})",
            "timestamp": report.analysis_date.isoformat(),
            "requires_immediate_action": report.drift_severity == SchemaChangeImpact.BREAKING,
            "fingerprint_hash_old": report.previous_fingerprint.fingerprint_hash if report.previous_fingerprint else None,
            "fingerprint_hash_new": report.current_fingerprint.fingerprint_hash
        }

        return alert_data

    def get_schema_drift_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Get schema drift summary for the specified period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)

            query = f"""
            SELECT
                source,
                endpoint,
                COUNT(*) as fingerprint_count,
                COUNT(DISTINCT fingerprint_hash) as unique_schemas
            FROM `{self.fingerprint_table}`
            WHERE created_at >= '{cutoff_date.isoformat()}'
            GROUP BY source, endpoint
            ORDER BY source, endpoint
            """

            query_job = self.client.query(query)
            results = query_job.result()

            summary = {
                "analysis_period_days": days_back,
                "total_endpoints_monitored": 0,
                "endpoints_with_changes": 0,
                "endpoint_details": [],
                "generated_at": datetime.now().isoformat()
            }

            for row in results:
                endpoint_info = {
                    "source": row.source,
                    "endpoint": row.endpoint,
                    "fingerprint_count": row.fingerprint_count,
                    "unique_schemas": row.unique_schemas,
                    "has_changes": row.unique_schemas > 1
                }

                summary["endpoint_details"].append(endpoint_info)
                summary["total_endpoints_monitored"] += 1

                if endpoint_info["has_changes"]:
                    summary["endpoints_with_changes"] += 1

            return summary

        except Exception as e:
            logger.error("Failed to generate schema drift summary", extra={"error": str(e)})
            return {}


# Global instance - lazy initialization
schema_monitor = None

def get_schema_monitor():
    """Get or create schema monitor instance."""
    global schema_monitor
    if schema_monitor is None:
        schema_monitor = SchemaMonitor()
    return schema_monitor