"""Error tracking and categorization system for AI Usage Analytics Dashboard."""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

from .logging_setup import get_logger, RequestContextLogger
from .cloud_monitoring import cloud_monitoring
from .config import config

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Error category classifications."""
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    CONFIGURATION_ERROR = "configuration_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    DATA_QUALITY_ERROR = "data_quality_error"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorEvent:
    """Structured error event for tracking."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    error_type: str
    message: str
    platform: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    manual_intervention_required: bool = False
    resolution_status: str = "unresolved"  # unresolved, resolved, ignored
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def from_exception(cls, error: Exception, component: str, platform: str = None,
                      request_id: str = None, retry_count: int = 0) -> 'ErrorEvent':
        """Create ErrorEvent from an exception."""
        error_type = type(error).__name__
        message = str(error)

        # Categorize error
        category = cls._categorize_error(error_type, message, component)
        severity = cls._determine_severity(error_type, message, retry_count)

        # Generate unique error ID based on content
        error_content = f"{component}:{error_type}:{message}"
        error_id = hashlib.md5(error_content.encode()).hexdigest()[:12]

        return cls(
            error_id=error_id,
            category=category,
            severity=severity,
            component=component,
            error_type=error_type,
            message=message,
            platform=platform,
            request_id=request_id,
            retry_count=retry_count,
            manual_intervention_required=severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        )

    @staticmethod
    def _categorize_error(error_type: str, message: str, component: str) -> ErrorCategory:
        """Categorize error based on type, message, and component."""
        message_lower = message.lower()
        error_type_lower = error_type.lower()

        # API-related errors
        if any(keyword in error_type_lower for keyword in ["api", "http", "request", "connection"]):
            return ErrorCategory.API_ERROR

        if any(keyword in message_lower for keyword in ["rate limit", "401", "403", "timeout"]):
            return ErrorCategory.API_ERROR

        # Validation errors
        if any(keyword in error_type_lower for keyword in ["validation", "schema", "value"]):
            return ErrorCategory.VALIDATION_ERROR

        if any(keyword in message_lower for keyword in ["invalid", "missing", "required", "format"]):
            return ErrorCategory.VALIDATION_ERROR

        # Infrastructure errors
        if any(keyword in error_type_lower for keyword in ["bigquery", "cloud", "gcp"]):
            return ErrorCategory.INFRASTRUCTURE_ERROR

        if any(keyword in message_lower for keyword in ["credentials", "permission", "quota"]):
            return ErrorCategory.INFRASTRUCTURE_ERROR

        # Configuration errors
        if any(keyword in message_lower for keyword in ["config", "secret", "environment"]):
            return ErrorCategory.CONFIGURATION_ERROR

        # Processing errors (default for data processing components)
        if component in ["transformer", "attribution", "orchestrator"]:
            return ErrorCategory.PROCESSING_ERROR

        # Data quality errors
        if any(keyword in message_lower for keyword in ["quality", "duplicate", "corrupt"]):
            return ErrorCategory.DATA_QUALITY_ERROR

        # Default to processing error
        return ErrorCategory.PROCESSING_ERROR

    @staticmethod
    def _determine_severity(error_type: str, message: str, retry_count: int) -> ErrorSeverity:
        """Determine error severity."""
        message_lower = message.lower()

        # Critical errors that stop the pipeline
        if any(keyword in message_lower for keyword in ["critical", "fatal", "abort"]):
            return ErrorSeverity.CRITICAL

        if retry_count > 3:
            return ErrorSeverity.CRITICAL

        # High severity errors
        if any(keyword in message_lower for keyword in ["auth", "permission", "credential"]):
            return ErrorSeverity.HIGH

        if retry_count > 1:
            return ErrorSeverity.HIGH

        # Medium severity errors
        if any(keyword in message_lower for keyword in ["timeout", "rate limit", "quota"]):
            return ErrorSeverity.MEDIUM

        # Default to low
        return ErrorSeverity.LOW


