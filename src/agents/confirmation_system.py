"""
Confirmation Gate System for Enhanced Tool Executor

This module provides a sophisticated confirmation system for managing
user approval of potentially destructive or privileged operations.

Features:
- Risk-based confirmation requirements
- CLI integration hooks for interactive prompts
- Timeout handling with safe defaults
- Comprehensive audit logging
- Batch confirmation for multiple operations

Author: Claude Code Assistant
Date: 2025-01-26
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class ConfirmationStatus(Enum):
    """Status of a confirmation request."""
    PENDING = "pending"
    APPROVED = "approved" 
    DENIED = "denied"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RiskLevel(Enum):
    """Risk levels for operations requiring confirmation."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class ConfirmationRequest:
    """A request for user confirmation."""
    request_id: str
    operation_type: str
    command: str
    risk_level: RiskLevel
    description: str
    confirmation_template: str
    safety_checks: List[str]
    timeout_seconds: int
    auto_deny_on_timeout: bool
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any]
    
    def is_expired(self) -> bool:
        """Check if confirmation request has expired."""
        return datetime.now() > self.expires_at
    
    def time_remaining(self) -> int:
        """Get remaining time in seconds."""
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, int(remaining))


@dataclass 
class ConfirmationResponse:
    """Response to a confirmation request."""
    request_id: str
    status: ConfirmationStatus
    user_input: str
    confirmed: bool
    response_time: float
    responded_at: datetime
    reason: str
    metadata: Dict[str, Any] = None


