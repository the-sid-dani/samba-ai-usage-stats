"""Vendor invoice reconciliation system for AI Usage Analytics Dashboard."""

import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import statistics

from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from ..shared.logging_setup import get_logger, RequestContextLogger
from ..shared.cloud_monitoring import get_cloud_monitoring
from ..shared.error_tracker import error_tracker, ErrorCategory
from ..shared.config import config

logger = get_logger(__name__)


class ReconciliationStatus(Enum):
    """Reconciliation status levels."""
    MATCHED = "matched"
    VARIANCE_ACCEPTABLE = "variance_acceptable"
    VARIANCE_WARNING = "variance_warning"
    VARIANCE_CRITICAL = "variance_critical"
    MISSING_DATA = "missing_data"
    DUPLICATE_DATA = "duplicate_data"


@dataclass
class VarianceAnalysis:
    """Detailed variance analysis between calculated and vendor costs."""
    platform: str
    period: str
    calculated_cost: Decimal
    vendor_cost: Decimal
    variance_amount: Decimal
    variance_percentage: float
    status: ReconciliationStatus
    threshold_breached: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconciliationReport:
    """Comprehensive reconciliation report."""
    reconciliation_id: str
    period_start: date
    period_end: date
    total_platforms: int
    matched_platforms: int
    variance_analyses: List[VarianceAnalysis]
    overall_status: ReconciliationStatus
    total_variance_amount: Decimal
    total_variance_percentage: float
    requires_manual_review: bool
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VendorInvoiceReconciliationEngine:
    """Automated reconciliation system for vendor invoice validation."""

    def __init__(self):
        """Initialize reconciliation engine."""
        self.project_id = config.project_id
        self.dataset_id = config.dataset
        self.client = bigquery.Client(project=self.project_id)
        self.context_logger = RequestContextLogger("reconciliation_engine")

        # Reconciliation thresholds
        self.ACCEPTABLE_VARIANCE_PERCENTAGE = 5.0  # 5% acceptable variance
        self.WARNING_VARIANCE_PERCENTAGE = 10.0    # 10% warning threshold
        self.CRITICAL_VARIANCE_PERCENTAGE = 20.0   # 20% critical threshold

        logger.info("Initialized Vendor Invoice Reconciliation Engine", extra={
            "project_id": self.project_id,
            "dataset": self.dataset_id,
            "thresholds": {
                "acceptable": self.ACCEPTABLE_VARIANCE_PERCENTAGE,
                "warning": self.WARNING_VARIANCE_PERCENTAGE,
                "critical": self.CRITICAL_VARIANCE_PERCENTAGE
            }
        })

    def reconcile_monthly_costs(self, target_month: date,
                               vendor_invoices: Dict[str, Decimal]) -> ReconciliationReport:
        """
        Reconcile monthly costs against vendor invoices.

        Args:
            target_month: Month to reconcile (YYYY-MM-01 format)
            vendor_invoices: Dict of platform -> vendor invoice amount

        Returns:
            Comprehensive reconciliation report
        """
        reconciliation_id = f"recon_{target_month.strftime('%Y_%m')}_{int(time.time())}"

        self.context_logger.log_operation_start("reconcile_monthly_costs",
                                               reconciliation_id=reconciliation_id,
                                               target_month=str(target_month))

        try:
            # Get period boundaries
            period_start = target_month.replace(day=1)
            next_month = period_start.replace(month=period_start.month + 1) if period_start.month < 12 else period_start.replace(year=period_start.year + 1, month=1)
            period_end = next_month - timedelta(days=1)

            # Get calculated costs from BigQuery
            calculated_costs = self._get_calculated_monthly_costs(period_start, period_end)

            # Perform variance analysis
            variance_analyses = []
            total_calculated = Decimal('0.00')
            total_vendor = Decimal('0.00')

            for platform, vendor_cost in vendor_invoices.items():
                calculated_cost = calculated_costs.get(platform, Decimal('0.00'))

                variance_analysis = self._analyze_cost_variance(
                    platform,
                    period_start.strftime('%Y-%m'),
                    calculated_cost,
                    vendor_cost
                )

                variance_analyses.append(variance_analysis)
                total_calculated += calculated_cost
                total_vendor += vendor_cost

            # Calculate overall variance
            overall_variance_amount = total_calculated - total_vendor
            overall_variance_percentage = float((overall_variance_amount / total_vendor) * 100) if total_vendor > 0 else 0.0

            # Determine overall status
            overall_status = self._determine_overall_status(variance_analyses)

            # Check if manual review is required
            requires_manual_review = (
                overall_status in [ReconciliationStatus.VARIANCE_CRITICAL, ReconciliationStatus.MISSING_DATA] or
                abs(overall_variance_percentage) > self.WARNING_VARIANCE_PERCENTAGE
            )

            # Create reconciliation report
            report = ReconciliationReport(
                reconciliation_id=reconciliation_id,
                period_start=period_start,
                period_end=period_end,
                total_platforms=len(vendor_invoices),
                matched_platforms=len([v for v in variance_analyses if v.status == ReconciliationStatus.MATCHED]),
                variance_analyses=variance_analyses,
                overall_status=overall_status,
                total_variance_amount=overall_variance_amount,
                total_variance_percentage=overall_variance_percentage,
                requires_manual_review=requires_manual_review,
                metadata={
                    "total_calculated": float(total_calculated),
                    "total_vendor": float(total_vendor),
                    "platforms_reconciled": list(vendor_invoices.keys())
                }
            )

            # Record metrics to Cloud Monitoring
            self._record_reconciliation_metrics(report)

            # Log reconciliation completion
            self.context_logger.log_operation_complete("reconcile_monthly_costs",
                                                     reconciliation_id=reconciliation_id,
                                                     overall_status=overall_status.value,
                                                     variance_percentage=overall_variance_percentage,
                                                     manual_review_required=requires_manual_review)

            return report

        except Exception as e:
            error_tracker.track_exception(e, "reconciliation_engine", "vendor_reconciliation")
            self.context_logger.log_operation_error("reconcile_monthly_costs", error=e)
            raise

    def _get_calculated_monthly_costs(self, period_start: date, period_end: date) -> Dict[str, Decimal]:
        """Get calculated costs from BigQuery for the specified period."""
        try:
            query = f"""
            SELECT
                platform,
                SUM(cost_usd) as total_cost
            FROM `{self.project_id}.{self.dataset_id}.fct_cost_daily`
            WHERE DATE(cost_date) BETWEEN '{period_start}' AND '{period_end}'
            GROUP BY platform
            """

            query_job = self.client.query(query)
            results = query_job.result()

            calculated_costs = {}
            for row in results:
                platform = row.platform
                total_cost = Decimal(str(row.total_cost)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                calculated_costs[platform] = total_cost

            logger.debug("Retrieved calculated monthly costs", extra={
                "period_start": str(period_start),
                "period_end": str(period_end),
                "platforms": list(calculated_costs.keys()),
                "total_calculated": float(sum(calculated_costs.values()))
            })

            return calculated_costs

        except GoogleAPIError as e:
            logger.error("Failed to retrieve calculated costs from BigQuery", extra={"error": str(e)})
            raise

    def _analyze_cost_variance(self, platform: str, period: str,
                              calculated_cost: Decimal, vendor_cost: Decimal) -> VarianceAnalysis:
        """Analyze variance between calculated and vendor costs."""
        # Convert to Decimal for precise calculations
        vendor_cost_decimal = Decimal(str(vendor_cost))

        # Calculate variance
        variance_amount = calculated_cost - vendor_cost_decimal
        variance_percentage = float((variance_amount / vendor_cost_decimal) * 100) if vendor_cost_decimal > 0 else 0.0

        # Determine status based on variance percentage
        abs_variance = abs(variance_percentage)

        if abs_variance <= self.ACCEPTABLE_VARIANCE_PERCENTAGE:
            status = ReconciliationStatus.MATCHED if abs_variance < 1.0 else ReconciliationStatus.VARIANCE_ACCEPTABLE
        elif abs_variance <= self.WARNING_VARIANCE_PERCENTAGE:
            status = ReconciliationStatus.VARIANCE_WARNING
        else:
            status = ReconciliationStatus.VARIANCE_CRITICAL

        # Check for missing data scenarios
        if calculated_cost == 0 and vendor_cost_decimal > 0:
            status = ReconciliationStatus.MISSING_DATA
        elif calculated_cost > 0 and vendor_cost_decimal == 0:
            status = ReconciliationStatus.DUPLICATE_DATA

        threshold_breached = abs_variance > self.ACCEPTABLE_VARIANCE_PERCENTAGE

        return VarianceAnalysis(
            platform=platform,
            period=period,
            calculated_cost=calculated_cost,
            vendor_cost=vendor_cost_decimal,
            variance_amount=variance_amount,
            variance_percentage=variance_percentage,
            status=status,
            threshold_breached=threshold_breached,
            metadata={
                "acceptable_threshold": self.ACCEPTABLE_VARIANCE_PERCENTAGE,
                "warning_threshold": self.WARNING_VARIANCE_PERCENTAGE,
                "critical_threshold": self.CRITICAL_VARIANCE_PERCENTAGE
            }
        )

    def _determine_overall_status(self, variance_analyses: List[VarianceAnalysis]) -> ReconciliationStatus:
        """Determine overall reconciliation status from individual analyses."""
        if not variance_analyses:
            return ReconciliationStatus.MISSING_DATA

        status_counts = {}
        for analysis in variance_analyses:
            status = analysis.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # Priority order: CRITICAL > MISSING_DATA > WARNING > ACCEPTABLE > MATCHED
        if status_counts.get(ReconciliationStatus.VARIANCE_CRITICAL, 0) > 0:
            return ReconciliationStatus.VARIANCE_CRITICAL
        elif status_counts.get(ReconciliationStatus.MISSING_DATA, 0) > 0:
            return ReconciliationStatus.MISSING_DATA
        elif status_counts.get(ReconciliationStatus.DUPLICATE_DATA, 0) > 0:
            return ReconciliationStatus.DUPLICATE_DATA
        elif status_counts.get(ReconciliationStatus.VARIANCE_WARNING, 0) > 0:
            return ReconciliationStatus.VARIANCE_WARNING
        elif status_counts.get(ReconciliationStatus.VARIANCE_ACCEPTABLE, 0) > 0:
            return ReconciliationStatus.VARIANCE_ACCEPTABLE
        else:
            return ReconciliationStatus.MATCHED

    def _record_reconciliation_metrics(self, report: ReconciliationReport) -> None:
        """Record reconciliation metrics to Cloud Monitoring."""
        try:
            monitoring_client = get_cloud_monitoring()

            # Record overall variance percentage
            monitoring_client.record_cost_variance(
                abs(report.total_variance_percentage),
                "all_platforms",
                "monthly_reconciliation"
            )

            # Record platform-specific variances
            for analysis in report.variance_analyses:
                monitoring_client.record_cost_variance(
                    abs(analysis.variance_percentage),
                    analysis.platform,
                    "monthly_reconciliation"
                )

            # Record reconciliation success metrics
            success_rate = (report.matched_platforms / max(1, report.total_platforms)) * 100
            monitoring_client.record_pipeline_health(success_rate, "vendor_reconciliation")

            logger.debug("Recorded reconciliation metrics to Cloud Monitoring", extra={
                "reconciliation_id": report.reconciliation_id,
                "success_rate": success_rate,
                "overall_variance": report.total_variance_percentage
            })

        except Exception as e:
            logger.warning("Failed to record reconciliation metrics", extra={"error": str(e)})

    def generate_reconciliation_report_summary(self, report: ReconciliationReport) -> str:
        """Generate human-readable reconciliation report summary."""
        summary_lines = [
            f"=== VENDOR INVOICE RECONCILIATION REPORT ===",
            f"Period: {report.period_start} to {report.period_end}",
            f"Reconciliation ID: {report.reconciliation_id}",
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"OVERALL STATUS: {report.overall_status.value.upper()}",
            f"Total Variance: ${report.total_variance_amount:.2f} ({report.total_variance_percentage:+.2f}%)",
            f"Manual Review Required: {'YES' if report.requires_manual_review else 'NO'}",
            f"",
            f"PLATFORM BREAKDOWN ({report.matched_platforms}/{report.total_platforms} matched):"
        ]

        for analysis in report.variance_analyses:
            status_emoji = {
                ReconciliationStatus.MATCHED: "✅",
                ReconciliationStatus.VARIANCE_ACCEPTABLE: "✅",
                ReconciliationStatus.VARIANCE_WARNING: "⚠️",
                ReconciliationStatus.VARIANCE_CRITICAL: "❌",
                ReconciliationStatus.MISSING_DATA: "❓",
                ReconciliationStatus.DUPLICATE_DATA: "🔄"
            }.get(analysis.status, "❓")

            summary_lines.append(
                f"  {status_emoji} {analysis.platform}: "
                f"Calculated=${analysis.calculated_cost:.2f}, "
                f"Vendor=${analysis.vendor_cost:.2f}, "
                f"Variance={analysis.variance_percentage:+.2f}%"
            )

        # Add recommendations
        summary_lines.extend([
            f"",
            f"RECOMMENDATIONS:"
        ])

        critical_variances = [a for a in report.variance_analyses if a.status == ReconciliationStatus.VARIANCE_CRITICAL]
        if critical_variances:
            summary_lines.append(f"  🚨 IMMEDIATE ACTION: Review {len(critical_variances)} critical variance(s)")

        warning_variances = [a for a in report.variance_analyses if a.status == ReconciliationStatus.VARIANCE_WARNING]
        if warning_variances:
            summary_lines.append(f"  ⚠️  INVESTIGATE: {len(warning_variances)} platform(s) with warning variance")

        missing_data = [a for a in report.variance_analyses if a.status == ReconciliationStatus.MISSING_DATA]
        if missing_data:
            summary_lines.append(f"  ❓ DATA ISSUE: {len(missing_data)} platform(s) with missing cost data")

        if report.overall_status == ReconciliationStatus.MATCHED:
            summary_lines.append(f"  ✅ ALL GOOD: No action required - all variances within acceptable limits")

        return "\n".join(summary_lines)

    def validate_vendor_invoice_data(self, vendor_invoices: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate vendor invoice data format and completeness."""
        validation_issues = []

        for platform, invoice_data in vendor_invoices.items():
            # Validate platform name
            if not platform or not isinstance(platform, str):
                validation_issues.append({
                    "level": "error",
                    "code": "INVALID_PLATFORM",
                    "message": f"Invalid platform identifier: {platform}",
                    "platform": platform
                })
                continue

            # Validate cost amount
            try:
                cost_amount = Decimal(str(invoice_data))
                if cost_amount < 0:
                    validation_issues.append({
                        "level": "error",
                        "code": "NEGATIVE_INVOICE_AMOUNT",
                        "message": f"Negative invoice amount for {platform}: ${cost_amount}",
                        "platform": platform,
                        "amount": float(cost_amount)
                    })
            except (ValueError, TypeError, Exception):
                validation_issues.append({
                    "level": "error",
                    "code": "INVALID_INVOICE_AMOUNT",
                    "message": f"Invalid invoice amount format for {platform}: {invoice_data}",
                    "platform": platform,
                    "raw_value": str(invoice_data)
                })

        return validation_issues

    def create_variance_alert(self, variance_analysis: VarianceAnalysis) -> Dict[str, Any]:
        """Create alert data for variance threshold breaches."""
        if not variance_analysis.threshold_breached:
            return {}

        severity = "info"
        if variance_analysis.status == ReconciliationStatus.VARIANCE_CRITICAL:
            severity = "critical"
        elif variance_analysis.status == ReconciliationStatus.VARIANCE_WARNING:
            severity = "warning"

        alert_data = {
            "alert_type": "vendor_reconciliation_variance",
            "severity": severity,
            "platform": variance_analysis.platform,
            "period": variance_analysis.period,
            "variance_percentage": variance_analysis.variance_percentage,
            "variance_amount": float(variance_analysis.variance_amount),
            "calculated_cost": float(variance_analysis.calculated_cost),
            "vendor_cost": float(variance_analysis.vendor_cost),
            "threshold_breached": variance_analysis.threshold_breached,
            "message": f"Cost variance alert for {variance_analysis.platform}: "
                      f"{variance_analysis.variance_percentage:+.2f}% variance "
                      f"(${variance_analysis.variance_amount:+.2f})",
            "timestamp": datetime.now().isoformat(),
            "requires_action": variance_analysis.status in [
                ReconciliationStatus.VARIANCE_CRITICAL,
                ReconciliationStatus.MISSING_DATA
            ]
        }

        return alert_data

    def get_historical_variance_trends(self, platform: str, months_back: int = 6) -> Dict[str, Any]:
        """Get historical variance trends for a platform."""
        try:
            # This would require a historical reconciliation results table
            # For now, return basic trend analysis structure

            trend_analysis = {
                "platform": platform,
                "analysis_period_months": months_back,
                "trend_direction": "stable",  # Would be calculated from historical data
                "average_variance_percentage": 0.0,
                "variance_volatility": 0.0,
                "reconciliation_count": 0,
                "last_analysis_date": datetime.now().isoformat(),
                "recommendations": []
            }

            return trend_analysis

        except Exception as e:
            logger.warning(f"Failed to get historical variance trends for {platform}", extra={"error": str(e)})
            return {}

    def schedule_monthly_reconciliation(self, target_month: date) -> bool:
        """Schedule automated monthly reconciliation job."""
        try:
            # This would integrate with Cloud Scheduler
            # For now, log the scheduling request

            self.context_logger.info("Scheduled monthly reconciliation",
                                   target_month=str(target_month),
                                   scheduled_at=datetime.now().isoformat())

            return True

        except Exception as e:
            error_tracker.track_exception(e, "reconciliation_engine", "scheduling")
            logger.error("Failed to schedule monthly reconciliation", extra={"error": str(e)})
            return False


# Global instance - lazy initialization
reconciliation_engine = None

def get_reconciliation_engine():
    """Get or create reconciliation engine instance."""
    global reconciliation_engine
    if reconciliation_engine is None:
        reconciliation_engine = VendorInvoiceReconciliationEngine()
    return reconciliation_engine