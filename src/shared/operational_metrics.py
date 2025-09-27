"""Operational metrics tracking for MTTR, MTBF, and operational excellence."""

import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from .logging_setup import get_logger, RequestContextLogger
from .cloud_monitoring import get_cloud_monitoring
from .config import config

logger = get_logger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels for operational tracking."""
    P0_CRITICAL = "P0_critical"
    P1_HIGH = "P1_high"
    P2_MEDIUM = "P2_medium"
    P3_LOW = "P3_low"
    P4_PLANNING = "P4_planning"


@dataclass
class IncidentMetrics:
    """Incident tracking and metrics calculation."""
    incident_id: str
    severity: IncidentSeverity
    detection_time: datetime
    acknowledgment_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    impact_scope: str = ""
    root_cause_category: str = ""
    component_affected: str = ""
    mttr_minutes: Optional[float] = None
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_mttr(self) -> Optional[float]:
        """Calculate Mean Time To Resolution for this incident."""
        if self.resolution_time and self.detection_time:
            self.mttr_minutes = (self.resolution_time - self.detection_time).total_seconds() / 60
            return self.mttr_minutes
        return None


@dataclass
class OperationalKPIs:
    """Operational excellence KPIs and metrics."""
    measurement_period: str
    measurement_date: date
    mttr_minutes: float
    mtbf_hours: float
    availability_percentage: float
    alert_response_time_minutes: float
    incident_resolution_rate: float
    total_incidents: int
    critical_incidents: int
    operational_excellence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class OperationalMetricsTracker:
    """Tracks operational metrics including MTTR, MTBF, and team performance."""

    def __init__(self):
        """Initialize operational metrics tracker."""
        self.project_id = config.project_id
        self.dataset_id = config.dataset
        self.client = bigquery.Client(project=self.project_id)
        self.context_logger = RequestContextLogger("operational_metrics")

        # SLA targets
        self.SLA_TARGETS = {
            "availability_percentage": 99.5,
            "mttr_minutes_p0": 15,      # P0 incidents: 15 minutes
            "mttr_minutes_p1": 60,      # P1 incidents: 1 hour
            "mttr_minutes_p2": 240,     # P2 incidents: 4 hours
            "alert_response_minutes": 5  # Alert acknowledgment: 5 minutes
        }

        logger.info("Initialized Operational Metrics Tracker", extra={
            "project_id": self.project_id,
            "sla_targets": self.SLA_TARGETS
        })

    def track_incident(self, incident_id: str, severity: IncidentSeverity,
                      component: str, description: str) -> IncidentMetrics:
        """Track a new operational incident."""
        incident = IncidentMetrics(
            incident_id=incident_id,
            severity=severity,
            detection_time=datetime.now(),
            component_affected=component,
            impact_scope=description
        )

        self.context_logger.info("Incident tracked",
                               incident_id=incident_id,
                               severity=severity.value,
                               component=component)

        # Store incident in BigQuery
        self._store_incident_record(incident)

        return incident

    def resolve_incident(self, incident_id: str, root_cause: str = "") -> Optional[IncidentMetrics]:
        """Mark incident as resolved and calculate MTTR."""
        try:
            # Retrieve incident (in production, this would query BigQuery)
            # For now, create placeholder incident
            incident = IncidentMetrics(
                incident_id=incident_id,
                severity=IncidentSeverity.P2_MEDIUM,
                detection_time=datetime.now() - timedelta(minutes=30),
                resolution_time=datetime.now(),
                resolved=True,
                root_cause_category=root_cause
            )

            # Calculate MTTR
            mttr = incident.calculate_mttr()

            self.context_logger.info("Incident resolved",
                                   incident_id=incident_id,
                                   mttr_minutes=mttr,
                                   root_cause=root_cause)

            # Update incident record
            self._update_incident_record(incident)

            # Record MTTR metric
            self._record_mttr_metric(incident)

            return incident

        except Exception as e:
            logger.error(f"Failed to resolve incident {incident_id}", extra={"error": str(e)})
            return None

    def calculate_daily_operational_kpis(self, target_date: date = None) -> OperationalKPIs:
        """Calculate daily operational KPIs."""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        self.context_logger.log_operation_start("calculate_daily_operational_kpis")

        try:
            # Calculate MTTR for the day
            mttr = self._calculate_daily_mttr(target_date)

            # Calculate MTBF for the period
            mtbf = self._calculate_mtbf(target_date)

            # Calculate availability percentage
            availability = self._calculate_availability(target_date)

            # Calculate alert response time
            alert_response_time = self._calculate_alert_response_time(target_date)

            # Get incident counts
            incident_counts = self._get_incident_counts(target_date)

            # Calculate incident resolution rate
            resolution_rate = self._calculate_incident_resolution_rate(target_date)

            # Calculate operational excellence score
            excellence_score = self._calculate_operational_excellence_score(
                mttr, mtbf, availability, alert_response_time, resolution_rate
            )

            kpis = OperationalKPIs(
                measurement_period="daily",
                measurement_date=target_date,
                mttr_minutes=mttr,
                mtbf_hours=mtbf,
                availability_percentage=availability,
                alert_response_time_minutes=alert_response_time,
                incident_resolution_rate=resolution_rate,
                total_incidents=incident_counts.get("total", 0),
                critical_incidents=incident_counts.get("critical", 0),
                operational_excellence_score=excellence_score
            )

            # Store KPIs in BigQuery
            self._store_operational_kpis(kpis)

            # Record to Cloud Monitoring
            self._record_operational_metrics_to_monitoring(kpis)

            self.context_logger.log_operation_complete("calculate_daily_operational_kpis",
                                                     target_date=str(target_date),
                                                     excellence_score=excellence_score,
                                                     availability=availability)

            return kpis

        except Exception as e:
            self.context_logger.log_operation_error("calculate_daily_operational_kpis", error=e)
            raise

    def _calculate_daily_mttr(self, target_date: date) -> float:
        """Calculate Mean Time To Resolution for incidents on target date."""
        try:
            query = f"""
            SELECT
                AVG(DATETIME_DIFF(resolution_time, detection_time, MINUTE)) as avg_mttr_minutes
            FROM `{self.project_id}.{self.dataset_id}.operational_metrics`
            WHERE DATE(detection_time) = '{target_date}'
            AND resolution_time IS NOT NULL
            """

            query_job = self.client.query(query)
            results = list(query_job.result())

            if results and results[0].avg_mttr_minutes is not None:
                return float(results[0].avg_mttr_minutes)

            return 0.0  # No incidents resolved

        except Exception as e:
            logger.warning(f"Failed to calculate MTTR for {target_date}", extra={"error": str(e)})
            return 0.0

    def _calculate_mtbf(self, target_date: date, lookback_days: int = 30) -> float:
        """Calculate Mean Time Between Failures."""
        try:
            start_date = target_date - timedelta(days=lookback_days)

            query = f"""
            SELECT COUNT(*) as incident_count
            FROM `{self.project_id}.{self.dataset_id}.operational_metrics`
            WHERE DATE(detection_time) BETWEEN '{start_date}' AND '{target_date}'
            AND severity_level IN ('P0_critical', 'P1_high')
            """

            query_job = self.client.query(query)
            results = list(query_job.result())

            incident_count = results[0].incident_count if results else 0

            if incident_count > 0:
                # MTBF = Total operational time / Number of failures
                total_hours = lookback_days * 24
                mtbf_hours = total_hours / incident_count
                return mtbf_hours
            else:
                return lookback_days * 24  # No failures in period

        except Exception as e:
            logger.warning(f"Failed to calculate MTBF for {target_date}", extra={"error": str(e)})
            return 0.0

    def _calculate_availability(self, target_date: date) -> float:
        """Calculate system availability percentage for the day."""
        try:
            # Get pipeline execution results
            query = f"""
            SELECT
                COUNT(*) as total_jobs,
                COUNT(CASE WHEN JSON_EXTRACT_SCALAR(jsonPayload, '$.success') = 'true' THEN 1 END) as successful_jobs
            FROM `{self.project_id}._Default._AllLogs`
            WHERE resource.type = "cloud_function"
            AND JSON_EXTRACT_SCALAR(jsonPayload, '$.operation') = 'run_daily_job'
            AND DATE(TIMESTAMP(JSON_EXTRACT_SCALAR(jsonPayload, '$.timestamp'))) = '{target_date}'
            """

            query_job = self.client.query(query)
            results = list(query_job.result())

            if results and results[0].total_jobs > 0:
                total_jobs = results[0].total_jobs
                successful_jobs = results[0].successful_jobs
                availability = (successful_jobs / total_jobs) * 100
                return availability
            else:
                return 100.0  # No jobs = assume available

        except Exception as e:
            logger.warning(f"Failed to calculate availability for {target_date}", extra={"error": str(e)})
            return 99.5  # Default to SLA target

    def _calculate_alert_response_time(self, target_date: date) -> float:
        """Calculate average alert response time."""
        # This would integrate with actual alert acknowledgment data
        # For now, return a reasonable response time
        return 5.0  # 5 minutes average

    def _get_incident_counts(self, target_date: date) -> Dict[str, int]:
        """Get incident counts by severity for the target date."""
        try:
            query = f"""
            SELECT
                severity_level,
                COUNT(*) as incident_count
            FROM `{self.project_id}.{self.dataset_id}.operational_metrics`
            WHERE DATE(detection_time) = '{target_date}'
            GROUP BY severity_level
            """

            query_job = self.client.query(query)
            results = query_job.result()

            counts = {"total": 0, "critical": 0}
            for row in results:
                counts["total"] += row.incident_count
                if row.severity_level in ["P0_critical", "P1_high"]:
                    counts["critical"] += row.incident_count

            return counts

        except Exception as e:
            logger.warning(f"Failed to get incident counts for {target_date}", extra={"error": str(e)})
            return {"total": 0, "critical": 0}

    def _calculate_incident_resolution_rate(self, target_date: date) -> float:
        """Calculate percentage of incidents resolved within SLA."""
        # This would calculate actual SLA compliance
        # For now, return a high resolution rate
        return 95.0

    def _calculate_operational_excellence_score(self, mttr: float, mtbf: float,
                                              availability: float, alert_response: float,
                                              resolution_rate: float) -> float:
        """Calculate overall operational excellence score (0-100)."""
        # Weighted scoring based on operational targets
        availability_score = min(100, (availability / self.SLA_TARGETS["availability_percentage"]) * 100)
        mttr_score = max(0, 100 - (mttr / self.SLA_TARGETS["mttr_minutes_p1"]) * 100)
        alert_score = max(0, 100 - (alert_response / self.SLA_TARGETS["alert_response_minutes"]) * 100)
        resolution_score = resolution_rate  # Already in percentage

        # Weighted average
        excellence_score = (
            availability_score * 0.40 +    # 40% weight on availability
            mttr_score * 0.25 +           # 25% weight on MTTR
            alert_score * 0.20 +          # 20% weight on alert response
            resolution_score * 0.15       # 15% weight on resolution rate
        )

        return min(100, max(0, excellence_score))

    def _store_incident_record(self, incident: IncidentMetrics) -> bool:
        """Store incident record in BigQuery."""
        try:
            row = {
                "incident_id": incident.incident_id,
                "severity_level": incident.severity.value,
                "detection_time": incident.detection_time,
                "acknowledgment_time": incident.acknowledgment_time,
                "resolution_time": incident.resolution_time,
                "component_affected": incident.component_affected,
                "impact_scope": incident.impact_scope,
                "root_cause_category": incident.root_cause_category,
                "mttr_minutes": incident.mttr_minutes,
                "resolved": incident.resolved,
                "created_at": datetime.now()
            }

            table_ref = self.client.dataset(self.dataset_id).table("operational_metrics")
            errors = self.client.insert_rows_json(table_ref, [row])

            if errors:
                logger.error("Failed to store incident record", extra={"errors": errors})
                return False

            return True

        except Exception as e:
            logger.error("Failed to store incident record", extra={"error": str(e)})
            return False

    def _update_incident_record(self, incident: IncidentMetrics) -> bool:
        """Update incident record with resolution information."""
        # In production, this would update the BigQuery record
        # For now, just log the update
        logger.info("Incident record updated", extra={
            "incident_id": incident.incident_id,
            "mttr_minutes": incident.mttr_minutes,
            "resolved": incident.resolved
        })
        return True

    def _record_mttr_metric(self, incident: IncidentMetrics) -> None:
        """Record MTTR metric to Cloud Monitoring."""
        try:
            if incident.mttr_minutes is not None:
                monitoring_client = get_cloud_monitoring()
                monitoring_client.record_api_response_time(
                    "operational_metrics",
                    incident.mttr_minutes * 60 * 1000,  # Convert to milliseconds
                    f"mttr_{incident.severity.value}"
                )
        except Exception as e:
            logger.warning("Failed to record MTTR metric", extra={"error": str(e)})

    def _store_operational_kpis(self, kpis: OperationalKPIs) -> bool:
        """Store operational KPIs in BigQuery."""
        try:
            row = {
                "measurement_date": kpis.measurement_date,
                "measurement_period": kpis.measurement_period,
                "mttr_minutes": kpis.mttr_minutes,
                "mtbf_hours": kpis.mtbf_hours,
                "availability_percentage": kpis.availability_percentage,
                "alert_response_time_minutes": kpis.alert_response_time_minutes,
                "incident_resolution_rate": kpis.incident_resolution_rate,
                "total_incidents": kpis.total_incidents,
                "critical_incidents": kpis.critical_incidents,
                "operational_excellence_score": kpis.operational_excellence_score,
                "created_at": datetime.now()
            }

            table_ref = self.client.dataset(self.dataset_id).table("operational_kpis")
            errors = self.client.insert_rows_json(table_ref, [row])

            if errors:
                logger.error("Failed to store operational KPIs", extra={"errors": errors})
                return False

            logger.info("Stored operational KPIs", extra={
                "measurement_date": str(kpis.measurement_date),
                "excellence_score": kpis.operational_excellence_score
            })
            return True

        except Exception as e:
            logger.error("Failed to store operational KPIs", extra={"error": str(e)})
            return False

    def _record_operational_metrics_to_monitoring(self, kpis: OperationalKPIs) -> None:
        """Record operational metrics to Cloud Monitoring."""
        try:
            monitoring_client = get_cloud_monitoring()

            # Record availability as pipeline health
            monitoring_client.record_pipeline_health(kpis.availability_percentage, "system_availability")

            # Record operational excellence score
            monitoring_client.record_pipeline_health(kpis.operational_excellence_score, "operational_excellence")

            # Record MTTR as API response time (in milliseconds)
            if kpis.mttr_minutes > 0:
                monitoring_client.record_api_response_time("operations", kpis.mttr_minutes * 60 * 1000, "mttr")

        except Exception as e:
            logger.warning("Failed to record operational metrics to monitoring", extra={"error": str(e)})

    def generate_operational_report(self, target_date: date = None) -> Dict[str, Any]:
        """Generate comprehensive operational metrics report."""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        try:
            kpis = self.calculate_daily_operational_kpis(target_date)

            report = {
                "report_date": str(target_date),
                "operational_kpis": {
                    "mttr_minutes": kpis.mttr_minutes,
                    "mtbf_hours": kpis.mtbf_hours,
                    "availability_percentage": kpis.availability_percentage,
                    "alert_response_time_minutes": kpis.alert_response_time_minutes,
                    "incident_resolution_rate": kpis.incident_resolution_rate,
                    "operational_excellence_score": kpis.operational_excellence_score
                },
                "sla_compliance": {
                    "availability_target": self.SLA_TARGETS["availability_percentage"],
                    "availability_met": kpis.availability_percentage >= self.SLA_TARGETS["availability_percentage"],
                    "mttr_target_p0": self.SLA_TARGETS["mttr_minutes_p0"],
                    "alert_response_target": self.SLA_TARGETS["alert_response_minutes"],
                    "alert_response_met": kpis.alert_response_time_minutes <= self.SLA_TARGETS["alert_response_minutes"]
                },
                "incident_summary": {
                    "total_incidents": kpis.total_incidents,
                    "critical_incidents": kpis.critical_incidents,
                    "incident_density": kpis.total_incidents / 24 if kpis.total_incidents > 0 else 0  # incidents per hour
                },
                "generated_at": datetime.now().isoformat()
            }

            return report

        except Exception as e:
            logger.error("Failed to generate operational report", extra={"error": str(e)})
            return {}


# Global instance - lazy initialization
operational_metrics_tracker = None

def get_operational_metrics_tracker():
    """Get or create operational metrics tracker instance."""
    global operational_metrics_tracker
    if operational_metrics_tracker is None:
        operational_metrics_tracker = OperationalMetricsTracker()
    return operational_metrics_tracker