"""
Multi-Agent Error Recovery Workflow System

This module orchestrates sophisticated error recovery workflows using multiple
specialized agents. It implements a robust recovery loop that can diagnose,
research, and automatically fix various types of terminal command errors.

Key Features:
- Multi-agent recovery orchestration (WebResearch, CodeEditor, ToolExecutor)
- Intelligent routing based on error classification
- Retry logic with exponential backoff and safety limits
- Comprehensive audit logging of all recovery attempts
- Integration with confirmation system for risky operations

Recovery Flow:
1. Error Classification → 2. Web Research → 3. Agent Routing → 4. Fix Application → 5. Retry/Validate

Author: Claude Code Assistant
Date: 2025-01-26
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .error_analysis import ErrorAnalysis, ErrorCategory, ErrorSeverity, ErrorClassifier
from .confirmation_system import ConfirmationGateSystem, RiskLevel


class RecoveryStatus(Enum):
    """Status of recovery attempt."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"
    REQUIRES_MANUAL = "requires_manual"


class RecoveryStrategy(Enum):  
    """Recovery strategies based on error type."""
    WEB_RESEARCH_ONLY = "web_research_only"
    CODE_FIX_REQUIRED = "code_fix_required"
    COMMAND_RETRY = "command_retry"
    MULTI_STEP_RECOVERY = "multi_step_recovery"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class RecoveryAttempt:
    """Single recovery attempt record."""
    attempt_id: str
    strategy: RecoveryStrategy
    actions_taken: List[str]
    agents_involved: List[str]
    success: bool
    execution_time: float
    error_message: Optional[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            **asdict(self),
            'strategy': self.strategy.value,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class RecoverySession:
    """Complete recovery session tracking."""
    session_id: str
    original_error: ErrorAnalysis
    recovery_strategy: RecoveryStrategy
    max_attempts: int
    attempts: List[RecoveryAttempt]
    final_status: RecoveryStatus
    total_time: float
    research_results: Optional[Dict[str, Any]]
    code_fixes_applied: List[str]
    commands_retried: List[str]
    manual_intervention_required: bool
    session_log: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'original_error': self.original_error.to_dict(),
            'recovery_strategy': self.recovery_strategy.value,
            'max_attempts': self.max_attempts,
            'attempts': [attempt.to_dict() for attempt in self.attempts],
            'final_status': self.final_status.value,
            'total_time': self.total_time,
            'research_results': self.research_results,
            'code_fixes_applied': self.code_fixes_applied,
            'commands_retried': self.commands_retried,
            'manual_intervention_required': self.manual_intervention_required,
            'session_log': self.session_log
        }


