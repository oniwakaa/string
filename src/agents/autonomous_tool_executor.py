"""
Autonomous Tool Executor Agent with Error Recovery

This module extends the Enhanced Tool Executor Agent with autonomous error
diagnosis, research, and recovery capabilities. It implements a robust
multi-agent recovery loop that significantly enhances reliability and autonomy.

Key Features:
- Autonomous error recognition and classification
- Multi-agent recovery orchestration (WebResearch, CodeEditor, ToolExecutor)
- Intelligent retry logic with exponential backoff
- Comprehensive audit logging with full traceability
- Safety mechanisms to prevent infinite loops
- Integration with confirmation system for risky recovery operations

Recovery Flow:
Command Execution → Error Detection → Classification → Recovery Strategy → 
Agent Routing → Fix Application → Validation → Success/Retry/Manual

Author: Claude Code Assistant
Date: 2025-01-26
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Import base components
from .enhanced_tool_executor import EnhancedToolExecutorAgent
from .error_analysis import ErrorClassifier, ErrorContext, ErrorAnalysis, create_error_classifier
from .recovery_workflow import RecoveryWorkflowOrchestrator, RecoverySession, create_recovery_orchestrator
from .confirmation_system import ConfirmationGateSystem, create_confirmation_system
from agents.base import Task, Result


@dataclass
class ExecutionResult:
    """Enhanced execution result with recovery information."""
    task_id: str
    status: str  # success, failed, recovered, manual_required
    output: Any
    error_message: Optional[str] = None
    recovery_session: Optional[RecoverySession] = None
    execution_time: float = 0.0
    recovery_applied: bool = False
    manual_intervention_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            'task_id': self.task_id,
            'status': self.status,
            'output': self.output,
            'error_message': self.error_message,
            'execution_time': self.execution_time,
            'recovery_applied': self.recovery_applied,
            'manual_intervention_required': self.manual_intervention_required
        }
        
        if self.recovery_session:
            result['recovery_session'] = self.recovery_session.to_dict()
        
        return result


class AutonomousToolExecutorAgent(EnhancedToolExecutorAgent):
    """
    Autonomous Tool Executor Agent with comprehensive error recovery.
    
    This agent extends the Enhanced Tool Executor with sophisticated error
    recovery capabilities, making it truly autonomous in handling failures
    and providing a robust multi-agent recovery loop.
    """
    
    def __init__(self, project_root: Optional[str] = None, log_file: Optional[str] = None):
        """
        Initialize the autonomous tool executor agent.
        
        Args:
            project_root: Root directory for operations
            log_file: Path to audit log file
        """
        super().__init__(project_root, log_file)
        
        # Initialize recovery components
        self.error_classifier = create_error_classifier()
        self.confirmation_system = create_confirmation_system()
        self.recovery_orchestrator = create_recovery_orchestrator(
            self.error_classifier, 
            self.confirmation_system
        )
        
        # Recovery configuration
        self.recovery_config = {
            'enable_auto_recovery': True,
            'max_recovery_attempts': 3,
            'recovery_timeout': 300,  # 5 minutes
            'enable_risky_recovery': False,
            'log_all_recovery_attempts': True,
            'enable_learning_from_recovery': True
        }
        
        # Recovery statistics
        self.recovery_stats = {
            'total_errors': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'manual_interventions': 0,
            'recovery_time_total': 0.0
        }
        
        # Update agent identity
        self.name = "AutonomousToolExecutorAgent"
        self.role = "autonomous_tool_executor"
        
        # Recovery audit log
        self.recovery_logger = logging.getLogger(f'{self.__class__.__name__}_Recovery')
        self.recovery_logger.setLevel(logging.INFO)
        
        self.logger.info("AutonomousToolExecutorAgent initialized with recovery capabilities")
    
    async def execute(self, task: Task) -> Result:
        """
        Execute a task with autonomous error recovery.
        
        This method extends the base execute method with comprehensive error
        handling and recovery capabilities.
        
        Args:
            task: Task to execute
            
        Returns:
            Result with recovery information if applicable
        """
        execution_start = time.time()
        
        try:
            # Ensure models are loaded
            if self.status != 'ready':
                self.lazy_load_model()
            
            self.logger.info(f"🚀 Executing autonomous task: {task.task_id}")
            
            # Execute base functionality
            initial_result = await super().execute(task)
            
            # Check if execution was successful
            if initial_result.status == "success":
                # No error recovery needed
                execution_time = time.time() - execution_start
                self.logger.info(f"✅ Task {task.task_id} completed successfully in {execution_time:.2f}s")
                return initial_result
            
            # Handle execution failure with recovery
            if self.recovery_config['enable_auto_recovery']:
                recovery_result = await self._handle_execution_failure(
                    task, initial_result, execution_start
                )
                return recovery_result
            else:
                # Return original failure without recovery
                return initial_result
                
        except Exception as e:
            execution_time = time.time() - execution_start
            error_msg = f"AutonomousToolExecutorAgent execution failed: {str(e)}"
            self.logger.error(error_msg)
            
            return Result(
                task_id=task.task_id,
                status="failure",
                output="",
                error_message=error_msg
            )
    
    async def _handle_execution_failure(self, task: Task, initial_result: Result, execution_start: float) -> Result:
        """
        Handle execution failure with autonomous recovery.
        
        Args:
            task: Original task that failed
            initial_result: Initial failed result
            execution_start: Start time of execution
            
        Returns:
            Result with recovery information
        """
        self.recovery_stats['total_errors'] += 1
        
        try:
            # Step 1: Extract error context from failed execution
            error_context = await self._extract_error_context(task, initial_result)
            
            if not error_context:
                self.logger.warning(f"Could not extract error context for task {task.task_id}")
                return self._create_failed_result(task, initial_result, execution_start)
            
            # Step 2: Classify the error
            self.recovery_logger.info(f"🔍 Classifying error for task {task.task_id}")
            error_analysis = self.error_classifier.analyze_error(error_context)
            
            # Log error analysis
            self._log_error_analysis(error_analysis)
            
            # Step 3: Check if recovery should be attempted
            if not self._should_attempt_recovery(error_analysis):
                self.recovery_logger.info(f"❌ Skipping recovery for task {task.task_id}: not recoverable")
                return self._create_failed_result(task, initial_result, execution_start, error_analysis)
            
            # Step 4: Initiate recovery workflow
            self.recovery_logger.info(f"🛠️ Initiating recovery for task {task.task_id}")
            recovery_session = await self.recovery_orchestrator.initiate_recovery(
                error_analysis, 
                original_command=error_context.command,
                context={'task_id': task.task_id}
            )
            
            # Step 5: Process recovery results
            execution_result = await self._process_recovery_results(
                task, initial_result, recovery_session, execution_start
            )
            
            # Update statistics
            self._update_recovery_stats(recovery_session)
            
            return self._convert_to_result(execution_result)
            
        except Exception as e:
            self.recovery_logger.error(f"Recovery handling failed for task {task.task_id}: {e}")
            self.recovery_stats['failed_recoveries'] += 1
            
            return Result(
                task_id=task.task_id,
                status="failure",
                output=initial_result.output,
                error_message=f"Recovery failed: {str(e)}"
            )
    
    async def _extract_error_context(self, task: Task, result: Result) -> Optional[ErrorContext]:
        """
        Extract error context from failed task execution.
        
        Args:
            task: Failed task
            result: Failed result
            
        Returns:
            ErrorContext if extractable, None otherwise
        """
        try:
            # Determine command from task
            if self._is_json_command(task.prompt):
                # Extract command from JSON
                command_data = json.loads(task.prompt)
                if command_data.get('tool') == 'run_terminal_command':
                    command = ' '.join(command_data.get('args', {}).get('command', []))
                else:
                    command = f"Tool: {command_data.get('tool', 'unknown')}"
            else:
                # Natural language command
                command = task.prompt
            
            # Extract error information from result
            error_output = ""
            exit_code = 1
            
            if isinstance(result.output, dict):
                if 'execution_result' in result.output:
                    exec_result = result.output['execution_result']
                    error_output = exec_result.get('stderr', '') or exec_result.get('error', '')
                    exit_code = exec_result.get('exit_code', 1)
                elif 'error' in result.output:
                    error_output = str(result.output['error'])
            
            if not error_output and result.error_message:
                error_output = result.error_message
            
            return ErrorContext(
                command=command,
                exit_code=exit_code,
                stdout="",  # Usually not available at this level
                stderr=error_output,
                execution_time=0.0,  # Will be calculated elsewhere
                working_directory=str(self.toolbox.project_root),
                environment_vars={},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error context extraction failed: {e}")
            return None
    
    def _should_attempt_recovery(self, error_analysis: ErrorAnalysis) -> bool:
        """
        Determine if recovery should be attempted based on error analysis.
        
        Args:
            error_analysis: Analyzed error information
            
        Returns:
            True if recovery should be attempted
        """
        # Don't attempt recovery for very low confidence classifications
        if error_analysis.confidence < 0.3:
            return False
        
        # Don't attempt recovery for critical system errors without permission
        if error_analysis.severity.value == 'critical' and not self.recovery_config['enable_risky_recovery']:
            return False
        
        # Always attempt recovery for code errors and command syntax issues
        if error_analysis.requires_code_fix or error_analysis.requires_command_retry:
            return True
        
        # Attempt recovery for medium severity errors
        if error_analysis.severity.value in ['low', 'medium']:
            return True
        
        return False
    
    def _log_error_analysis(self, error_analysis: ErrorAnalysis):
        """Log error analysis for audit trail."""
        self.recovery_logger.info(
            f"Error Analysis - ID: {error_analysis.error_id}, "
            f"Category: {error_analysis.category.value}, "
            f"Severity: {error_analysis.severity.value}, "
            f"Confidence: {error_analysis.confidence:.2f}, "
            f"Message: {error_analysis.primary_message}"
        )
        
        if error_analysis.suggested_fixes:
            self.recovery_logger.info(f"Suggested fixes: {', '.join(error_analysis.suggested_fixes[:3])}")
    
    async def _process_recovery_results(self, task: Task, initial_result: Result, 
                                      recovery_session: RecoverySession, execution_start: float) -> ExecutionResult:
        """
        Process recovery session results and determine final outcome.
        
        Args:
            task: Original task
            initial_result: Initial failed result
            recovery_session: Recovery session with results
            execution_start: Start time of execution
            
        Returns:
            ExecutionResult with final status
        """
        execution_time = time.time() - execution_start
        
        if recovery_session.final_status.value == 'success':
            # Recovery succeeded
            self.recovery_logger.info(f"✅ Recovery successful for task {task.task_id}")
            
            return ExecutionResult(
                task_id=task.task_id,
                status="recovered",
                output={
                    'recovery_applied': True,
                    'original_error': recovery_session.original_error.primary_message,
                    'recovery_actions': [attempt.actions_taken for attempt in recovery_session.attempts],
                    'fixes_applied': recovery_session.code_fixes_applied,
                    'commands_retried': recovery_session.commands_retried
                },
                recovery_session=recovery_session,
                execution_time=execution_time,
                recovery_applied=True
            )
        
        elif recovery_session.final_status.value == 'requires_manual':
            # Manual intervention required
            self.recovery_logger.info(f"⚠️ Manual intervention required for task {task.task_id}")
            
            return ExecutionResult(
                task_id=task.task_id,
                status="manual_required",
                output={
                    'recovery_attempted': True,
                    'manual_intervention_required': True,
                    'research_results': recovery_session.research_results,
                    'suggested_actions': recovery_session.original_error.suggested_fixes
                },
                recovery_session=recovery_session,
                execution_time=execution_time,
                recovery_applied=True,
                manual_intervention_required=True
            )
        
        else:
            # Recovery failed
            self.recovery_logger.info(f"❌ Recovery failed for task {task.task_id}")
            
            return ExecutionResult(
                task_id=task.task_id,
                status="failed",
                output=initial_result.output,
                error_message=initial_result.error_message,
                recovery_session=recovery_session,
                execution_time=execution_time,
                recovery_applied=True
            )
    
    def _create_failed_result(self, task: Task, initial_result: Result, execution_start: float, 
                             error_analysis: ErrorAnalysis = None) -> Result:
        """Create failed result without recovery."""
        execution_time = time.time() - execution_start
        
        enhanced_output = {
            'original_output': initial_result.output,
            'execution_time': execution_time,
            'recovery_attempted': False
        }
        
        if error_analysis:
            enhanced_output['error_analysis'] = {
                'category': error_analysis.category.value,
                'severity': error_analysis.severity.value,
                'message': error_analysis.primary_message,
                'suggested_fixes': error_analysis.suggested_fixes
            }
        
        return Result(
            task_id=task.task_id,
            status="failure",
            output=enhanced_output,
            error_message=initial_result.error_message
        )
    
    def _update_recovery_stats(self, recovery_session: RecoverySession):
        """Update recovery statistics."""
        if recovery_session.final_status.value == 'success':
            self.recovery_stats['successful_recoveries'] += 1
        elif recovery_session.final_status.value == 'requires_manual':
            self.recovery_stats['manual_interventions'] += 1
        else:
            self.recovery_stats['failed_recoveries'] += 1
        
        self.recovery_stats['recovery_time_total'] += recovery_session.total_time
    
    def _convert_to_result(self, execution_result: ExecutionResult) -> Result:
        """Convert ExecutionResult to Result for compatibility."""
        return Result(
            task_id=execution_result.task_id,
            status=execution_result.status,
            output=execution_result.output,
            error_message=execution_result.error_message
        )
    
    # Additional methods for recovery management
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get comprehensive recovery statistics."""
        base_stats = self.recovery_stats.copy()
        
        # Calculate success rates
        total_recoveries = (
            base_stats['successful_recoveries'] + 
            base_stats['failed_recoveries'] + 
            base_stats['manual_interventions']
        )
        
        if total_recoveries > 0:
            base_stats['recovery_success_rate'] = base_stats['successful_recoveries'] / total_recoveries
            base_stats['manual_intervention_rate'] = base_stats['manual_interventions'] / total_recoveries
            base_stats['average_recovery_time'] = base_stats['recovery_time_total'] / total_recoveries
        else:
            base_stats['recovery_success_rate'] = 0.0
            base_stats['manual_intervention_rate'] = 0.0
            base_stats['average_recovery_time'] = 0.0
        
        # Add orchestrator statistics
        orchestrator_stats = self.recovery_orchestrator.get_recovery_statistics()
        base_stats['orchestrator_stats'] = orchestrator_stats
        
        return base_stats
    
    def get_recent_recovery_sessions(self, limit: int = 10) -> List[RecoverySession]:
        """Get recent recovery sessions."""
        return self.recovery_orchestrator.get_completed_sessions(limit)
    
    def configure_recovery(self, **config_updates):
        """Update recovery configuration."""
        self.recovery_config.update(config_updates)
        self.logger.info(f"Recovery configuration updated: {config_updates}")
    
    def enable_recovery_learning(self):
        """Enable learning from recovery patterns (placeholder for future ML integration)."""
        self.recovery_config['enable_learning_from_recovery'] = True
        self.logger.info("Recovery learning enabled")
    
    def get_recovery_insights(self) -> Dict[str, Any]:
        """Get insights from recovery patterns for system improvement."""
        sessions = self.get_recent_recovery_sessions(50)
        
        if not sessions:
            return {'insights': 'No recovery sessions available for analysis'}
        
        # Analyze common error patterns
        error_categories = {}
        recovery_strategies = {}
        
        for session in sessions:
            category = session.original_error.category.value
            strategy = session.recovery_strategy.value
            
            error_categories[category] = error_categories.get(category, 0) + 1
            recovery_strategies[strategy] = recovery_strategies.get(strategy, 0) + 1
        
        return {
            'total_sessions_analyzed': len(sessions),
            'most_common_error_categories': sorted(error_categories.items(), key=lambda x: x[1], reverse=True)[:5],
            'most_used_recovery_strategies': sorted(recovery_strategies.items(), key=lambda x: x[1], reverse=True)[:5],
            'insights': [
                f"Most common error: {max(error_categories.items(), key=lambda x: x[1])[0]}" if error_categories else "No errors",
                f"Most effective strategy: {max(recovery_strategies.items(), key=lambda x: x[1])[0]}" if recovery_strategies else "No strategies"
            ]
        }


