"""
Comprehensive Error Handling and Circuit Breaker System.

Provides robust error handling, automatic recovery, and safety mechanisms
to prevent system failures and protect trading capital.
"""

import asyncio
import traceback
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

from core.logger import get_logger, trading_logger

logger = get_logger("error_handler")


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SystemState(Enum):
    """System operational states."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    SHUTDOWN = "shutdown"


@dataclass
class ErrorRecord:
    """Error record for tracking and analysis."""
    timestamp: datetime
    error_type: str
    message: str
    severity: ErrorSeverity
    component: str
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        # State tracking
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
        logger.info(f"Circuit breaker '{name}' initialized")
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                logger.info(f"Circuit breaker '{self.name}' entering half-open state")
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self):
        """Record successful execution."""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info(f"Circuit breaker '{self.name}' reset to closed state")
    
    def record_failure(self, exception: Exception):
        """Record failed execution."""
        if isinstance(exception, self.expected_exceptions):
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures"
                )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        return datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)


class ErrorManager:
    """Centralized error management system."""
    
    def __init__(self):
        self.error_history: List[ErrorRecord] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.system_state = SystemState.NORMAL
        self.error_counts: Dict[str, int] = {}
        self.last_error_time: Optional[datetime] = None
        
        # Safety thresholds
        self.max_errors_per_hour = 20
        self.critical_error_threshold = 3
        self.system_recovery_time = 300  # 5 minutes
        
        logger.info("Error management system initialized")
    
    def register_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ) -> CircuitBreaker:
        """Register a new circuit breaker."""
        breaker = CircuitBreaker(name, failure_threshold, recovery_timeout, expected_exceptions)
        self.circuit_breakers[name] = breaker
        return breaker
    
    def handle_error(
        self,
        error: Exception,
        component: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Handle an error with appropriate response.
        
        Returns:
            True if system can continue, False if shutdown required
        """
        try:
            # Create error record
            error_record = ErrorRecord(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                message=str(error),
                severity=severity,
                component=component,
                details=context or {}
            )
            
            self.error_history.append(error_record)
            self.last_error_time = datetime.now()
            
            # Update error counts
            error_key = f"{component}:{type(error).__name__}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # Log error with context
            log_level = self._get_log_level(severity)
            logger.log(
                log_level,
                f"Error in {component}: {error}",
                extra={
                    "component": component,
                    "error_type": type(error).__name__,
                    "severity": severity.value,
                    "context": context
                }
            )
            
            # Log to trading system
            trading_logger.log_error(component, error, **context or {})
            
            # Handle based on severity
            return self._handle_by_severity(error_record)
            
        except Exception as handler_error:
            logger.critical(f"Error handler failed: {handler_error}")
            return False
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """Get logging level for severity."""
        level_map = {
            ErrorSeverity.LOW: 20,      # INFO
            ErrorSeverity.MEDIUM: 30,   # WARNING
            ErrorSeverity.HIGH: 40,     # ERROR
            ErrorSeverity.CRITICAL: 50  # CRITICAL
        }
        return level_map.get(severity, 40)
    
    def _handle_by_severity(self, error_record: ErrorRecord) -> bool:
        """Handle error based on severity level."""
        if error_record.severity == ErrorSeverity.CRITICAL:
            self._handle_critical_error(error_record)
            return False
        elif error_record.severity == ErrorSeverity.HIGH:
            return self._handle_high_error(error_record)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            return self._handle_medium_error(error_record)
        else:  # LOW
            return self._handle_low_error(error_record)
    
    def _handle_critical_error(self, error_record: ErrorRecord):
        """Handle critical errors - immediate shutdown."""
        logger.critical(f"CRITICAL ERROR - System shutdown initiated: {error_record.message}")
        self.system_state = SystemState.SHUTDOWN
        
        # Notify about critical error
        self._notify_critical_error(error_record)
    
    def _handle_high_error(self, error_record: ErrorRecord) -> bool:
        """Handle high severity errors."""
        critical_count = sum(
            1 for record in self.error_history[-10:]
            if record.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        )
        
        if critical_count >= self.critical_error_threshold:
            logger.error("Too many high-severity errors - entering emergency mode")
            self.system_state = SystemState.EMERGENCY
            return False
        
        self.system_state = SystemState.DEGRADED
        return True
    
    def _handle_medium_error(self, error_record: ErrorRecord) -> bool:
        """Handle medium severity errors."""
        # Check error rate
        recent_errors = self._get_recent_error_count()
        if recent_errors > self.max_errors_per_hour:
            logger.warning("High error rate detected - entering degraded mode")
            self.system_state = SystemState.DEGRADED
        
        return True
    
    def _handle_low_error(self, error_record: ErrorRecord) -> bool:
        """Handle low severity errors."""
        # Just log and continue
        return True
    
    def _get_recent_error_count(self) -> int:
        """Get error count in the last hour."""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        return sum(
            1 for record in self.error_history
            if record.timestamp > one_hour_ago
        )
    
    def _notify_critical_error(self, error_record: ErrorRecord):
        """Notify external systems about critical errors."""
        # This would integrate with Telegram bot or other notification systems
        pass
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        recent_errors = self._get_recent_error_count()
        
        return {
            "state": self.system_state.value,
            "recent_errors": recent_errors,
            "total_errors": len(self.error_history),
            "circuit_breakers": {
                name: {
                    "state": breaker.state,
                    "failure_count": breaker.failure_count
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "last_error": self.last_error_time.isoformat() if self.last_error_time else None,
            "health_score": self._calculate_health_score()
        }
    
    def _calculate_health_score(self) -> int:
        """Calculate system health score (0-100)."""
        score = 100
        
        # Deduct for recent errors
        recent_errors = self._get_recent_error_count()
        score -= min(recent_errors * 5, 50)
        
        # Deduct for system state
        state_penalties = {
            SystemState.NORMAL: 0,
            SystemState.DEGRADED: 20,
            SystemState.EMERGENCY: 50,
            SystemState.SHUTDOWN: 100
        }
        score -= state_penalties.get(self.system_state, 0)
        
        # Deduct for open circuit breakers
        open_breakers = sum(
            1 for breaker in self.circuit_breakers.values()
            if breaker.state == "open"
        )
        score -= open_breakers * 10
        
        return max(0, score)
    
    def can_continue_trading(self) -> bool:
        """Check if trading can continue safely."""
        return self.system_state in [SystemState.NORMAL, SystemState.DEGRADED]
    
    def reset_system_state(self):
        """Reset system state if recovery conditions are met."""
        if self.system_state == SystemState.EMERGENCY:
            if self._check_recovery_conditions():
                self.system_state = SystemState.DEGRADED
                logger.info("System state reset from emergency to degraded")
        elif self.system_state == SystemState.DEGRADED:
            if self._check_recovery_conditions():
                self.system_state = SystemState.NORMAL
                logger.info("System state reset to normal")
    
    def _check_recovery_conditions(self) -> bool:
        """Check if system can recover to better state."""
        if not self.last_error_time:
            return True
        
        time_since_error = datetime.now() - self.last_error_time
        return time_since_error > timedelta(seconds=self.system_recovery_time)


# Global error manager instance
error_manager = ErrorManager()


def with_circuit_breaker(breaker_name: str, **breaker_kwargs):
    """Decorator to add circuit breaker protection to functions."""
    def decorator(func: Callable) -> Callable:
        # Register circuit breaker if not exists
        if breaker_name not in error_manager.circuit_breakers:
            error_manager.register_circuit_breaker(breaker_name, **breaker_kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = error_manager.circuit_breakers[breaker_name]
            
            if not breaker.can_execute():
                raise Exception(f"Circuit breaker '{breaker_name}' is open")
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure(e)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker = error_manager.circuit_breakers[breaker_name]
            
            if not breaker.can_execute():
                raise Exception(f"Circuit breaker '{breaker_name}' is open")
            
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure(e)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def handle_error(
    component: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    **context
):
    """Decorator for automatic error handling."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                can_continue = error_manager.handle_error(e, component, severity, context)
                if not can_continue:
                    logger.critical(f"System shutdown required due to error in {component}")
                    raise SystemExit(1)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                can_continue = error_manager.handle_error(e, component, severity, context)
                if not can_continue:
                    logger.critical(f"System shutdown required due to error in {component}")
                    raise SystemExit(1)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Health check function
def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status."""
    return error_manager.get_system_health() 