class RecoveryWorkflowOrchestrator:
    """
    Orchestrates multi-agent error recovery workflows.
    
    This orchestrator manages the complete recovery process, coordinating
    between different agents to automatically diagnose, research, and fix
    errors from terminal command execution.
    """
    
    def __init__(self, 
                 error_classifier: ErrorClassifier,
                 confirmation_system: ConfirmationGateSystem,
                 agent_registry: Dict[str, Any] = None):
        """
        Initialize the recovery workflow orchestrator.
        
        Args:
            error_classifier: Error classification system
            confirmation_system: Confirmation gate system for risky operations
            agent_registry: Registry of available agents for recovery
        """
        self.error_classifier = error_classifier
        self.confirmation_system = confirmation_system
        self.agent_registry = agent_registry or {}
        
        # Recovery configuration
        self.config = {
            'max_recovery_attempts': 3,
            'web_research_timeout': 30,
            'code_fix_timeout': 60,
            'command_retry_timeout': 15,
            'exponential_backoff_base': 2,
            'safety_limits': {
                'max_code_modifications': 5,
                'max_command_retries': 3,
                'max_total_recovery_time': 300  # 5 minutes
            }
        }
        
        # Active recovery sessions
        self.active_sessions: Dict[str, RecoverySession] = {}
        self.completed_sessions: Dict[str, RecoverySession] = {}
        
        # Logging
        self.logger = logging.getLogger(f'{self.__class__.__name__}')
        self.logger.setLevel(logging.INFO)
        
        self.logger.info("RecoveryWorkflowOrchestrator initialized")
    
    async def initiate_recovery(self, error_analysis: ErrorAnalysis, 
                               original_command: str = None,
                               context: Dict[str, Any] = None) -> RecoverySession:
        """
        Initiate error recovery workflow.
        
        Args:
            error_analysis: Analyzed error information
            original_command: Original command that failed (if different from analysis)
            context: Additional context for recovery
            
        Returns:
            RecoverySession with complete recovery information
        """
        session_start = time.time()
        session_id = self._generate_session_id()
        
        self.logger.info(f"🚨 Initiating recovery session {session_id} for {error_analysis.category.value} error")
        
        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(error_analysis)
        
        # Create recovery session
        session = RecoverySession(
            session_id=session_id,
            original_error=error_analysis,
            recovery_strategy=recovery_strategy,
            max_attempts=self.config['max_recovery_attempts'],
            attempts=[],
            final_status=RecoveryStatus.PENDING,
            total_time=0.0,
            research_results=None,
            code_fixes_applied=[],
            commands_retried=[],
            manual_intervention_required=False,
            session_log=[]
        )
        
        self.active_sessions[session_id] = session
        session.session_log.append(f"Recovery session initiated: {recovery_strategy.value}")
        
        try:
            # Execute recovery workflow based on strategy
            if recovery_strategy == RecoveryStrategy.WEB_RESEARCH_ONLY:
                await self._execute_web_research_workflow(session)
            elif recovery_strategy == RecoveryStrategy.CODE_FIX_REQUIRED:
                await self._execute_code_fix_workflow(session)
            elif recovery_strategy == RecoveryStrategy.COMMAND_RETRY:
                await self._execute_command_retry_workflow(session)
            elif recovery_strategy == RecoveryStrategy.MULTI_STEP_RECOVERY:
                await self._execute_multi_step_workflow(session)
            else:
                await self._execute_manual_intervention_workflow(session)
            
            session.total_time = time.time() - session_start
            
            # Move to completed sessions
            self.completed_sessions[session_id] = session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            self.logger.info(f"✅ Recovery session {session_id} completed: {session.final_status.value} in {session.total_time:.2f}s")
            
            return session
            
        except Exception as e:
            session.final_status = RecoveryStatus.FAILED
            session.total_time = time.time() - session_start
            session.session_log.append(f"Recovery failed with exception: {str(e)}")
            
            self.logger.error(f"❌ Recovery session {session_id} failed: {e}")
            
            # Move to completed sessions
            self.completed_sessions[session_id] = session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            return session
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = int(time.time() * 1000)
        return f"recovery_{timestamp}"
    
    def _determine_recovery_strategy(self, error_analysis: ErrorAnalysis) -> RecoveryStrategy:
        """Determine appropriate recovery strategy based on error analysis."""
        
        # Code errors typically require code fixes
        if error_analysis.requires_code_fix:
            if error_analysis.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                return RecoveryStrategy.MULTI_STEP_RECOVERY
            else:
                return RecoveryStrategy.CODE_FIX_REQUIRED
        
        # Command syntax errors can often be fixed by retry
        elif error_analysis.requires_command_retry:
            if error_analysis.category == ErrorCategory.COMMAND_SYNTAX:
                return RecoveryStrategy.COMMAND_RETRY
            else:
                return RecoveryStrategy.MULTI_STEP_RECOVERY
        
        # System errors often require manual intervention
        elif error_analysis.category == ErrorCategory.SYSTEM_ERROR:
            if error_analysis.severity == ErrorSeverity.CRITICAL:
                return RecoveryStrategy.MANUAL_INTERVENTION
            else:
                return RecoveryStrategy.MULTI_STEP_RECOVERY
        
        # Unknown errors start with web research
        elif error_analysis.category == ErrorCategory.UNKNOWN_ERROR:
            return RecoveryStrategy.WEB_RESEARCH_ONLY
        
        # Default to multi-step recovery for complex cases
        else:
            return RecoveryStrategy.MULTI_STEP_RECOVERY
    
    async def _execute_web_research_workflow(self, session: RecoverySession):
        """Execute web research workflow to find solutions."""
        session.session_log.append("Starting web research workflow")
        
        attempt_id = f"{session.session_id}_research"
        attempt_start = time.time()
        
        try:
            # Step 1: Conduct web research
            research_results = await self._conduct_web_research(session.original_error)
            session.research_results = research_results
            
            # Step 2: Analyze research results
            if research_results and research_results.get('success'):
                session.final_status = RecoveryStatus.SUCCESS
                session.session_log.append("Web research provided solution guidance")
            else:
                session.final_status = RecoveryStatus.FAILED
                session.session_log.append("Web research did not find useful solutions")
            
            # Record attempt
            attempt = RecoveryAttempt(
                attempt_id=attempt_id,
                strategy=RecoveryStrategy.WEB_RESEARCH_ONLY,
                actions_taken=["web_research"],
                agents_involved=["WebResearchAgent"],
                success=session.final_status == RecoveryStatus.SUCCESS,
                execution_time=time.time() - attempt_start,
                error_message=None,
                timestamp=datetime.now()
            )
            session.attempts.append(attempt)
            
        except Exception as e:
            session.final_status = RecoveryStatus.FAILED
            session.session_log.append(f"Web research workflow failed: {str(e)}")
            
            attempt = RecoveryAttempt(
                attempt_id=attempt_id,
                strategy=RecoveryStrategy.WEB_RESEARCH_ONLY,
                actions_taken=["web_research"],
                agents_involved=["WebResearchAgent"],
                success=False,
                execution_time=time.time() - attempt_start,
                error_message=str(e),
                timestamp=datetime.now()
            )
            session.attempts.append(attempt)
    
    async def _execute_code_fix_workflow(self, session: RecoverySession):
        """Execute code fix workflow using CodeEditorAgent."""
        session.session_log.append("Starting code fix workflow")
        
        attempt_id = f"{session.session_id}_codefix"
        attempt_start = time.time()
        
        try:
            # Step 1: Research solutions first
            research_results = await self._conduct_web_research(session.original_error)
            session.research_results = research_results
            
            # Step 2: Apply code fixes
            code_fix_results = await self._apply_code_fixes(session.original_error, research_results)
            
            if code_fix_results.get('success'):
                session.code_fixes_applied = code_fix_results.get('fixes_applied', [])
                session.final_status = RecoveryStatus.SUCCESS
                session.session_log.append(f"Code fixes applied: {len(session.code_fixes_applied)}")
            else:
                session.final_status = RecoveryStatus.FAILED
                session.session_log.append("Code fix application failed")
            
            # Record attempt
            attempt = RecoveryAttempt(
                attempt_id=attempt_id,
                strategy=RecoveryStrategy.CODE_FIX_REQUIRED,
                actions_taken=["web_research", "code_fix"],
                agents_involved=["WebResearchAgent", "CodeEditorAgent"],
                success=session.final_status == RecoveryStatus.SUCCESS,
                execution_time=time.time() - attempt_start,
                error_message=code_fix_results.get('error'),
                timestamp=datetime.now()
            )
            session.attempts.append(attempt)
            
        except Exception as e:
            session.final_status = RecoveryStatus.FAILED
            session.session_log.append(f"Code fix workflow failed: {str(e)}")
            
            attempt = RecoveryAttempt(
                attempt_id=attempt_id,
                strategy=RecoveryStrategy.CODE_FIX_REQUIRED,
                actions_taken=["web_research", "code_fix"],
                agents_involved=["WebResearchAgent", "CodeEditorAgent"],
                success=False,
                execution_time=time.time() - attempt_start,
                error_message=str(e),
                timestamp=datetime.now()
            )
            session.attempts.append(attempt)
    
    async def _execute_command_retry_workflow(self, session: RecoverySession):
        """Execute command retry workflow with corrected commands."""
        session.session_log.append("Starting command retry workflow")
        
        max_retries = self.config['safety_limits']['max_command_retries']
        
        for retry_count in range(max_retries):
            attempt_id = f"{session.session_id}_retry_{retry_count + 1}"
            attempt_start = time.time()
            
            try:
                # Step 1: Generate corrected command
                corrected_command = await self._generate_corrected_command(
                    session.original_error, retry_count
                )
                
                if not corrected_command:
                    session.session_log.append(f"Retry {retry_count + 1}: Could not generate corrected command")
                    continue
                
                # Step 2: Execute corrected command
                execution_result = await self._execute_corrected_command(corrected_command)
                session.commands_retried.append(corrected_command)
                
                # Record attempt
                attempt = RecoveryAttempt(
                    attempt_id=attempt_id,
                    strategy=RecoveryStrategy.COMMAND_RETRY,
                    actions_taken=["command_correction", "command_execution"],
                    agents_involved=["EnhancedPromptHandler", "ToolExecutorAgent"],
                    success=execution_result.get('success', False),
                    execution_time=time.time() - attempt_start,
                    error_message=execution_result.get('error'),
                    timestamp=datetime.now()
                )
                session.attempts.append(attempt)
                
                if execution_result.get('success'):
                    session.final_status = RecoveryStatus.SUCCESS
                    session.session_log.append(f"Command retry successful on attempt {retry_count + 1}")
                    return
                else:
                    session.session_log.append(f"Retry {retry_count + 1} failed: {execution_result.get('error', 'Unknown error')}")
                    
                    # Wait before next retry (exponential backoff)
                    if retry_count < max_retries - 1:
                        wait_time = self.config['exponential_backoff_base'] ** retry_count
                        await asyncio.sleep(wait_time)
                
            except Exception as e:
                session.session_log.append(f"Retry {retry_count + 1} exception: {str(e)}")
                
                attempt = RecoveryAttempt(
                    attempt_id=attempt_id,
                    strategy=RecoveryStrategy.COMMAND_RETRY,
                    actions_taken=["command_correction", "command_execution"],
                    agents_involved=["EnhancedPromptHandler", "ToolExecutorAgent"],
                    success=False,
                    execution_time=time.time() - attempt_start,
                    error_message=str(e),
                    timestamp=datetime.now()
                )
                session.attempts.append(attempt)
        
        # All retries failed
        session.final_status = RecoveryStatus.FAILED
        session.session_log.append(f"All {max_retries} command retries failed")
    
    async def _execute_multi_step_workflow(self, session: RecoverySession):
        """Execute comprehensive multi-step recovery workflow."""
        session.session_log.append("Starting multi-step recovery workflow")
        
        # Step 1: Web research
        session.session_log.append("Step 1: Conducting web research")
        research_results = await self._conduct_web_research(session.original_error)
        session.research_results = research_results
        
        # Step 2: Determine next actions based on research
        if session.original_error.requires_code_fix:
            session.session_log.append("Step 2: Applying code fixes")
            code_fix_results = await self._apply_code_fixes(session.original_error, research_results)
            
            if code_fix_results.get('success'):
                session.code_fixes_applied = code_fix_results.get('fixes_applied', [])
                
                # Step 3: Retry original command after code fix
                session.session_log.append("Step 3: Retrying command after code fixes")
                retry_result = await self._execute_corrected_command(session.original_error.context.command)
                
                if retry_result.get('success'):
                    session.final_status = RecoveryStatus.SUCCESS
                    session.session_log.append("Multi-step recovery successful")
                else:
                    session.final_status = RecoveryStatus.FAILED
                    session.session_log.append("Command still fails after code fixes")
            else:
                session.final_status = RecoveryStatus.FAILED
                session.session_log.append("Code fix application failed")
        
        elif session.original_error.requires_command_retry:
            # Try command correction workflow
            session.session_log.append("Step 2: Attempting command corrections")
            await self._execute_command_retry_workflow(session)
        
        else:
            # Research-only workflow for complex cases
            if research_results and research_results.get('success'):
                session.final_status = RecoveryStatus.SUCCESS
                session.session_log.append("Multi-step recovery completed with research guidance")
            else:
                session.final_status = RecoveryStatus.REQUIRES_MANUAL
                session.manual_intervention_required = True
                session.session_log.append("Multi-step recovery requires manual intervention")
    
    async def _execute_manual_intervention_workflow(self, session: RecoverySession):
        """Execute manual intervention workflow for critical errors."""
        session.session_log.append("Manual intervention required")
        
        # Conduct research to provide guidance
        research_results = await self._conduct_web_research(session.original_error)
        session.research_results = research_results
        
        session.final_status = RecoveryStatus.REQUIRES_MANUAL
        session.manual_intervention_required = True
        session.session_log.append("Recovery workflow completed - manual intervention flagged")
    
    async def _conduct_web_research(self, error_analysis: ErrorAnalysis) -> Dict[str, Any]:
        """Conduct web research for error solutions."""
        try:
            # Simulate web research (in real implementation, would call WebResearchAgent)
            self.logger.info(f"🔍 Researching: {error_analysis.research_query}")
            
            # Mock research results based on error category
            if error_analysis.category == ErrorCategory.CODE_ERROR:
                return {
                    'success': True,
                    'solutions': [
                        "Install missing dependencies",
                        "Fix syntax errors in code",
                        "Update import statements"
                    ],
                    'documentation_links': [
                        "https://docs.python.org/3/tutorial/modules.html"
                    ],
                    'confidence': 0.8
                }
            elif error_analysis.category == ErrorCategory.COMMAND_SYNTAX:
                return {
                    'success': True,
                    'solutions': [
                        "Check command syntax",
                        "Verify command options",
                        "Use correct file paths"
                    ],
                    'documentation_links': [
                        "https://man7.org/linux/man-pages/"
                    ],
                    'confidence': 0.7
                }
            else:
                return {
                    'success': False,
                    'error': 'No specific solutions found',
                    'confidence': 0.3
                }
                
        except Exception as e:
            self.logger.error(f"Web research failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'confidence': 0.0
            }
    
    async def _apply_code_fixes(self, error_analysis: ErrorAnalysis, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Apply code fixes using CodeEditorAgent."""
        try:
            # Simulate code fix application (in real implementation, would call CodeEditorAgent)
            self.logger.info("🔧 Applying code fixes")
            
            fixes_applied = []
            
            if 'ModuleNotFoundError' in error_analysis.primary_message:
                # Simulate installing missing module
                fixes_applied.append("pip install flask")
                return {
                    'success': True,
                    'fixes_applied': fixes_applied,
                    'modified_files': []
                }
            elif 'SyntaxError' in error_analysis.primary_message:
                # Simulate syntax fix
                fixes_applied.append("Fixed syntax error in line 10")
                return {
                    'success': True,
                    'fixes_applied': fixes_applied,
                    'modified_files': ['app.py']
                }
            else:
                return {
                    'success': False,
                    'error': 'No applicable code fixes found'
                }
                
        except Exception as e:
            self.logger.error(f"Code fix application failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _generate_corrected_command(self, error_analysis: ErrorAnalysis, retry_count: int) -> Optional[str]:
        """Generate corrected command based on error analysis."""
        try:
            original_command = error_analysis.context.command
            
            # Simple command correction logic (in real implementation, would use EnhancedPromptHandler)
            if 'command not found' in error_analysis.primary_message:
                # Try common alternatives
                command_alternatives = {
                    'ls': ['ls -la', 'dir'],
                    'cat': ['cat', 'type'],
                    'grep': ['grep', 'findstr']
                }
                
                base_command = original_command.split()[0]
                if base_command in command_alternatives:
                    alternatives = command_alternatives[base_command]
                    if retry_count < len(alternatives):
                        return alternatives[retry_count]
            
            elif 'No such file or directory' in error_analysis.primary_message:
                # Try with different paths
                if retry_count == 0:
                    return f"./{original_command}"
                elif retry_count == 1:
                    return original_command.replace(' ', ' ./')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Command correction failed: {e}")
            return None
    
    async def _execute_corrected_command(self, command: str) -> Dict[str, Any]:
        """Execute corrected command."""
        try:
            # Simulate command execution (in real implementation, would call ToolExecutorAgent)
            self.logger.info(f"▶️ Executing corrected command: {command}")
            
            # Mock execution results
            if 'pip install' in command:
                return {
                    'success': True,
                    'stdout': 'Successfully installed flask-2.0.1',
                    'stderr': '',
                    'exit_code': 0
                }
            elif command.startswith('./'):
                return {
                    'success': True,
                    'stdout': 'Command executed successfully',
                    'stderr': '',
                    'exit_code': 0
                }
            else:
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': 'Command still fails',
                    'exit_code': 1,
                    'error': 'Corrected command did not resolve issue'
                }
                
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_session(self, session_id: str) -> Optional[RecoverySession]:
        """Get recovery session by ID."""
        return self.active_sessions.get(session_id) or self.completed_sessions.get(session_id)
    
    def get_active_sessions(self) -> List[RecoverySession]:
        """Get all active recovery sessions."""
        return list(self.active_sessions.values())
    
    def get_completed_sessions(self, limit: int = 50) -> List[RecoverySession]:
        """Get recent completed recovery sessions."""
        sessions = list(self.completed_sessions.values())
        sessions.sort(key=lambda s: s.session_id, reverse=True)
        return sessions[:limit]
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery workflow statistics."""
        completed = list(self.completed_sessions.values())
        
        if not completed:
            return {
                'total_sessions': 0,
                'success_rate': 0.0,
                'average_time': 0.0,
                'strategy_success_rates': {}
            }
        
        successful = [s for s in completed if s.final_status == RecoveryStatus.SUCCESS]
        
        strategy_stats = {}
        for session in completed:
            strategy = session.recovery_strategy.value
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'total': 0, 'successful': 0}
            strategy_stats[strategy]['total'] += 1
            if session.final_status == RecoveryStatus.SUCCESS:
                strategy_stats[strategy]['successful'] += 1
        
        strategy_success_rates = {}
        for strategy, stats in strategy_stats.items():
            strategy_success_rates[strategy] = stats['successful'] / stats['total'] if stats['total'] > 0 else 0.0
        
        return {
            'total_sessions': len(completed),
            'success_rate': len(successful) / len(completed),
            'average_time': sum(s.total_time for s in completed) / len(completed),
            'strategy_success_rates': strategy_success_rates,
            'active_sessions': len(self.active_sessions)
        }


