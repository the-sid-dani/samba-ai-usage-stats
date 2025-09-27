"""Enhanced retry logic with intelligent failure classification and jitter."""

import time
import random
import functools
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass
from enum import Enum

from .logging_setup import get_logger, RequestContextLogger
from .circuit_breaker import FailureType, CircuitBreakerOpenException

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for enhanced retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter_percentage: float = 0.25  # ±25% random jitter
    retry_budget_seconds: float = 300.0  # 5 minute max total retry time


@dataclass
class RetryAttempt:
    """Record of a single retry attempt."""
    attempt_number: int
    delay_seconds: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None
    failure_type: Optional[FailureType] = None


@dataclass
class RetrySession:
    """Complete retry session record."""
    session_id: str
    function_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    attempts: List[RetryAttempt] = None
    final_success: bool = False
    total_duration_seconds: float = 0.0
    budget_exhausted: bool = False

    def __post_init__(self):
        if self.attempts is None:
            self.attempts = []


class EnhancedRetryHandler:
    """Enhanced retry handler with intelligent failure classification."""

    def __init__(self, config: RetryConfig = None):
        """Initialize enhanced retry handler."""
        self.config = config or RetryConfig()
        self.context_logger = RequestContextLogger("enhanced_retry")

    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with enhanced retry logic."""
        session = RetrySession(
            session_id=f"retry_{int(time.time())}_{random.randint(1000, 9999)}",
            function_name=func.__name__,
            started_at=datetime.now(),
            attempts=[]
        )

        self.context_logger.log_operation_start("retry_with_backoff",
                                               session_id=session.session_id,
                                               function_name=session.function_name,
                                               max_attempts=self.config.max_attempts)

        for attempt_num in range(1, self.config.max_attempts + 1):
            # Check retry budget
            elapsed_time = (datetime.now() - session.started_at).total_seconds()
            if elapsed_time >= self.config.retry_budget_seconds:
                session.budget_exhausted = True
                break

            # Calculate delay with jitter
            delay = self._calculate_delay_with_jitter(attempt_num)

            attempt = RetryAttempt(
                attempt_number=attempt_num,
                delay_seconds=delay,
                started_at=datetime.now()
            )

            try:
                # Apply delay (except for first attempt)
                if attempt_num > 1:
                    time.sleep(delay)

                # Execute function
                result = func(*args, **kwargs)

                # Success!
                attempt.completed_at = datetime.now()
                attempt.success = True
                session.attempts.append(attempt)
                session.final_success = True
                session.completed_at = datetime.now()
                session.total_duration_seconds = (session.completed_at - session.started_at).total_seconds()

                self.context_logger.log_operation_complete("retry_with_backoff",
                                                         session_id=session.session_id,
                                                         attempts_used=attempt_num,
                                                         total_duration=session.total_duration_seconds)

                return result

            except CircuitBreakerOpenException:
                # Circuit breaker is open - don't retry
                attempt.completed_at = datetime.now()
                attempt.success = False
                attempt.error = "Circuit breaker open"
                attempt.failure_type = FailureType.PERMANENT
                session.attempts.append(attempt)
                break

            except Exception as e:
                attempt.completed_at = datetime.now()
                attempt.success = False
                attempt.error = str(e)
                attempt.failure_type = self._classify_failure(e)
                session.attempts.append(attempt)

                # Don't retry permanent failures
                if attempt.failure_type == FailureType.PERMANENT:
                    self.context_logger.warning("Permanent failure detected, stopping retry",
                                               session_id=session.session_id,
                                               attempt_number=attempt_num,
                                               error_type=type(e).__name__)
                    break

                # Log retry attempt
                if attempt_num < self.config.max_attempts:
                    self.context_logger.info("Retry attempt failed, retrying",
                                           session_id=session.session_id,
                                           attempt_number=attempt_num,
                                           next_delay_seconds=delay,
                                           failure_type=attempt.failure_type.value,
                                           error_type=type(e).__name__)

        # All attempts exhausted
        session.completed_at = datetime.now()
        session.total_duration_seconds = (session.completed_at - session.started_at).total_seconds()

        self.context_logger.log_operation_error("retry_with_backoff",
                                               session_id=session.session_id,
                                               attempts_exhausted=len(session.attempts),
                                               budget_exhausted=session.budget_exhausted,
                                               total_duration=session.total_duration_seconds)

        # Raise the last exception
        if session.attempts:
            last_attempt = session.attempts[-1]
            raise Exception(f"Retry exhausted after {len(session.attempts)} attempts. Last error: {last_attempt.error}")
        else:
            raise Exception("Retry budget exhausted before any attempts")

    def _calculate_delay_with_jitter(self, attempt_number: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        # Base exponential backoff
        delay = min(
            self.config.base_delay_seconds * (self.config.exponential_base ** (attempt_number - 1)),
            self.config.max_delay_seconds
        )

        # Add jitter (±25% by default)
        jitter_range = delay * self.config.jitter_percentage
        jitter = random.uniform(-jitter_range, jitter_range)

        return max(0.1, delay + jitter)  # Minimum 0.1 second delay

    def _classify_failure(self, error: Exception) -> FailureType:
        """Classify failure type for retry decision."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Rate limiting - special handling
        if "429" in error_str or "rate limit" in error_str:
            return FailureType.RATE_LIMIT

        # Timeouts - usually transient
        if "timeout" in error_str or "timeout" in error_type:
            return FailureType.TIMEOUT

        # Authentication/authorization - permanent
        if any(code in error_str for code in ["401", "403"]):
            return FailureType.PERMANENT

        # Bad request - permanent
        if "400" in error_str or "bad request" in error_str:
            return FailureType.PERMANENT

        # Not found - permanent
        if "404" in error_str or "not found" in error_str:
            return FailureType.PERMANENT

        # Server errors - transient
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return FailureType.TRANSIENT

        # Connection errors - transient
        if any(keyword in error_str for keyword in ["connection", "network", "dns"]):
            return FailureType.TRANSIENT

        # Default to transient for unknown errors
        return FailureType.TRANSIENT


def enhanced_retry(service_name: str = "default", config: RetryConfig = None):
    """Decorator for enhanced retry with circuit breaker integration."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = EnhancedRetryHandler(config)

            # Import here to avoid circular dependency
            from .circuit_breaker import circuit_breaker_manager

            # Combine circuit breaker and retry logic
            def circuit_protected_func(*f_args, **f_kwargs):
                return circuit_breaker_manager.call_with_circuit_breaker(
                    service_name, func, *f_args, **f_kwargs
                )

            return retry_handler.retry_with_backoff(circuit_protected_func, *args, **kwargs)

        return wrapper
    return decorator


# Default retry handler instance
default_retry_handler = EnhancedRetryHandler()