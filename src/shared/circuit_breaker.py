"""Circuit breaker pattern implementation for AI Usage Analytics Dashboard."""

import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from functools import wraps

from .logging_setup import get_logger, RequestContextLogger
from .cloud_monitoring import get_cloud_monitoring
from .error_tracker import error_tracker, ErrorCategory

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Circuit tripped, fail fast
    HALF_OPEN = "half_open" # Testing recovery


class FailureType(Enum):
    """Types of failures for intelligent classification."""
    TRANSIENT = "transient"     # Temporary, should retry
    PERMANENT = "permanent"     # Don't retry
    RATE_LIMIT = "rate_limit"   # Special handling
    TIMEOUT = "timeout"         # Network/latency issue


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    name: str
    failure_threshold: int = 5           # Failures to trigger OPEN
    recovery_timeout_seconds: int = 60   # Seconds before HALF_OPEN attempt
    success_threshold: int = 3           # Successes to return to CLOSED
    request_timeout_seconds: int = 30    # Individual request timeout
    half_open_max_calls: int = 5         # Max calls in HALF_OPEN state
    failure_rate_threshold: float = 0.5  # 50% failure rate to trip circuit


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker performance metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0
    total_recovery_time_seconds: float = 0.0


class CircuitBreaker:
    """Circuit breaker implementation with intelligent failure handling."""

    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker with configuration."""
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.state_changed_at = datetime.now()
        self.half_open_calls = 0
        self._lock = threading.RLock()

        self.context_logger = RequestContextLogger("circuit_breaker", operation=f"manage_{config.name}")

        logger.info(f"Initialized circuit breaker: {config.name}", extra={
            "circuit_name": config.name,
            "failure_threshold": config.failure_threshold,
            "recovery_timeout": config.recovery_timeout_seconds
        })

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function call through circuit breaker."""
        with self._lock:
            # Check if circuit should allow the call
            if not self._can_execute():
                self._record_call_blocked()
                raise CircuitBreakerOpenException(
                    f"Circuit breaker {self.config.name} is OPEN. "
                    f"Try again in {self._time_until_retry():.0f} seconds."
                )

            # Execute the call
            call_start_time = time.time()

            try:
                result = func(*args, **kwargs)
                self._record_success(call_start_time)
                return result

            except Exception as e:
                self._record_failure(e, call_start_time)
                raise

    def _can_execute(self) -> bool:
        """Determine if circuit should allow execution."""
        if self.state == CircuitState.CLOSED:
            return True

        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_reset():
                self._transition_to_half_open()
                return True
            return False

        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self.half_open_calls < self.config.half_open_max_calls

        return False

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        time_since_opened = (datetime.now() - self.state_changed_at).total_seconds()
        return time_since_opened >= self.config.recovery_timeout_seconds

    def _time_until_retry(self) -> float:
        """Calculate seconds until retry is allowed."""
        if self.state != CircuitState.OPEN:
            return 0.0

        time_since_opened = (datetime.now() - self.state_changed_at).total_seconds()
        return max(0, self.config.recovery_timeout_seconds - time_since_opened)

    def _record_success(self, call_start_time: float) -> None:
        """Record successful call and update circuit state."""
        call_duration = time.time() - call_start_time

        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.current_consecutive_successes += 1
        self.metrics.current_consecutive_failures = 0
        self.metrics.last_success_time = datetime.now()

        # State transitions based on success
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.metrics.current_consecutive_successes >= self.config.success_threshold:
                self._transition_to_closed()

        self.context_logger.debug(f"Circuit breaker call succeeded",
                                circuit_name=self.config.name,
                                state=self.state.value,
                                call_duration_ms=call_duration * 1000,
                                consecutive_successes=self.metrics.current_consecutive_successes)

        # Record metrics to monitoring
        self._record_circuit_metrics()

    def _record_failure(self, error: Exception, call_start_time: float) -> None:
        """Record failed call and update circuit state."""
        call_duration = time.time() - call_start_time
        failure_type = self._classify_failure(error)

        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.current_consecutive_failures += 1
        self.metrics.current_consecutive_successes = 0
        self.metrics.last_failure_time = datetime.now()

        # Only count certain failures toward circuit opening
        if failure_type in [FailureType.TRANSIENT, FailureType.TIMEOUT]:
            # Check if should transition to OPEN
            if (self.state == CircuitState.CLOSED and
                self.metrics.current_consecutive_failures >= self.config.failure_threshold):
                self._transition_to_open()

            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open returns to open
                self._transition_to_open()

        # Track error
        error_tracker.track_exception(error, f"circuit_breaker_{self.config.name}")

        self.context_logger.warning(f"Circuit breaker call failed",
                                  circuit_name=self.config.name,
                                  state=self.state.value,
                                  failure_type=failure_type.value,
                                  call_duration_ms=call_duration * 1000,
                                  consecutive_failures=self.metrics.current_consecutive_failures,
                                  error_type=type(error).__name__)

        # Record metrics to monitoring
        self._record_circuit_metrics()

    def _classify_failure(self, error: Exception) -> FailureType:
        """Classify failure type for intelligent handling."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Rate limiting
        if "429" in error_str or "rate limit" in error_str:
            return FailureType.RATE_LIMIT

        # Timeouts
        if "timeout" in error_str or "timeout" in error_type:
            return FailureType.TIMEOUT

        # Permanent errors
        if any(code in error_str for code in ["400", "401", "403", "404"]):
            return FailureType.PERMANENT

        # Transient errors (default)
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return FailureType.TRANSIENT

        # Default to transient for unknown errors
        return FailureType.TRANSIENT

    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.state_changed_at = datetime.now()
        self.half_open_calls = 0
        self.metrics.circuit_opened_count += 1

        self.context_logger.warning(f"Circuit breaker opened",
                                  circuit_name=self.config.name,
                                  previous_state=old_state.value,
                                  consecutive_failures=self.metrics.current_consecutive_failures,
                                  recovery_timeout=self.config.recovery_timeout_seconds)

    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.state_changed_at = datetime.now()
        self.half_open_calls = 0

        self.context_logger.info(f"Circuit breaker attempting recovery",
                               circuit_name=self.config.name,
                               previous_state=old_state.value,
                               recovery_attempt_time=self.state_changed_at.isoformat())

    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        old_state = self.state
        recovery_time = (datetime.now() - self.state_changed_at).total_seconds()

        self.state = CircuitState.CLOSED
        self.state_changed_at = datetime.now()
        self.half_open_calls = 0
        self.metrics.total_recovery_time_seconds += recovery_time

        self.context_logger.info(f"Circuit breaker recovered",
                               circuit_name=self.config.name,
                               previous_state=old_state.value,
                               recovery_time_seconds=recovery_time,
                               consecutive_successes=self.metrics.current_consecutive_successes)

    def _record_call_blocked(self) -> None:
        """Record when a call is blocked by open circuit."""
        self.context_logger.debug(f"Circuit breaker blocked call",
                                circuit_name=self.config.name,
                                state=self.state.value,
                                time_until_retry=self._time_until_retry())

    def _record_circuit_metrics(self) -> None:
        """Record circuit breaker metrics to Cloud Monitoring."""
        try:
            monitoring_client = get_cloud_monitoring()

            # Record circuit state as health score
            health_score = 100.0 if self.state == CircuitState.CLOSED else 0.0
            monitoring_client.record_pipeline_health(health_score, f"circuit_breaker_{self.config.name}")

            # Record failure rate
            failure_rate = 0.0
            if self.metrics.total_calls > 0:
                failure_rate = (self.metrics.failed_calls / self.metrics.total_calls) * 100

            monitoring_client.record_error_rate(f"circuit_{self.config.name}", failure_rate, "circuit_breaker")

        except Exception as e:
            logger.warning(f"Failed to record circuit breaker metrics for {self.config.name}", extra={"error": str(e)})

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "state_duration_seconds": (datetime.now() - self.state_changed_at).total_seconds(),
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "successful_calls": self.metrics.successful_calls,
                "failed_calls": self.metrics.failed_calls,
                "failure_rate": (self.metrics.failed_calls / max(1, self.metrics.total_calls)) * 100,
                "consecutive_failures": self.metrics.current_consecutive_failures,
                "consecutive_successes": self.metrics.current_consecutive_successes,
                "circuit_opened_count": self.metrics.circuit_opened_count
            },
            "next_allowed_call": None if self._can_execute() else (
                self.state_changed_at + timedelta(seconds=self.config.recovery_timeout_seconds)
            ).isoformat(),
            "configuration": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout_seconds,
                "success_threshold": self.config.success_threshold
            }
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            old_state = self.state
            self.state = CircuitState.CLOSED
            self.state_changed_at = datetime.now()
            self.half_open_calls = 0
            self.metrics.current_consecutive_failures = 0

            self.context_logger.info(f"Circuit breaker manually reset",
                                   circuit_name=self.config.name,
                                   previous_state=old_state.value)


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different services."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.context_logger = RequestContextLogger("circuit_breaker_manager")

        # Create default circuit breakers for main services
        self._create_default_circuit_breakers()

        logger.info("Initialized Circuit Breaker Manager", extra={
            "circuit_breakers_count": len(self.circuit_breakers)
        })

    def _create_default_circuit_breakers(self) -> None:
        """Create circuit breakers for main external services."""
        # Anthropic API circuit breaker
        anthropic_config = CircuitBreakerConfig(
            name="anthropic_api",
            failure_threshold=5,
            recovery_timeout_seconds=60,
            success_threshold=3,
            request_timeout_seconds=30
        )
        self.circuit_breakers["anthropic_api"] = CircuitBreaker(anthropic_config)

        # Cursor API circuit breaker
        cursor_config = CircuitBreakerConfig(
            name="cursor_api",
            failure_threshold=5,
            recovery_timeout_seconds=60,
            success_threshold=3,
            request_timeout_seconds=30
        )
        self.circuit_breakers["cursor_api"] = CircuitBreaker(cursor_config)

        # Google Sheets API circuit breaker (more tolerant)
        sheets_config = CircuitBreakerConfig(
            name="sheets_api",
            failure_threshold=3,
            recovery_timeout_seconds=30,
            success_threshold=2,
            request_timeout_seconds=15
        )
        self.circuit_breakers["sheets_api"] = CircuitBreaker(sheets_config)

        # BigQuery circuit breaker (critical path, more tolerant)
        bigquery_config = CircuitBreakerConfig(
            name="bigquery",
            failure_threshold=10,
            recovery_timeout_seconds=120,
            success_threshold=5,
            request_timeout_seconds=60
        )
        self.circuit_breakers["bigquery"] = CircuitBreaker(bigquery_config)

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            # Create default circuit breaker for unknown service
            default_config = CircuitBreakerConfig(
                name=service_name,
                failure_threshold=5,
                recovery_timeout_seconds=60
            )
            self.circuit_breakers[service_name] = CircuitBreaker(default_config)

        return self.circuit_breakers[service_name]

    def call_with_circuit_breaker(self, service_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute function call with circuit breaker protection."""
        circuit_breaker = self.get_circuit_breaker(service_name)
        return circuit_breaker.call(func, *args, **kwargs)

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        statuses = {}
        for name, circuit_breaker in self.circuit_breakers.items():
            statuses[name] = circuit_breaker.get_status()

        return statuses

    def reset_circuit_breaker(self, service_name: str) -> bool:
        """Manually reset a specific circuit breaker."""
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name].reset()
            logger.info(f"Reset circuit breaker: {service_name}")
            return True

        logger.warning(f"Circuit breaker not found: {service_name}")
        return False

    def reset_all_circuit_breakers(self) -> Dict[str, bool]:
        """Reset all circuit breakers."""
        results = {}
        for service_name in self.circuit_breakers:
            results[service_name] = self.reset_circuit_breaker(service_name)

        self.context_logger.info("Reset all circuit breakers",
                               circuit_breakers_reset=len(results),
                               successful_resets=sum(results.values()))

        return results

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of all circuit breakers."""
        statuses = self.get_all_statuses()

        healthy_count = len([s for s in statuses.values() if s["state"] == "closed"])
        degraded_count = len([s for s in statuses.values() if s["state"] == "half_open"])
        unhealthy_count = len([s for s in statuses.values() if s["state"] == "open"])

        overall_health = "healthy"
        if unhealthy_count > 0:
            overall_health = "unhealthy"
        elif degraded_count > 0:
            overall_health = "degraded"

        return {
            "overall_health": overall_health,
            "total_circuit_breakers": len(statuses),
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "unhealthy_count": unhealthy_count,
            "circuit_breaker_details": statuses,
            "generated_at": datetime.now().isoformat()
        }


def circuit_breaker(service_name: str):
    """Decorator for applying circuit breaker to functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker_manager.call_with_circuit_breaker(service_name, func, *args, **kwargs)
        return wrapper
    return decorator


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()