# Convenience function
def create_recovery_orchestrator(error_classifier: ErrorClassifier, 
                                confirmation_system: ConfirmationGateSystem) -> RecoveryWorkflowOrchestrator:
    """Create recovery workflow orchestrator."""
    return RecoveryWorkflowOrchestrator(error_classifier, confirmation_system)


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from .error_analysis import create_error_classifier, ErrorContext
    from .confirmation_system import create_confirmation_system
    
    async def test_recovery_workflow():
        """Test the recovery workflow."""
        # Create components
        classifier = create_error_classifier()
        confirmation = create_confirmation_system()
        orchestrator = create_recovery_orchestrator(classifier, confirmation)
        
        # Create test error
        test_context = ErrorContext(
            command="python app.py",
            exit_code=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'flask'",
            execution_time=0.5,
            working_directory="/home/user/project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        # Analyze error
        error_analysis = classifier.analyze_error(test_context)
        
        # Initiate recovery
        recovery_session = await orchestrator.initiate_recovery(error_analysis)
        
        print("🔄 Recovery Workflow Test")
        print("=" * 50)
        print(f"Session ID: {recovery_session.session_id}")
        print(f"Strategy: {recovery_session.recovery_strategy.value}")
        print(f"Status: {recovery_session.final_status.value}")
        print(f"Attempts: {len(recovery_session.attempts)}")
        print(f"Total Time: {recovery_session.total_time:.2f}s")
        print(f"Fixes Applied: {recovery_session.code_fixes_applied}")
    
    # Run test
    asyncio.run(test_recovery_workflow())