# Convenience function
def create_autonomous_tool_executor(project_root: str = None, log_file: str = None) -> AutonomousToolExecutorAgent:
    """Create autonomous tool executor agent instance."""
    return AutonomousToolExecutorAgent(project_root=project_root, log_file=log_file)


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from agents.base import Task
    
    async def test_autonomous_executor():
        """Test the autonomous tool executor with error recovery."""
        agent = create_autonomous_tool_executor()
        
        print("🤖 Autonomous Tool Executor Agent Test")
        print("=" * 50)
        
        # Test 1: Successful command
        success_task = Task(
            task_id="test_success",
            prompt="list all Python files",
            context={}
        )
        
        result1 = await agent.execute(success_task)
        print(f"Success Test: {result1.status}")
        
        # Test 2: Command that will fail and trigger recovery
        fail_task = Task(
            task_id="test_recovery", 
            prompt='{"tool": "run_terminal_command", "args": {"command": ["python", "nonexistent_script.py"]}}',
            context={}
        )
        
        result2 = await agent.execute(fail_task)
        print(f"Recovery Test: {result2.status}")
        
        # Show recovery statistics
        stats = agent.get_recovery_statistics()
        print(f"Recovery Stats: {stats}")
    
    # Run test
    asyncio.run(test_autonomous_executor())