class ConfirmationGateSystem:
    """
    System for managing confirmation gates and user approvals.
    
    This system handles:
    - Creating confirmation requests with appropriate risk levels
    - Managing request lifecycle and timeouts
    - Integrating with CLI for user interaction
    - Logging all confirmation decisions
    - Providing hooks for custom confirmation handlers
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize confirmation gate system.
        
        Args:
            config: Configuration dictionary for timeouts, templates, etc.
        """
        self.config = config or self._default_config()
        self.pending_requests: Dict[str, ConfirmationRequest] = {}
        self.completed_requests: Dict[str, ConfirmationResponse] = {}
        
        # CLI integration hooks
        self.cli_prompt_handler: Optional[Callable] = None
        self.cli_display_handler: Optional[Callable] = None
        
        # Audit logging
        self.logger = logging.getLogger(f'{self.__class__.__name__}')
        self.logger.setLevel(logging.INFO)
        
        # Auto-confirmation for testing/CI
        self.auto_confirm_enabled = self.config.get('auto_confirm', {}).get('enabled', False)
        self.auto_confirm_patterns = self.config.get('auto_confirm', {}).get('patterns', [])
        
        self.logger.info("ConfirmationGateSystem initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for confirmation system."""
        return {
            'timeouts': {
                'default_timeout': 30,
                'admin_timeout': 60,
                'auto_deny_on_timeout': True
            },
            'templates': {
                'default': "⚠️  Execute: {command}? [y/N]",
                'file_operation': "📁 {operation} {files}? [y/N]",
                'server_operation': "🔧 {operation} {service}? [y/N]",
                'admin_operation': "🚨 ADMIN: {operation}. Type 'CONFIRM':"
            },
            'risk_thresholds': {
                'minimal': 0,     # No confirmation needed
                'low': 0,         # No confirmation needed  
                'medium': 30,     # 30 second timeout
                'high': 60,       # 60 second timeout
                'maximum': 120    # 2 minute timeout, elevated confirmation
            },
            'auto_confirm': {
                'enabled': False,
                'patterns': []
            }
        }
    
    def set_cli_handlers(self, prompt_handler: Callable = None, display_handler: Callable = None):
        """
        Set handlers for CLI integration.
        
        Args:
            prompt_handler: Function to handle user input prompts
            display_handler: Function to display confirmation requests
        """
        self.cli_prompt_handler = prompt_handler
        self.cli_display_handler = display_handler
        self.logger.info("CLI handlers configured")
    
    async def request_confirmation(
        self,
        operation_type: str,
        command: str,
        risk_level: str,
        description: str = "",
        metadata: Dict[str, Any] = None
    ) -> ConfirmationResponse:
        """
        Request user confirmation for an operation.
        
        Args:
            operation_type: Type of operation (file_modification, server_shutdown, etc.)
            command: The actual command to be executed
            risk_level: Risk level string (minimal, low, medium, high, maximum)
            description: Human-readable description of the operation
            metadata: Additional metadata for the request
            
        Returns:
            ConfirmationResponse with user's decision
        """
        # Convert risk level string to enum
        try:
            risk_enum = RiskLevel(risk_level.lower())
        except ValueError:
            risk_enum = RiskLevel.MEDIUM
        
        # Check if confirmation is actually needed
        if risk_enum in [RiskLevel.MINIMAL, RiskLevel.LOW]:
            return self._create_auto_approved_response(
                "low_risk_auto_approved", 
                f"Auto-approved {risk_level} risk operation"
            )
        
        # Check auto-confirmation patterns
        if self.auto_confirm_enabled:
            for pattern in self.auto_confirm_patterns:
                if pattern in command.lower():
                    return self._create_auto_approved_response(
                        "auto_confirm_pattern_match",
                        f"Auto-confirmed due to pattern match: {pattern}"
                    )
        
        # Create confirmation request
        request_id = self._generate_request_id()
        timeout_seconds = self.config['risk_thresholds'].get(risk_level, 30)
        
        confirmation_request = ConfirmationRequest(
            request_id=request_id,
            operation_type=operation_type,
            command=command,
            risk_level=risk_enum,
            description=description or f"Execute command: {command}",
            confirmation_template=self._get_confirmation_template(operation_type, risk_enum),
            safety_checks=[],  # TODO: Implement safety checks
            timeout_seconds=timeout_seconds,
            auto_deny_on_timeout=self.config['timeouts']['auto_deny_on_timeout'],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=timeout_seconds),
            metadata=metadata or {}
        )
        
        # Store pending request
        self.pending_requests[request_id] = confirmation_request
        
        # Log confirmation request
        self._log_confirmation_request(confirmation_request)
        
        try:
            # Handle confirmation based on available handlers
            if self.cli_prompt_handler:
                # Interactive CLI confirmation
                response = await self._handle_cli_confirmation(confirmation_request)
            else:
                # Simulated confirmation for testing
                response = await self._handle_simulated_confirmation(confirmation_request)
            
            # Store completed request
            self.completed_requests[request_id] = response
            
            # Remove from pending
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            
            # Log final response
            self._log_confirmation_response(response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Confirmation handling failed: {e}")
            # Return denial on error
            return ConfirmationResponse(
                request_id=request_id,
                status=ConfirmationStatus.DENIED,
                user_input="",
                confirmed=False,
                response_time=0.0,
                responded_at=datetime.now(),
                reason=f"Error during confirmation: {str(e)}"
            )
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = int(time.time() * 1000)
        return f"confirm_{timestamp}"
    
    def _get_confirmation_template(self, operation_type: str, risk_level: RiskLevel) -> str:
        """Get appropriate confirmation template."""
        templates = self.config['templates']
        
        if risk_level == RiskLevel.MAXIMUM:
            return templates.get('admin_operation', templates['default'])
        elif operation_type in templates:
            return templates[operation_type]
        else:
            return templates['default']
    
    async def _handle_cli_confirmation(self, request: ConfirmationRequest) -> ConfirmationResponse:
        """Handle confirmation through CLI interface."""
        start_time = time.time()
        
        try:
            # Display confirmation request if handler available
            if self.cli_display_handler:
                self.cli_display_handler(request)
            
            # Format prompt message
            prompt_message = self._format_confirmation_prompt(request)
            
            # Get user input through CLI handler
            user_input = await self.cli_prompt_handler(
                prompt_message, 
                timeout=request.timeout_seconds
            )
            
            # Parse user response
            confirmed = self._parse_user_confirmation(user_input, request.risk_level)
            
            response_time = time.time() - start_time
            
            return ConfirmationResponse(
                request_id=request.request_id,
                status=ConfirmationStatus.APPROVED if confirmed else ConfirmationStatus.DENIED,
                user_input=user_input,
                confirmed=confirmed,
                response_time=response_time,
                responded_at=datetime.now(),
                reason="User response via CLI"
            )
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return ConfirmationResponse(
                request_id=request.request_id,
                status=ConfirmationStatus.TIMEOUT,
                user_input="",
                confirmed=False,
                response_time=response_time,
                responded_at=datetime.now(),
                reason="User confirmation timed out"
            )
    
    async def _handle_simulated_confirmation(self, request: ConfirmationRequest) -> ConfirmationResponse:
        """Handle simulated confirmation for testing."""
        start_time = time.time()
        
        # Simulate thinking time
        await asyncio.sleep(0.1)
        
        # Simulate confirmation logic based on risk level
        if request.risk_level == RiskLevel.MAXIMUM:
            # Maximum risk requires explicit confirmation - deny in simulation
            confirmed = False
            reason = "Simulated denial for maximum risk operation"
            status = ConfirmationStatus.DENIED
        elif request.risk_level == RiskLevel.HIGH:
            # High risk - cautious approval
            confirmed = True
            reason = "Simulated cautious approval for high risk operation"
            status = ConfirmationStatus.APPROVED
        else:
            # Medium risk - approve
            confirmed = True
            reason = "Simulated approval for medium risk operation"
            status = ConfirmationStatus.APPROVED
        
        response_time = time.time() - start_time
        
        return ConfirmationResponse(
            request_id=request.request_id,
            status=status,
            user_input="simulated",
            confirmed=confirmed,
            response_time=response_time,
            responded_at=datetime.now(),
            reason=reason
        )
    
    def _format_confirmation_prompt(self, request: ConfirmationRequest) -> str:
        """Format confirmation prompt for display."""
        template = request.confirmation_template
        
        # Replace template variables
        formatted = template.format(
            command=request.command,
            operation=request.operation_type,
            description=request.description
        )
        
        # Add risk level indicator
        risk_indicators = {
            RiskLevel.MEDIUM: "⚠️ ",
            RiskLevel.HIGH: "🔴 ",
            RiskLevel.MAXIMUM: "🚨 "
        }
        
        indicator = risk_indicators.get(request.risk_level, "")
        
        # Add timeout information
        timeout_info = f" (timeout: {request.timeout_seconds}s)"
        
        return f"{indicator}{formatted}{timeout_info}"
    
    def _parse_user_confirmation(self, user_input: str, risk_level: RiskLevel) -> bool:
        """Parse user input to determine confirmation."""
        if not user_input:
            return False
        
        user_input = user_input.strip().lower()
        
        # Maximum risk requires explicit "CONFIRM"
        if risk_level == RiskLevel.MAXIMUM:
            return user_input == "confirm"
        
        # Standard yes/no parsing
        positive_responses = ['y', 'yes', 'ok', 'confirm', '1', 'true']
        return user_input in positive_responses
    
    def _create_auto_approved_response(self, reason: str, description: str) -> ConfirmationResponse:
        """Create an auto-approved confirmation response."""
        return ConfirmationResponse(
            request_id="auto_approved",
            status=ConfirmationStatus.APPROVED,
            user_input="auto",
            confirmed=True,
            response_time=0.0,
            responded_at=datetime.now(),
            reason=description
        )
    
    def _log_confirmation_request(self, request: ConfirmationRequest):
        """Log confirmation request for audit trail."""
        self.logger.info(
            f"Confirmation requested: {request.operation_type} "
            f"[{request.risk_level.value}] - {request.command}"
        )
    
    def _log_confirmation_response(self, response: ConfirmationResponse):
        """Log confirmation response for audit trail."""
        self.logger.info(
            f"Confirmation {response.status.value}: {response.request_id} "
            f"- {'APPROVED' if response.confirmed else 'DENIED'} "
            f"({response.response_time:.2f}s) - {response.reason}"
        )
    
    def get_pending_requests(self) -> List[ConfirmationRequest]:
        """Get all pending confirmation requests."""
        return list(self.pending_requests.values())
    
    def get_completed_requests(self, limit: int = 50) -> List[ConfirmationResponse]:
        """Get recent completed confirmation requests."""
        responses = list(self.completed_requests.values())
        responses.sort(key=lambda r: r.responded_at, reverse=True)
        return responses[:limit]
    
    def cancel_request(self, request_id: str, reason: str = "Cancelled by system") -> bool:
        """Cancel a pending confirmation request."""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            
            response = ConfirmationResponse(
                request_id=request_id,
                status=ConfirmationStatus.CANCELLED,
                user_input="",
                confirmed=False,
                response_time=0.0,
                responded_at=datetime.now(),
                reason=reason
            )
            
            self.completed_requests[request_id] = response
            del self.pending_requests[request_id]
            
            self._log_confirmation_response(response)
            return True
        
        return False
    
    def cleanup_expired_requests(self):
        """Clean up expired confirmation requests."""
        expired_ids = []
        
        for request_id, request in self.pending_requests.items():
            if request.is_expired():
                expired_ids.append(request_id)
        
        for request_id in expired_ids:
            request = self.pending_requests[request_id]
            
            response = ConfirmationResponse(
                request_id=request_id,
                status=ConfirmationStatus.TIMEOUT,
                user_input="",
                confirmed=False,
                response_time=request.timeout_seconds,
                responded_at=datetime.now(),
                reason="Request expired without user response"
            )
            
            self.completed_requests[request_id] = response
            del self.pending_requests[request_id]
            
            self._log_confirmation_response(response)
        
        if expired_ids:
            self.logger.info(f"Cleaned up {len(expired_ids)} expired confirmation requests")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get confirmation system status."""
        return {
            'pending_requests': len(self.pending_requests),
            'completed_requests': len(self.completed_requests),
            'cli_handlers_configured': bool(self.cli_prompt_handler and self.cli_display_handler),
            'auto_confirm_enabled': self.auto_confirm_enabled,
            'system_uptime': datetime.now().isoformat()
        }


# Convenience function for creating confirmation system
def create_confirmation_system(config: Dict[str, Any] = None) -> ConfirmationGateSystem:
    """Create a new confirmation gate system."""
    return ConfirmationGateSystem(config)


# Example CLI integration functions (for reference)
async def example_cli_prompt_handler(message: str, timeout: int) -> str:
    """Example implementation of CLI prompt handler."""
    import sys
    
    print(f"\n{message}")
    
    try:
        # In real implementation, this would use proper async input handling
        response = input("Your response: ")
        return response
    except KeyboardInterrupt:
        return ""


def example_cli_display_handler(request: ConfirmationRequest):
    """Example implementation of CLI display handler."""
    print(f"\n{'='*60}")
    print(f"CONFIRMATION REQUIRED")
    print(f"{'='*60}")
    print(f"Operation: {request.operation_type}")
    print(f"Command: {request.command}")
    print(f"Risk Level: {request.risk_level.value.upper()}")
    print(f"Description: {request.description}")
    print(f"Timeout: {request.timeout_seconds}s")
    print(f"{'='*60}")


# Testing function
async def test_confirmation_system():
    """Test the confirmation system."""
    system = create_confirmation_system()
    
    # Set example handlers
    system.set_cli_handlers(
        prompt_handler=example_cli_prompt_handler,
        display_handler=example_cli_display_handler
    )
    
    # Test different risk levels
    test_cases = [
        ("file_modification", "rm unused_files/*", "high", "Remove unused files"),
        ("server_shutdown", "pkill -f npm", "medium", "Stop development server"),
        ("system_config", "sudo systemctl restart nginx", "maximum", "Restart nginx service")
    ]
    
    for operation_type, command, risk_level, description in test_cases:
        print(f"\nTesting {risk_level} risk operation...")
        
        response = await system.request_confirmation(
            operation_type=operation_type,
            command=command,
            risk_level=risk_level,
            description=description
        )
        
        print(f"Result: {'APPROVED' if response.confirmed else 'DENIED'} ({response.reason})")
    
    # Show system status
    status = system.get_system_status() 
    print(f"\nSystem Status: {status}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_confirmation_system())