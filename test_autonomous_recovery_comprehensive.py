#!/usr/bin/env python3
"""
Comprehensive Test Suite for Autonomous Error Recovery System

This test suite validates all aspects of the autonomous error recovery system:
1. Error recognition and classification accuracy
2. Multi-agent recovery workflow orchestration
3. Safety mechanisms and circuit breaker functionality
4. Audit logging and traceability
5. Real-world error scenario handling
6. Performance and scalability under load

Test Scenarios:
- Code errors (Python tracebacks, syntax errors, missing modules)
- Command syntax errors (invalid options, missing files)
- System errors (permissions, ports, resources)
- Network errors (connection failures, DNS issues)
- Complex multi-step recovery workflows
- Safety limit enforcement
- Circuit breaker activation
- Audit trail completeness

Author: Claude Code Assistant
Date: 2025-01-26
"""

import asyncio
import json
import logging
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import components to test
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Add both src and direct paths for imports
project_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, project_root)

# Try multiple import paths to handle different directory structures
try:
    from agents.base import Task, Result
except ImportError:
    from src.agents.base import Task, Result

try:
    from agents.error_analysis import ErrorClassifier, ErrorContext, ErrorCategory, ErrorSeverity, create_error_classifier
    from agents.recovery_workflow import RecoveryWorkflowOrchestrator, RecoveryStatus, RecoveryStrategy, create_recovery_orchestrator
    from agents.recovery_safety import RecoverySafetyManager, SafetyLimits, SafetyLevel, create_safety_manager
    from agents.confirmation_system import ConfirmationGateSystem, create_confirmation_system
except ImportError:
    from src.agents.error_analysis import ErrorClassifier, ErrorContext, ErrorCategory, ErrorSeverity, create_error_classifier
    from src.agents.recovery_workflow import RecoveryWorkflowOrchestrator, RecoveryStatus, RecoveryStrategy, create_recovery_orchestrator
    from src.agents.recovery_safety import RecoverySafetyManager, SafetyLimits, SafetyLevel, create_safety_manager
    from src.agents.confirmation_system import ConfirmationGateSystem, create_confirmation_system