class ErrorTracker:
    """Tracks and analyzes errors across the pipeline."""

    def __init__(self):
        """Initialize error tracker."""
        self.errors: List[ErrorEvent] = []
        self.context_logger = RequestContextLogger("error_tracker")

        logger.info("Initialized Error Tracker")

    def track_error(self, error_event: ErrorEvent) -> None:
        """Track a new error event."""
        self.errors.append(error_event)

        # Record to Cloud Monitoring
        try:
            error_rate = 100.0  # Single error = 100% for this event
            cloud_monitoring.record_error_rate(
                error_event.platform or "unknown",
                error_rate,
                error_event.category.value
            )
        except Exception as e:
            logger.warning(f"Failed to record error to Cloud Monitoring: {e}")

        # Log structured error
        self.context_logger.error(
            f"Error tracked: {error_event.error_type}",
            error_id=error_event.error_id,
            category=error_event.category.value,
            severity=error_event.severity.value,
            component=error_event.component,
            platform=error_event.platform,
            retry_count=error_event.retry_count,
            manual_intervention=error_event.manual_intervention_required
        )

    def track_exception(self, error: Exception, component: str, platform: str = None,
                       request_id: str = None, retry_count: int = 0) -> ErrorEvent:
        """Track an exception and return the error event."""
        error_event = ErrorEvent.from_exception(
            error, component, platform, request_id, retry_count
        )
        self.track_error(error_event)
        return error_event

    def get_error_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]

        # Group by category
        category_counts = {}
        severity_counts = {}
        component_counts = {}

        for error in recent_errors:
            # Count by category
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

            # Count by severity
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Count by component
            component = error.component
            component_counts[component] = component_counts.get(component, 0) + 1

        # Calculate metrics
        total_errors = len(recent_errors)
        manual_intervention_count = sum(1 for e in recent_errors if e.manual_intervention_required)
        avg_retry_count = sum(e.retry_count for e in recent_errors) / max(1, total_errors)

        summary = {
            "time_period_hours": hours_back,
            "total_errors": total_errors,
            "manual_intervention_required": manual_intervention_count,
            "average_retry_count": avg_retry_count,
            "error_rate_per_hour": total_errors / hours_back,
            "category_breakdown": category_counts,
            "severity_breakdown": severity_counts,
            "component_breakdown": component_counts,
            "recent_critical_errors": [
                {
                    "error_id": e.error_id,
                    "component": e.component,
                    "message": e.message,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in recent_errors
                if e.severity == ErrorSeverity.CRITICAL
            ][-10:],  # Last 10 critical errors
            "generated_at": datetime.now().isoformat()
        }

        return summary

    def get_error_trends(self, days_back: int = 7) -> Dict[str, Any]:
        """Analyze error trends over time."""
        cutoff_time = datetime.now() - timedelta(days=days_back)
        recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]

        # Group by day and category
        daily_trends = {}
        for error in recent_errors:
            day = error.timestamp.date().isoformat()
            category = error.category.value

            if day not in daily_trends:
                daily_trends[day] = {}
            daily_trends[day][category] = daily_trends[day].get(category, 0) + 1

        # Calculate trend metrics
        total_errors_by_day = [sum(day_errors.values()) for day_errors in daily_trends.values()]

        trend_analysis = {
            "period_days": days_back,
            "daily_error_counts": daily_trends,
            "total_errors": len(recent_errors),
            "average_errors_per_day": len(recent_errors) / days_back,
            "peak_error_day": max(total_errors_by_day) if total_errors_by_day else 0,
            "trend_direction": self._calculate_trend_direction(total_errors_by_day),
            "most_common_category": max(
                (error.category.value for error in recent_errors),
                key=lambda x: sum(1 for e in recent_errors if e.category.value == x),
                default="none"
            ) if recent_errors else "none"
        }

        return trend_analysis

    def _calculate_trend_direction(self, daily_counts: List[int]) -> str:
        """Calculate if errors are trending up, down, or stable."""
        if len(daily_counts) < 3:
            return "insufficient_data"

        # Compare first half vs second half
        mid_point = len(daily_counts) // 2
        first_half_avg = sum(daily_counts[:mid_point]) / mid_point
        second_half_avg = sum(daily_counts[mid_point:]) / (len(daily_counts) - mid_point)

        if second_half_avg > first_half_avg * 1.2:
            return "increasing"
        elif second_half_avg < first_half_avg * 0.8:
            return "decreasing"
        else:
            return "stable"


# Global instance
error_tracker = ErrorTracker()