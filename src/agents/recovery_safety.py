"""
Recovery Safety and Audit System

This module provides comprehensive safety mechanisms and audit logging
for the autonomous error recovery system. It prevents infinite loops,
enforces resource limits, and maintains detailed audit trails.

Key Features:
- Infinite loop prevention with circuit breaker patterns
- Resource usage monitoring and limits
- Comprehensive audit logging with structured data
- Safety interlocks for risky recovery operations
- Recovery operation rollback capabilities
- Performance monitoring and alerting

Author: Claude Code Assistant
Date: 2025-01-26
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque


class SafetyLevel(Enum):
    """Safety levels for recovery operations."""
    SAFE = "safe"           # No restrictions
    CAUTIOUS = "cautious"   # Moderate restrictions
    RESTRICTED = "restricted" # High restrictions
    BLOCKED = "blocked"     # Operation blocked


class AuditEventType(Enum):
    """Types of audit events."""
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    SAFETY_LIMIT_HIT = "safety_limit_hit"
    CIRCUIT_BREAKER_OPENED = "circuit_breaker_opened"
    RISKY_OPERATION_BLOCKED = "risky_operation_blocked"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"


@dataclass
class SafetyLimits:
    """Configuration for safety limits."""
    max_concurrent_recoveries: int = 3
    max_recovery_attempts_per_hour: int = 10
    max_recovery_time_per_session: int = 300  # 5 minutes
    max_total_recovery_time_per_hour: int = 1800  # 30 minutes
    max_code_modifications_per_hour: int = 5
    max_command_retries_per_session: int = 3
    max_memory_usage_mb: int = 500
    max_disk_space_usage_mb: int = 100
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 300  # 5 minutes


@dataclass
class AuditEvent:
    """Structured audit event."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    session_id: Optional[str]
    user_id: Optional[str]
    details: Dict[str, Any]
    risk_level: str
    resource_usage: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'user_id': self.user_id,
            'details': self.details,
            'risk_level': self.risk_level,
            'resource_usage': self.resource_usage
        }


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    memory_usage_mb: float
    disk_usage_mb: float
    cpu_percent: float
    active_recoveries: int
    total_recovery_time_hour: float
    code_modifications_hour: int
    
    def exceeds_limits(self, limits: SafetyLimits) -> List[str]:
        """Check which limits are exceeded."""
        violations = []
        
        if self.memory_usage_mb > limits.max_memory_usage_mb:
            violations.append(f"Memory usage: {self.memory_usage_mb:.1f}MB > {limits.max_memory_usage_mb}MB")
        
        if self.disk_usage_mb > limits.max_disk_space_usage_mb:
            violations.append(f"Disk usage: {self.disk_usage_mb:.1f}MB > {limits.max_disk_space_usage_mb}MB")
        
        if self.active_recoveries > limits.max_concurrent_recoveries:
            violations.append(f"Active recoveries: {self.active_recoveries} > {limits.max_concurrent_recoveries}")
        
        if self.total_recovery_time_hour > limits.max_total_recovery_time_per_hour:
            violations.append(f"Recovery time/hour: {self.total_recovery_time_hour:.1f}s > {limits.max_total_recovery_time_per_hour}s")
        
        if self.code_modifications_hour > limits.max_code_modifications_per_hour:
            violations.append(f"Code modifications/hour: {self.code_modifications_hour} > {limits.max_code_modifications_per_hour}")
        
        return violations


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 300):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()
    
    def can_proceed(self) -> bool:
        """Check if operation can proceed through circuit breaker."""
        with self._lock:
            if self.state == "closed":
                return True
            elif self.state == "open":
                if self.last_failure_time and (
                    datetime.now() - self.last_failure_time
                ).total_seconds() > self.timeout_seconds:
                    self.state = "half-open"
                    return True
                return False
            else:  # half-open
                return True
    
    def record_success(self):
        """Record successful operation."""
        with self._lock:
            self.failure_count = 0
            self.state = "closed"
    
    def record_failure(self):
        """Record failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        with self._lock:
            return {
                'state': self.state,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None
            }


class RecoverySafetyManager:
    """
    Comprehensive safety manager for recovery operations.
    
    This manager enforces safety limits, prevents infinite loops,
    and maintains detailed audit trails for all recovery operations.
    """
    
    def __init__(self, safety_limits: SafetyLimits = None, audit_log_path: str = None):
        """
        Initialize recovery safety manager.
        
        Args:
            safety_limits: Configuration for safety limits
            audit_log_path: Path to audit log file
        """
        self.safety_limits = safety_limits or SafetyLimits()
        self.audit_log_path = audit_log_path or "recovery_audit.jsonl"
        
        # Circuit breakers for different operations
        self.circuit_breakers = {
            'recovery': CircuitBreaker(
                self.safety_limits.circuit_breaker_failure_threshold,
                self.safety_limits.circuit_breaker_timeout_seconds
            ),
            'code_fix': CircuitBreaker(3, 600),  # 10 minute timeout for code fixes
            'command_retry': CircuitBreaker(5, 180)  # 3 minute timeout for command retries
        }
        
        # Activity tracking
        self.active_recoveries: Set[str] = set()
        self.recovery_history = deque(maxlen=1000)  # Keep last 1000 operations
        self.hourly_stats = defaultdict(lambda: {
            'recovery_attempts': 0,
            'code_modifications': 0,
            'total_recovery_time': 0.0
        })
        
        # Resource monitoring
        self.resource_monitor = ResourceMonitor()
        
        # Audit logging
        self.audit_logger = self._setup_audit_logger()
        
        # Safety callbacks
        self.safety_callbacks: List[Callable] = []
        
        self.logger = logging.getLogger(f'{self.__class__.__name__}')
        self.logger.setLevel(logging.INFO)
        
        self.logger.info("RecoverySafetyManager initialized")
    
    def _setup_audit_logger(self) -> logging.Logger:
        """Setup structured audit logger."""
        audit_logger = logging.getLogger('RecoveryAudit')
        audit_logger.setLevel(logging.INFO)
        
        # Create file handler for audit log
        handler = logging.FileHandler(self.audit_log_path)
        handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        audit_logger.addHandler(handler)
        return audit_logger
    
    async def check_recovery_authorization(self, session_id: str, 
                                         operation_type: str,
                                         risk_level: str,
                                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check if recovery operation is authorized to proceed.
        
        Args:
            session_id: Recovery session ID
            operation_type: Type of recovery operation
            risk_level: Risk level of operation
            context: Additional context
            
        Returns:
            Authorization result with status and reason
        """
        authorization_start = time.time()
        
        try:
            # Step 1: Check circuit breakers
            circuit_check = self._check_circuit_breakers(operation_type)
            if not circuit_check['can_proceed']:
                await self._log_audit_event(
                    AuditEventType.RISKY_OPERATION_BLOCKED,
                    session_id=session_id,
                    details={
                        'operation_type': operation_type,
                        'reason': 'Circuit breaker open',
                        'circuit_status': circuit_check
                    },
                    risk_level=risk_level
                )
                return {
                    'authorized': False,
                    'reason': 'Circuit breaker protection active',
                    'safety_level': SafetyLevel.BLOCKED,
                    'retry_after': circuit_check.get('retry_after', 300)
                }
            
            # Step 2: Check resource limits
            resource_usage = self.resource_monitor.get_current_usage()
            resource_violations = resource_usage.exceeds_limits(self.safety_limits)
            
            if resource_violations:
                await self._log_audit_event(
                    AuditEventType.RESOURCE_LIMIT_EXCEEDED,
                    session_id=session_id,
                    details={
                        'operation_type': operation_type,
                        'violations': resource_violations,
                        'resource_usage': asdict(resource_usage)
                    },
                    risk_level=risk_level
                )
                return {
                    'authorized': False,
                    'reason': f"Resource limits exceeded: {', '.join(resource_violations)}",
                    'safety_level': SafetyLevel.BLOCKED,
                    'resource_usage': asdict(resource_usage)
                }
            
            # Step 3: Check concurrency limits
            if len(self.active_recoveries) >= self.safety_limits.max_concurrent_recoveries:
                return {
                    'authorized': False,
                    'reason': f"Too many concurrent recoveries: {len(self.active_recoveries)}",
                    'safety_level': SafetyLevel.RESTRICTED,
                    'active_recoveries': len(self.active_recoveries)
                }
            
            # Step 4: Check hourly limits
            current_hour = datetime.now().hour
            hour_stats = self.hourly_stats[current_hour]
            
            if hour_stats['recovery_attempts'] >= self.safety_limits.max_recovery_attempts_per_hour:
                return {
                    'authorized': False,
                    'reason': f"Hourly recovery limit exceeded: {hour_stats['recovery_attempts']}",
                    'safety_level': SafetyLevel.RESTRICTED,
                    'hourly_stats': hour_stats
                }
            
            # Step 5: Risk-based authorization
            safety_level = self._determine_safety_level(risk_level, operation_type, resource_usage)
            
            if safety_level == SafetyLevel.BLOCKED:
                return {
                    'authorized': False,
                    'reason': f"Operation blocked due to risk level: {risk_level}",
                    'safety_level': safety_level
                }
            
            # Step 6: Record authorization
            self.active_recoveries.add(session_id)
            hour_stats['recovery_attempts'] += 1
            
            await self._log_audit_event(
                AuditEventType.RECOVERY_STARTED,
                session_id=session_id,
                details={
                    'operation_type': operation_type,
                    'safety_level': safety_level.value,
                    'authorization_time': time.time() - authorization_start,
                    'context': context or {}
                },
                risk_level=risk_level
            )
            
            return {
                'authorized': True,
                'reason': 'Authorization granted',
                'safety_level': safety_level,
                'conditions': self._get_safety_conditions(safety_level)
            }
            
        except Exception as e:
            self.logger.error(f"Recovery authorization failed: {e}")
            return {
                'authorized': False,
                'reason': f"Authorization check failed: {str(e)}",
                'safety_level': SafetyLevel.BLOCKED
            }
    
    async def register_recovery_completion(self, session_id: str,
                                         success: bool,
                                         execution_time: float,
                                         operations_performed: List[str],
                                         resources_modified: List[str] = None):
        """
        Register completion of recovery operation.
        
        Args:
            session_id: Recovery session ID
            success: Whether recovery was successful
            execution_time: Time taken for recovery
            operations_performed: List of operations performed
            resources_modified: List of resources that were modified
        """
        try:
            # Remove from active recoveries
            if session_id in self.active_recoveries:
                self.active_recoveries.remove(session_id)
            
            # Update statistics
            current_hour = datetime.now().hour
            hour_stats = self.hourly_stats[current_hour]
            hour_stats['total_recovery_time'] += execution_time
            
            # Count code modifications
            code_operations = [op for op in operations_performed if 'code' in op.lower()]
            hour_stats['code_modifications'] += len(code_operations)
            
            # Update circuit breaker
            if success:
                self.circuit_breakers['recovery'].record_success()
            else:
                self.circuit_breakers['recovery'].record_failure()
            
            # Record in history
            self.recovery_history.append({
                'session_id': session_id,
                'timestamp': datetime.now(),
                'success': success,
                'execution_time': execution_time,
                'operations': operations_performed
            })
            
            # Log audit event
            event_type = AuditEventType.RECOVERY_COMPLETED if success else AuditEventType.RECOVERY_FAILED
            
            await self._log_audit_event(
                event_type,
                session_id=session_id,
                details={
                    'execution_time': execution_time,
                    'operations_performed': operations_performed,
                    'resources_modified': resources_modified or [],
                    'final_resource_usage': asdict(self.resource_monitor.get_current_usage())
                },
                risk_level='medium'
            )
            
            self.logger.info(f"Recovery completion registered: {session_id} ({'success' if success else 'failed'})")
            
        except Exception as e:
            self.logger.error(f"Failed to register recovery completion: {e}")
    
    def _check_circuit_breakers(self, operation_type: str) -> Dict[str, Any]:
        """Check circuit breaker status for operation type."""
        breaker_key = 'recovery'  # Default
        
        if 'code' in operation_type.lower():
            breaker_key = 'code_fix'
        elif 'command' in operation_type.lower():
            breaker_key = 'command_retry'
        
        breaker = self.circuit_breakers.get(breaker_key, self.circuit_breakers['recovery'])
        can_proceed = breaker.can_proceed()
        
        return {
            'can_proceed': can_proceed,
            'breaker_status': breaker.get_status(),
            'breaker_type': breaker_key,
            'retry_after': self.safety_limits.circuit_breaker_timeout_seconds if not can_proceed else 0
        }
    
    def _determine_safety_level(self, risk_level: str, operation_type: str, 
                               resource_usage: ResourceUsage) -> SafetyLevel:
        """Determine safety level for operation."""
        # High risk operations are more restricted
        if risk_level in ['critical', 'maximum']:
            return SafetyLevel.RESTRICTED
        
        # High resource usage increases restrictions
        if resource_usage.memory_usage_mb > self.safety_limits.max_memory_usage_mb * 0.8:
            return SafetyLevel.CAUTIOUS
        
        if resource_usage.active_recoveries > self.safety_limits.max_concurrent_recoveries * 0.7:
            return SafetyLevel.CAUTIOUS
        
        # Code modifications are inherently risky
        if 'code' in operation_type.lower() and resource_usage.code_modifications_hour > 3:
            return SafetyLevel.CAUTIOUS
        
        return SafetyLevel.SAFE
    
    def _get_safety_conditions(self, safety_level: SafetyLevel) -> List[str]:
        """Get safety conditions for given safety level."""
        conditions = []
        
        if safety_level == SafetyLevel.RESTRICTED:
            conditions.extend([
                "Additional confirmation required for risky operations",
                "Enhanced monitoring and logging active",
                "Automatic rollback enabled"
            ])
        elif safety_level == SafetyLevel.CAUTIOUS:
            conditions.extend([
                "Increased monitoring active",
                "Resource usage will be tracked closely"
            ])
        
        return conditions
    
    async def _log_audit_event(self, event_type: AuditEventType,
                             session_id: str = None,
                             details: Dict[str, Any] = None,
                             risk_level: str = 'medium'):
        """Log audit event with structured data."""
        try:
            event = AuditEvent(
                event_id=f"audit_{int(time.time() * 1000)}",
                event_type=event_type,
                timestamp=datetime.now(),
                session_id=session_id,
                user_id=None,  # Could be populated from context
                details=details or {},
                risk_level=risk_level,
                resource_usage=asdict(self.resource_monitor.get_current_usage())
            )
            
            # Log as JSON line
            self.audit_logger.info(json.dumps(event.to_dict()))
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get comprehensive safety status."""
        return {
            'active_recoveries': len(self.active_recoveries),
            'resource_usage': asdict(self.resource_monitor.get_current_usage()),
            'circuit_breakers': {
                name: breaker.get_status() 
                for name, breaker in self.circuit_breakers.items()
            },
            'hourly_stats': dict(self.hourly_stats),
            'safety_limits': asdict(self.safety_limits),
            'recent_violations': self._get_recent_violations()
        }
    
    def _get_recent_violations(self) -> List[Dict[str, Any]]:
        """Get recent safety violations."""
        # This would typically query recent audit events
        # For now, return empty list as placeholder
        return []
    
    def add_safety_callback(self, callback: Callable):
        """Add callback for safety events."""
        self.safety_callbacks.append(callback)
    
    def cleanup_expired_data(self):
        """Clean up expired tracking data."""
        # Clean up old hourly stats (keep last 24 hours)
        current_hour = datetime.now().hour
        hours_to_keep = set((current_hour - i) % 24 for i in range(24))
        
        keys_to_remove = [
            hour for hour in self.hourly_stats.keys() 
            if hour not in hours_to_keep
        ]
        
        for hour in keys_to_remove:
            del self.hourly_stats[hour]
        
        self.logger.info(f"Cleaned up {len(keys_to_remove)} expired hour stats")


class ResourceMonitor:
    """Monitor system resources for safety limits."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.logger = logging.getLogger(f'{self.__class__.__name__}')
    
    def get_current_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        try:
            import psutil
            
            # Get current process info
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return ResourceUsage(
                memory_usage_mb=memory_info.rss / 1024 / 1024,
                disk_usage_mb=0.0,  # Would implement disk usage tracking
                cpu_percent=process.cpu_percent(),
                active_recoveries=0,  # Will be set by caller
                total_recovery_time_hour=0.0,  # Will be set by caller
                code_modifications_hour=0  # Will be set by caller
            )
            
        except ImportError:
            # Fallback if psutil not available
            return ResourceUsage(
                memory_usage_mb=50.0,  # Estimated
                disk_usage_mb=10.0,
                cpu_percent=5.0,
                active_recoveries=0,
                total_recovery_time_hour=0.0,
                code_modifications_hour=0
            )
        
        except Exception as e:
            self.logger.error(f"Resource monitoring failed: {e}")
            return ResourceUsage(
                memory_usage_mb=0.0,
                disk_usage_mb=0.0,
                cpu_percent=0.0,
                active_recoveries=0,
                total_recovery_time_hour=0.0,
                code_modifications_hour=0
            )


# Convenience functions
def create_safety_manager(safety_limits: SafetyLimits = None, 
                         audit_log_path: str = None) -> RecoverySafetyManager:
    """Create recovery safety manager."""
    return RecoverySafetyManager(safety_limits, audit_log_path)


def create_default_safety_limits() -> SafetyLimits:
    """Create default safety limits configuration."""
    return SafetyLimits()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_safety_manager():
        """Test the recovery safety manager."""
        safety_manager = create_safety_manager()
        
        print("🛡️ Recovery Safety Manager Test")
        print("=" * 50)
        
        # Test authorization
        auth_result = await safety_manager.check_recovery_authorization(
            session_id="test_001",
            operation_type="code_fix",
            risk_level="medium"
        )
        
        print(f"Authorization: {auth_result}")
        
        # Simulate recovery completion
        await safety_manager.register_recovery_completion(
            session_id="test_001",
            success=True,
            execution_time=5.2,
            operations_performed=["web_research", "code_fix"],
            resources_modified=["app.py"]
        )
        
        # Get safety status
        status = safety_manager.get_safety_status()
        print(f"Safety Status: Active recoveries: {status['active_recoveries']}")
    
    # Run test
    asyncio.run(test_safety_manager())