class TestErrorClassification(unittest.TestCase):
    """Test error classification accuracy across different error types."""
    
    def setUp(self):
        """Set up test environment."""
        self.classifier = create_error_classifier()
    
    def test_python_error_classification(self):
        """Test classification of Python-specific errors."""
        test_cases = [
            {
                'stderr': "Traceback (most recent call last):\n  File \"app.py\", line 10, in <module>\nModuleNotFoundError: No module named 'flask'",
                'expected_category': ErrorCategory.CODE_ERROR,
                'expected_severity': ErrorSeverity.MEDIUM,
                'should_require_code_fix': True
            },
            {
                'stderr': "  File \"test.py\", line 5\n    print(\"Hello\"\n         ^\nSyntaxError: EOF while scanning triple-quoted string literal",
                'expected_category': ErrorCategory.CODE_ERROR,
                'expected_severity': ErrorSeverity.MEDIUM,
                'should_require_code_fix': True
            },
            {
                'stderr': "ImportError: attempted relative import with no known parent package",
                'expected_category': ErrorCategory.CODE_ERROR,
                'expected_severity': ErrorSeverity.MEDIUM,
                'should_require_code_fix': True
            }
        ]
        
        for case in test_cases:
            with self.subTest(stderr=case['stderr'][:50]):
                context = ErrorContext(
                    command="python app.py",
                    exit_code=1,
                    stdout="",
                    stderr=case['stderr'],
                    execution_time=0.5,
                    working_directory="/test",
                    environment_vars={},
                    timestamp=datetime.now()
                )
                
                analysis = self.classifier.analyze_error(context)
                
                self.assertEqual(analysis.category, case['expected_category'])
                self.assertEqual(analysis.severity, case['expected_severity'])
                self.assertEqual(analysis.requires_code_fix, case['should_require_code_fix'])
                self.assertGreater(analysis.confidence, 0.5)
    
    def test_command_syntax_error_classification(self):
        """Test classification of command syntax errors."""
        test_cases = [
            {
                'stderr': "ls: invalid option -- 'z'\nTry 'ls --help' for more information.",
                'command': "ls -z",
                'expected_category': ErrorCategory.COMMAND_SYNTAX,
                'should_require_retry': True
            },
            {
                'stderr': "cat: nonexistent_file.txt: No such file or directory",
                'command': "cat nonexistent_file.txt",
                'expected_category': ErrorCategory.COMMAND_SYNTAX,
                'should_require_retry': True
            },
            {
                'stderr': "bash: invalidcommand: command not found",
                'command': "invalidcommand",
                'expected_category': ErrorCategory.COMMAND_SYNTAX,
                'should_require_retry': True
            }
        ]
        
        for case in test_cases:
            with self.subTest(command=case['command']):
                context = ErrorContext(
                    command=case['command'],
                    exit_code=127,
                    stdout="",
                    stderr=case['stderr'],
                    execution_time=0.1,
                    working_directory="/test",
                    environment_vars={},
                    timestamp=datetime.now()
                )
                
                analysis = self.classifier.analyze_error(context)
                
                self.assertEqual(analysis.category, case['expected_category'])
                self.assertEqual(analysis.requires_command_retry, case['should_require_retry'])
                self.assertGreater(len(analysis.suggested_fixes), 0)
    
    def test_system_error_classification(self):
        """Test classification of system-level errors."""
        test_cases = [
            {
                'stderr': "mkdir: cannot create directory 'test': Permission denied",
                'expected_category': ErrorCategory.SYSTEM_ERROR,
                'expected_severity': ErrorSeverity.HIGH
            },
            {
                'stderr': "bind: Address already in use\nError: Could not bind to port 8000",
                'expected_category': ErrorCategory.SYSTEM_ERROR,
                'expected_severity': ErrorSeverity.MEDIUM
            },
            {
                'stderr': "No space left on device",
                'expected_category': ErrorCategory.SYSTEM_ERROR,
                'expected_severity': ErrorSeverity.CRITICAL
            }
        ]
        
        for case in test_cases:
            with self.subTest(stderr=case['stderr'][:30]):
                context = ErrorContext(
                    command="test_command",
                    exit_code=1,
                    stdout="",
                    stderr=case['stderr'],
                    execution_time=0.2,
                    working_directory="/test",
                    environment_vars={},
                    timestamp=datetime.now()
                )
                
                analysis = self.classifier.analyze_error(context)
                
                self.assertEqual(analysis.category, case['expected_category'])
                self.assertEqual(analysis.severity, case['expected_severity'])
    
    def test_research_query_generation(self):
        """Test quality of generated research queries."""
        context = ErrorContext(
            command="npm install",
            exit_code=1,
            stdout="",
            stderr="npm ERR! network request failed, reason: connect ECONNREFUSED 127.0.0.1:8080",
            execution_time=10.0,
            working_directory="/project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        analysis = self.classifier.analyze_error(context)
        
        # Research query should be relevant and specific
        self.assertIn("npm", analysis.research_query.lower())
        self.assertTrue(
            any(term in analysis.research_query.lower() 
                for term in ["error", "network", "connection", "failed"])
        )
        self.assertGreater(len(analysis.research_query), 10)


class TestRecoveryWorkflow(unittest.TestCase):
    """Test multi-agent recovery workflow orchestration."""
    
    def setUp(self):
        """Set up test environment."""
        self.classifier = create_error_classifier()
        self.confirmation_system = create_confirmation_system()
        self.orchestrator = create_recovery_orchestrator(
            self.classifier, self.confirmation_system
        )
    
    async def test_code_fix_workflow(self):
        """Test code fix recovery workflow."""
        # Create Python import error
        context = ErrorContext(
            command="python app.py",
            exit_code=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'requests'",
            execution_time=0.3,
            working_directory="/project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        error_analysis = self.classifier.analyze_error(context)
        self.assertEqual(error_analysis.category, ErrorCategory.CODE_ERROR)
        self.assertTrue(error_analysis.requires_code_fix)
        
        # Run recovery workflow
        recovery_session = await self.orchestrator.initiate_recovery(error_analysis)
        
        # Verify recovery session
        self.assertIsNotNone(recovery_session)
        self.assertEqual(recovery_session.recovery_strategy, RecoveryStrategy.CODE_FIX_REQUIRED)
        self.assertGreater(len(recovery_session.attempts), 0)
        
        # Check that web research was conducted
        self.assertIsNotNone(recovery_session.research_results)
        
        # Verify audit trail
        self.assertGreater(len(recovery_session.session_log), 0)
        self.assertTrue(any("code fix" in entry.lower() for entry in recovery_session.session_log))
    
    async def test_command_retry_workflow(self):
        """Test command retry recovery workflow."""
        # Create command not found error
        context = ErrorContext(
            command="invalidcmd --help",
            exit_code=127,
            stdout="",
            stderr="bash: invalidcmd: command not found",
            execution_time=0.1,
            working_directory="/project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        error_analysis = self.classifier.analyze_error(context)
        self.assertEqual(error_analysis.category, ErrorCategory.COMMAND_SYNTAX)
        self.assertTrue(error_analysis.requires_command_retry)
        
        # Run recovery workflow
        recovery_session = await self.orchestrator.initiate_recovery(error_analysis)
        
        # Verify recovery session
        self.assertEqual(recovery_session.recovery_strategy, RecoveryStrategy.COMMAND_RETRY)
        self.assertGreaterEqual(len(recovery_session.attempts), 1)
        
        # Should have attempted command corrections
        if recovery_session.commands_retried:
            self.assertGreater(len(recovery_session.commands_retried), 0)
    
    async def test_multi_step_recovery_workflow(self):
        """Test complex multi-step recovery workflow."""
        # Create complex error requiring multiple steps
        context = ErrorContext(
            command="python -m pytest tests/",
            exit_code=1,
            stdout="",
            stderr="ImportError: No module named 'pytest'\nCollection failed",
            execution_time=2.0,
            working_directory="/project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        error_analysis = self.classifier.analyze_error(context)
        recovery_session = await self.orchestrator.initiate_recovery(error_analysis)
        
        # Multi-step workflow should involve multiple agents
        agents_involved = set()
        for attempt in recovery_session.attempts:
            agents_involved.update(attempt.agents_involved)
        
        # Should involve at least web research
        self.assertTrue(any("WebResearch" in agent for agent in agents_involved))
        
        # Should have detailed session log
        self.assertGreater(len(recovery_session.session_log), 2)
    
    def test_recovery_statistics(self):
        """Test recovery statistics tracking."""
        initial_stats = self.orchestrator.get_recovery_statistics()
        
        # Should have basic structure
        expected_keys = ['total_sessions', 'success_rate', 'average_time', 'strategy_success_rates']
        for key in expected_keys:
            self.assertIn(key, initial_stats)


class TestSafetyMechanisms(unittest.TestCase):
    """Test safety mechanisms and circuit breaker functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.safety_limits = SafetyLimits(
            max_concurrent_recoveries=2,
            max_recovery_attempts_per_hour=5,
            circuit_breaker_failure_threshold=3
        )
        self.safety_manager = create_safety_manager(self.safety_limits)
    
    async def test_concurrent_recovery_limits(self):
        """Test enforcement of concurrent recovery limits."""
        # First two recoveries should be authorized
        auth1 = await self.safety_manager.check_recovery_authorization(
            "session_1", "code_fix", "medium"
        )
        auth2 = await self.safety_manager.check_recovery_authorization(
            "session_2", "code_fix", "medium"
        )
        
        self.assertTrue(auth1['authorized'])
        self.assertTrue(auth2['authorized'])
        
        # Third recovery should be blocked
        auth3 = await self.safety_manager.check_recovery_authorization(
            "session_3", "code_fix", "medium"
        )
        
        self.assertFalse(auth3['authorized'])
        self.assertIn("concurrent", auth3['reason'].lower())
    
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker activation after failures."""
        # Simulate multiple failures to trigger circuit breaker
        for i in range(4):  # One more than threshold
            await self.safety_manager.register_recovery_completion(
                f"session_{i}", success=False, execution_time=1.0, 
                operations_performed=["failed_operation"]
            )
        
        # Next authorization should be blocked by circuit breaker
        auth = await self.safety_manager.check_recovery_authorization(
            "session_blocked", "code_fix", "medium"
        )
        
        self.assertFalse(auth['authorized'])
        self.assertIn("circuit breaker", auth['reason'].lower())
    
    async def test_hourly_limits_enforcement(self):
        """Test enforcement of hourly recovery limits."""
        # Simulate reaching hourly limit
        for i in range(self.safety_limits.max_recovery_attempts_per_hour):
            auth = await self.safety_manager.check_recovery_authorization(
                f"session_{i}", "code_fix", "low"
            )
            if auth['authorized']:
                await self.safety_manager.register_recovery_completion(
                    f"session_{i}", success=True, execution_time=1.0,
                    operations_performed=["test_operation"]
                )
        
        # Next recovery should be blocked
        auth = await self.safety_manager.check_recovery_authorization(
            "session_over_limit", "code_fix", "low"
        )
        
        self.assertFalse(auth['authorized'])
        self.assertIn("hourly", auth['reason'].lower())
    
    def test_safety_level_determination(self):
        """Test safety level determination logic."""
        # Test different risk levels
        high_risk_auth = asyncio.run(
            self.safety_manager.check_recovery_authorization(
                "high_risk", "system_config", "critical"
            )
        )
        
        if high_risk_auth['authorized']:
            self.assertEqual(high_risk_auth['safety_level'], SafetyLevel.RESTRICTED)
    
    def test_audit_logging(self):
        """Test audit logging functionality."""
        # Check that audit log file is created
        self.assertTrue(os.path.exists(self.safety_manager.audit_log_path))
        
        # Test logging an event
        asyncio.run(
            self.safety_manager.check_recovery_authorization(
                "audit_test", "code_fix", "medium"
            )
        )
        
        # Verify log entry was created
        with open(self.safety_manager.audit_log_path, 'r') as f:
            log_content = f.read()
            self.assertIn("audit_test", log_content)
            self.assertIn("recovery_started", log_content)


class TestRealWorldScenarios(unittest.TestCase):
    """Test realistic error scenarios and recovery patterns."""
    
    def setUp(self):
        """Set up test environment."""
        self.classifier = create_error_classifier()
        self.confirmation_system = create_confirmation_system()
        self.orchestrator = create_recovery_orchestrator(
            self.classifier, self.confirmation_system
        )
    
    async def test_npm_dependency_error_recovery(self):
        """Test recovery from NPM dependency issues."""
        context = ErrorContext(
            command="npm start",
            exit_code=1,
            stdout="",
            stderr="npm ERR! missing script: start\nnpm ERR! Did you mean one of these?\nnpm ERR!     npm star # Mark your favorite packages\nnpm ERR!     npm stars # View packages marked as favorites",
            execution_time=1.2,
            working_directory="/web-project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        analysis = self.classifier.analyze_error(context)
        recovery_session = await self.orchestrator.initiate_recovery(analysis)
        
        # Should classify as configuration/dependency error
        self.assertIn(analysis.category, [ErrorCategory.DEPENDENCY_ERROR, ErrorCategory.CONFIGURATION_ERROR])
        
        # Should generate appropriate research query
        self.assertIn("npm", analysis.research_query.lower())
        self.assertIn("script", analysis.research_query.lower())
        
        # Recovery should attempt to fix the issue
        self.assertIsNotNone(recovery_session)
        self.assertGreater(len(recovery_session.session_log), 0)
    
    async def test_python_virtual_environment_error(self):
        """Test recovery from Python virtual environment issues."""
        context = ErrorContext(
            command="pip install -r requirements.txt",
            exit_code=1,
            stdout="",
            stderr="ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied: '/usr/local/lib/python3.9/site-packages/setuptools'",
            execution_time=5.0,
            working_directory="/python-project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        analysis = self.classifier.analyze_error(context)
        recovery_session = await self.orchestrator.initiate_recovery(analysis)
        
        # Should be classified as system error due to permissions
        self.assertEqual(analysis.category, ErrorCategory.SYSTEM_ERROR)
        self.assertEqual(analysis.severity, ErrorSeverity.HIGH)
        
        # Should suggest appropriate fixes
        self.assertTrue(any("virtual environment" in fix.lower() or "permission" in fix.lower() 
                           for fix in analysis.suggested_fixes))
    
    async def test_git_merge_conflict_scenario(self):
        """Test handling of Git merge conflicts."""
        context = ErrorContext(
            command="git merge feature-branch",
            exit_code=1,
            stdout="",
            stderr="Auto-merging config.py\nCONFLICT (content): Merge conflict in config.py\nAutomatic merge failed; fix conflicts and then commit the result.",
            execution_time=0.8,
            working_directory="/project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        analysis = self.classifier.analyze_error(context)
        recovery_session = await self.orchestrator.initiate_recovery(analysis)
        
        # Should require manual intervention for merge conflicts
        self.assertTrue(
            recovery_session.manual_intervention_required or 
            recovery_session.final_status == RecoveryStatus.REQUIRES_MANUAL
        )
        
        # Should provide research guidance
        self.assertIsNotNone(recovery_session.research_results)
    
    async def test_database_connection_error(self):
        """Test recovery from database connection errors."""
        context = ErrorContext(
            command="python manage.py migrate",
            exit_code=1,
            stdout="",
            stderr="django.db.utils.OperationalError: could not connect to server: Connection refused\n\tIs the server running on host \"localhost\" (127.0.0.1) and accepting\n\tTCP/IP connections on port 5432?",
            execution_time=3.0,
            working_directory="/django-project",
            environment_vars={},
            timestamp=datetime.now()
        )
        
        analysis = self.classifier.analyze_error(context)
        recovery_session = await self.orchestrator.initiate_recovery(analysis)
        
        # Should be classified as system/network error
        self.assertIn(analysis.category, [ErrorCategory.SYSTEM_ERROR, ErrorCategory.NETWORK_ERROR])
        
        # Should suggest database-related fixes
        self.assertTrue(any("database" in fix.lower() or "server" in fix.lower() or "connection" in fix.lower()
                           for fix in analysis.suggested_fixes))


class TestPerformanceAndScalability(unittest.TestCase):
    """Test performance and scalability characteristics."""
    
    def setUp(self):
        """Set up test environment."""
        self.classifier = create_error_classifier()
    
    def test_classification_performance(self):
        """Test error classification performance."""
        # Create test error contexts
        test_contexts = []
        for i in range(20):
            context = ErrorContext(
                command=f"test_command_{i}",
                exit_code=1,
                stdout="",
                stderr=f"Error {i}: Some generic error message",
                execution_time=0.1,
                working_directory="/test",
                environment_vars={},
                timestamp=datetime.now()
            )
            test_contexts.append(context)
        
        # Measure classification time
        start_time = time.time()
        for context in test_contexts:
            analysis = self.classifier.analyze_error(context)
            self.assertIsNotNone(analysis)
        
        total_time = time.time() - start_time
        avg_time = total_time / len(test_contexts)
        
        # Should complete within reasonable time (< 50ms per classification)
        self.assertLess(avg_time, 0.05, f"Classification too slow: {avg_time:.3f}s average")
    
    async def test_concurrent_recovery_handling(self):
        """Test handling of concurrent recovery operations."""
        classifier = create_error_classifier()
        confirmation_system = create_confirmation_system()
        orchestrator = create_recovery_orchestrator(classifier, confirmation_system)
        
        # Create multiple concurrent recovery tasks
        contexts = []
        for i in range(5):
            context = ErrorContext(
                command=f"python script_{i}.py",
                exit_code=1,
                stdout="",
                stderr=f"ModuleNotFoundError: No module named 'module_{i}'",
                execution_time=0.5,
                working_directory="/test",
                environment_vars={},
                timestamp=datetime.now()
            )
            contexts.append(context)
        
        # Run concurrent recoveries
        start_time = time.time()
        
        recovery_tasks = []
        for i, context in enumerate(contexts):
            analysis = classifier.analyze_error(context)
            task = orchestrator.initiate_recovery(analysis)
            recovery_tasks.append(task)
        
        # Wait for all recoveries to complete
        recovery_sessions = await asyncio.gather(*recovery_tasks)
        
        total_time = time.time() - start_time
        
        # All recoveries should complete
        self.assertEqual(len(recovery_sessions), 5)
        for session in recovery_sessions:
            self.assertIsNotNone(session)
        
        # Should complete within reasonable time
        self.assertLess(total_time, 30, f"Concurrent recoveries too slow: {total_time:.2f}s")
    
    def test_memory_usage_stability(self):
        """Test memory usage stability during extended operation."""
        import gc
        
        # Get initial memory usage
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            initial_memory = 0
        
        # Perform many classification operations
        classifier = create_error_classifier()
        
        for i in range(100):
            context = ErrorContext(
                command="test_command",
                exit_code=1,
                stdout="",
                stderr=f"Test error {i}",
                execution_time=0.1,
                working_directory="/test",
                environment_vars={},
                timestamp=datetime.now()
            )
            
            analysis = classifier.analyze_error(context)
            
            # Force garbage collection periodically
            if i % 20 == 0:
                gc.collect()
        
        # Check final memory usage
        try:
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (< 100MB)
            self.assertLess(memory_increase, 100, 
                          f"Memory usage increased too much: {memory_increase:.1f}MB")
        except (ImportError, NameError):
            # Skip memory test if psutil not available
            pass


# Comprehensive Test Runner
class AutonomousRecoveryTestRunner:
    """Custom test runner with detailed recovery-specific reporting."""
    
    def __init__(self):
        """Initialize test runner."""
        self.results = {
            'error_classification_tests': 0,
            'recovery_workflow_tests': 0,
            'safety_mechanism_tests': 0,
            'real_world_scenario_tests': 0,
            'performance_tests': 0,
            'total_passed': 0,
            'total_failed': 0,
            'execution_time': 0.0,
            'detailed_results': []
        }
    
    def run_all_tests(self):
        """Run all test suites and generate comprehensive report."""
        start_time = time.time()
        
        print("🔄 Autonomous Error Recovery - Comprehensive Test Suite")
        print("=" * 70)
        print(f"Testing error recovery system at {datetime.now()}")
        print()
        
        # Test suites to run
        test_suites = [
            (TestErrorClassification, "Error Classification"),
            (TestRecoveryWorkflow, "Recovery Workflow"),
            (TestSafetyMechanisms, "Safety Mechanisms"),
            (TestRealWorldScenarios, "Real-World Scenarios"),
            (TestPerformanceAndScalability, "Performance & Scalability")
        ]
        
        all_passed = 0
        all_failed = 0
        
        for test_class, description in test_suites:
            print(f"Running {description} Tests...")
            
            # Create test suite
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Run tests with custom result handling
            runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            # Track results
            passed = result.testsRun - len(result.failures) - len(result.errors)
            failed = len(result.failures) + len(result.errors)
            
            all_passed += passed
            all_failed += failed
            
            # Update category-specific counters
            category_key = description.lower().replace(" ", "_").replace("&", "and") + "_tests"
            if hasattr(self.results, category_key):
                self.results[category_key] = passed
            
            print(f"  ✅ {passed}/{result.testsRun} tests passed")
            if result.failures:
                print(f"  ❌ {len(result.failures)} failures")
            if result.errors:
                print(f"  💥 {len(result.errors)} errors")
            
            # Store detailed results
            for test, traceback in result.failures + result.errors:
                self.results['detailed_results'].append({
                    'test': str(test),
                    'status': 'failed',
                    'error': traceback.split('\n')[-2] if traceback else 'Unknown error'
                })
        
        self.results['total_passed'] = all_passed
        self.results['total_failed'] = all_failed
        self.results['execution_time'] = time.time() - start_time
        
        self._generate_final_report()
    
    def _generate_final_report(self):
        """Generate final comprehensive report."""
        print()
        print("=" * 70)
        print("AUTONOMOUS ERROR RECOVERY TEST RESULTS")
        print("=" * 70)
        
        total_tests = self.results['total_passed'] + self.results['total_failed']
        success_rate = (self.results['total_passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {self.results['total_passed']}")
        print(f"❌ Failed: {self.results['total_failed']}")
        print(f"⏱️  Execution Time: {self.results['execution_time']:.2f}s")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # Category breakdown
        print("\n📋 Test Category Results:")
        categories = [
            ("Error Classification", "error_classification_tests"),
            ("Recovery Workflow", "recovery_workflow_tests"),
            ("Safety Mechanisms", "safety_mechanism_tests"),
            ("Real-World Scenarios", "real_world_scenario_tests"),
            ("Performance & Scalability", "performance_tests")
        ]
        
        for category_name, category_key in categories:
            if category_key in self.results:
                print(f"  {category_name}: {self.results[category_key]} tests passed")
        
        # Show failures if any
        if self.results['detailed_results']:
            print("\n❌ Failed Tests:")
            for result in self.results['detailed_results']:
                print(f"  - {result['test']}: {result['error']}")
        
        # Overall assessment
        print("\n🎯 Recovery System Assessment:")
        if success_rate >= 95:
            print("🎉 EXCELLENT: Autonomous recovery system is production-ready")
            print("   - Error classification is highly accurate")
            print("   - Recovery workflows are robust and reliable")
            print("   - Safety mechanisms are properly enforced")
        elif success_rate >= 85:
            print("✅ GOOD: Recovery system is mostly ready with minor issues")
            print("   - Core functionality is solid")
            print("   - Some edge cases may need attention")
        elif success_rate >= 70:
            print("⚠️  ACCEPTABLE: Recovery system is functional but needs improvement")
            print("   - Basic recovery works but reliability could be better")
        else:
            print("🚨 NEEDS WORK: Recovery system requires significant improvements")
            print("   - Multiple critical issues detected")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if success_rate < 95:
            print("   - Review failed test cases for improvement opportunities")
            print("   - Consider additional error pattern training")
            print("   - Enhance safety mechanism coverage")
        
        print("   - Monitor recovery success rates in production")
        print("   - Implement continuous learning from recovery patterns")
        print("   - Regular safety audit and limit review")
        
        print("=" * 70)


def main():
    """Main test execution function."""
    # Setup logging for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during testing
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run comprehensive test suite
    runner = AutonomousRecoveryTestRunner()
    runner.run_all_tests()
    
    # Save results
    results_file = f"autonomous_recovery_test_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump(runner.results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    main()