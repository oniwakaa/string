"""
Integration tests for the intent-based routing system.

These tests validate the end-to-end functionality of the model-based
prompt routing, including intent classification, agent selection, and
workflow execution.
"""

import asyncio
import pytest
import json
import os
import sys
from typing import List, Dict, Any
from uuid import UUID

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from agents.orchestrator import ProjectManager
from agents.base import Task, Result
from inference.intent_classifier import create_intent_classifier, IntentClassification


class MockAgent:
    """Mock agent for testing purposes."""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.status = 'ready'
        self.executed_tasks = []
    
    async def execute(self, task: Task) -> Result:
        """Mock execution that records the task."""
        self.executed_tasks.append(task)
        return Result(
            task_id=task.task_id,
            status="success",
            output=f"Mock {self.role} output for: {task.prompt}"
        )


@pytest.fixture
def mock_project_manager():
    """Create a ProjectManager with mock agents for testing."""
    pm = ProjectManager()
    
    # Replace real agents with mocks
    pm.agents = {
        'code_generator': MockAgent("MockCodeGen", "code_generator"),
        'code_quality_analyzer': MockAgent("MockQuality", "code_quality_analyzer"),
        'code_editor': MockAgent("MockEditor", "code_editor"),
        'documentation': MockAgent("MockDocs", "documentation"),
        'codebase_expert': MockAgent("MockExpert", "codebase_expert"),
        'web_researcher': MockAgent("MockWeb", "web_researcher"),
        'tool_executor': MockAgent("MockTool", "tool_executor")
    }
    
    return pm


class TestIntentRoutingIntegration:
    """Test the integration of intent classification with orchestration."""
    
    @pytest.mark.asyncio
    async def test_code_generation_routing(self, mock_project_manager):
        """Test that code generation prompts route correctly."""
        prompts = [
            "create a function to validate email addresses",
            "generate a REST API endpoint for user management",
            "implement a binary search algorithm",
            "build a React component for displaying charts"
        ]
        
        for prompt in prompts:
            plan = await mock_project_manager._decompose_prompt(prompt)
            
            # Should have at least one step
            assert len(plan) > 0
            
            # Primary agent should be code_generator
            primary_step = plan[0]
            assert primary_step['agent_role'] == 'code_generator'
            assert primary_step['prompt'] == prompt
    
    @pytest.mark.asyncio
    async def test_codebase_query_routing(self, mock_project_manager):
        """Test that codebase queries route correctly."""
        prompts = [
            "find the authentication function in the project",
            "where is the database connection class?",
            "explain how the payment processing works",
            "show me the user model implementation"
        ]
        
        for prompt in prompts:
            plan = await mock_project_manager._decompose_prompt(prompt)
            
            # Should route to codebase_expert
            assert len(plan) > 0
            assert plan[0]['agent_role'] == 'codebase_expert'
    
    @pytest.mark.asyncio
    async def test_code_editing_with_context(self, mock_project_manager):
        """Test code editing prompts that need context."""
        prompt = "fix the bug in the login function"
        plan = await mock_project_manager._decompose_prompt(prompt)
        
        # Should have two steps: find code, then edit
        assert len(plan) >= 2
        assert plan[0]['agent_role'] == 'codebase_expert'
        assert plan[1]['agent_role'] == 'code_editor'
        assert plan[1]['dependencies'] == [1]
    
    @pytest.mark.asyncio
    async def test_web_research_workflow(self, mock_project_manager):
        """Test web research with follow-up processing."""
        prompt = "scrape the documentation from https://example.com and generate a summary"
        plan = await mock_project_manager._decompose_prompt(prompt)
        
        # Should have web research followed by generation
        assert len(plan) >= 2
        assert plan[0]['agent_role'] == 'web_researcher'
        assert plan[1]['agent_role'] == 'code_generator'
        assert plan[1]['dependencies'] == [1]
    
    @pytest.mark.asyncio
    async def test_multi_intent_workflow(self, mock_project_manager):
        """Test prompts with multiple intents."""
        prompt = "create a function to parse JSON and analyze it for security issues"
        plan = await mock_project_manager._decompose_prompt(prompt)
        
        # Should generate code and then analyze
        agent_roles = [step['agent_role'] for step in plan]
        assert 'code_generator' in agent_roles
        
        # Depending on classification confidence, might also include analysis
        # This is implementation-dependent based on secondary intent detection
    
    @pytest.mark.asyncio
    async def test_context_modifier_detection(self, mock_project_manager):
        """Test detection of context modifiers."""
        prompt = "create a function based on the existing authentication code"
        plan = await mock_project_manager._decompose_prompt(prompt)
        
        # Should retrieve context first
        assert len(plan) >= 2
        assert plan[0]['agent_role'] == 'codebase_expert'
        assert plan[1]['agent_role'] == 'code_generator'
    
    @pytest.mark.asyncio
    async def test_fallback_routing(self, mock_project_manager):
        """Test fallback for ambiguous prompts."""
        ambiguous_prompts = [
            "help me with this",
            "what should I do next?",
            "can you assist?"
        ]
        
        for prompt in ambiguous_prompts:
            plan = await mock_project_manager._decompose_prompt(prompt)
            
            # Should fall back to default routing
            assert len(plan) > 0
            # Default is codebase_expert -> code_generator
            assert plan[0]['agent_role'] in ['codebase_expert', 'code_generator']
    
    @pytest.mark.asyncio
    async def test_full_execution_pipeline(self, mock_project_manager):
        """Test the full execution pipeline from prompt to result."""
        prompt = "find the user model and add a new field for phone number"
        
        result = await mock_project_manager.handle_request(
            user_prompt=prompt,
            user_id="test_user",
            project_id="test_project"
        )
        
        # Check result structure
        assert result['status'] == 'success'
        assert 'result' in result
        assert 'execution_plan' in result
        
        # Verify agents were called
        expert_agent = mock_project_manager.agents['codebase_expert']
        editor_agent = mock_project_manager.agents['code_editor']
        
        assert len(expert_agent.executed_tasks) > 0
        assert len(editor_agent.executed_tasks) > 0


class TestClassifierAccuracy:
    """Test the accuracy of intent classification on various prompts."""
    
    @pytest.fixture
    def test_prompts(self):
        """Load test prompts with expected classifications."""
        return [
            # Web research prompts
            {
                "prompt": "scrape product data from https://shop.example.com",
                "expected_intent": "web_research",
                "min_confidence": 0.7
            },
            {
                "prompt": "fetch and extract the main content from this webpage",
                "expected_intent": "web_research",
                "min_confidence": 0.7
            },
            
            # Code generation prompts
            {
                "prompt": "create a Python class for managing user sessions",
                "expected_intent": "code_generation",
                "min_confidence": 0.8
            },
            {
                "prompt": "implement a sorting algorithm that handles duplicates",
                "expected_intent": "code_generation",
                "min_confidence": 0.8
            },
            {
                "prompt": "genera una funzione per validare i numeri di telefono",
                "expected_intent": "code_generation",
                "min_confidence": 0.7
            },
            
            # Code editing prompts
            {
                "prompt": "fix the memory leak in the connection handler",
                "expected_intent": "code_editing",
                "min_confidence": 0.7
            },
            {
                "prompt": "refactor this method to use async/await",
                "expected_intent": "code_editing",
                "min_confidence": 0.7
            },
            {
                "prompt": "modifica la funzione per gestire gli errori",
                "expected_intent": "code_editing",
                "min_confidence": 0.7
            },
            
            # Codebase queries
            {
                "prompt": "where is the configuration file loaded?",
                "expected_intent": "codebase_query",
                "min_confidence": 0.7
            },
            {
                "prompt": "explain how the authentication middleware works",
                "expected_intent": "codebase_query",
                "min_confidence": 0.7
            },
            {
                "prompt": "trova la classe che gestisce i pagamenti",
                "expected_intent": "codebase_query",
                "min_confidence": 0.7
            },
            
            # Code analysis prompts
            {
                "prompt": "analyze this code for potential security vulnerabilities",
                "expected_intent": "code_analysis",
                "min_confidence": 0.7
            },
            {
                "prompt": "review the performance of the search algorithm",
                "expected_intent": "code_analysis",
                "min_confidence": 0.7
            },
            
            # Documentation prompts
            {
                "prompt": "document the API endpoints in this module",
                "expected_intent": "documentation",
                "min_confidence": 0.8
            },
            {
                "prompt": "create usage examples for the utility functions",
                "expected_intent": "documentation",
                "min_confidence": 0.7
            },
            
            # Complex multi-intent prompts
            {
                "prompt": "find the database models and generate TypeScript interfaces for them",
                "expected_intent": "codebase_query",  # Primary intent
                "secondary_intents": ["code_generation"],
                "min_confidence": 0.6
            },
            {
                "prompt": "create a new endpoint and write tests for it",
                "expected_intent": "code_generation",
                "secondary_intents": ["code_generation"],  # Tests are also generation
                "min_confidence": 0.7
            }
        ]
    
    def test_keyword_classifier_accuracy(self, test_prompts):
        """Test keyword-based classifier accuracy."""
        classifier = create_intent_classifier("keyword")
        
        correct_classifications = 0
        total_prompts = len(test_prompts)
        
        for test_case in test_prompts:
            prompt = test_case["prompt"]
            expected = test_case["expected_intent"]
            min_confidence = test_case.get("min_confidence", 0.5)
            
            result = classifier.classify(prompt)
            
            # Check primary intent
            if result.primary_intent == expected and result.confidence >= min_confidence:
                correct_classifications += 1
            else:
                print(f"Misclassified: '{prompt}' -> {result.primary_intent} ({result.confidence:.2f}), expected {expected}")
        
        accuracy = correct_classifications / total_prompts
        print(f"Keyword classifier accuracy: {accuracy:.2%} ({correct_classifications}/{total_prompts})")
        
        # Keyword classifier should achieve at least 70% accuracy
        assert accuracy >= 0.7
    
    @pytest.mark.skipif(
        os.getenv("SKIP_MODEL_TESTS", "true").lower() == "true",
        reason="Model tests skipped (set SKIP_MODEL_TESTS=false to run)"
    )
    def test_gemma_classifier_accuracy(self, test_prompts):
        """Test Gemma model-based classifier accuracy."""
        try:
            classifier = create_intent_classifier("gemma")
        except Exception as e:
            pytest.skip(f"Gemma classifier not available: {e}")
        
        correct_classifications = 0
        total_prompts = len(test_prompts)
        
        for test_case in test_prompts:
            prompt = test_case["prompt"]
            expected = test_case["expected_intent"]
            min_confidence = test_case.get("min_confidence", 0.5)
            
            result = classifier.classify(prompt)
            
            # Check primary intent
            if result.primary_intent == expected and result.confidence >= min_confidence:
                correct_classifications += 1
            else:
                print(f"Misclassified: '{prompt}' -> {result.primary_intent} ({result.confidence:.2f}), expected {expected}")
            
            # Check secondary intents if specified
            if "secondary_intents" in test_case:
                expected_secondary = test_case["secondary_intents"]
                actual_secondary = [intent for intent, _ in result.secondary_intents]
                
                for expected_intent in expected_secondary:
                    if expected_intent not in actual_secondary:
                        print(f"  Missing secondary intent: {expected_intent}")
        
        accuracy = correct_classifications / total_prompts
        print(f"Gemma classifier accuracy: {accuracy:.2%} ({correct_classifications}/{total_prompts})")
        
        # Model-based classifier should achieve at least 80% accuracy
        assert accuracy >= 0.8


class TestIntentRoutingPerformance:
    """Performance tests for the routing system."""
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_routing_performance(self, mock_project_manager, benchmark):
        """Benchmark the routing performance."""
        prompts = [
            "create a function to validate emails",
            "find the user authentication code",
            "fix the bug in the payment processor",
            "analyze this code for security issues",
            "document the API endpoints"
        ]
        
        async def route_prompts():
            plans = []
            for prompt in prompts:
                plan = await mock_project_manager._decompose_prompt(prompt)
                plans.append(plan)
            return plans
        
        # Benchmark the routing
        plans = await benchmark(route_prompts)
        
        # Verify all prompts were routed
        assert len(plans) == len(prompts)
        for plan in plans:
            assert len(plan) > 0


def create_validation_report():
    """Create a validation report summarizing test results."""
    report = {
        "test_suite": "Intent Routing Validation",
        "test_categories": [
            {
                "name": "Routing Accuracy",
                "description": "Tests that prompts route to correct agents",
                "test_count": 8
            },
            {
                "name": "Classifier Accuracy",
                "description": "Tests intent classification accuracy",
                "test_count": 2
            },
            {
                "name": "Performance",
                "description": "Tests routing system performance",
                "test_count": 1
            }
        ],
        "coverage": {
            "intents_tested": [
                "web_research",
                "codebase_query",
                "code_generation",
                "code_editing",
                "code_analysis",
                "documentation"
            ],
            "workflows_tested": [
                "single_agent",
                "multi_step",
                "context_dependent",
                "multi_intent"
            ]
        }
    }
    
    return report


if __name__ == "__main__":
    # Run tests and generate report
    pytest.main([__file__, "-v", "--tb=short"])
    
    # Generate validation report
    report = create_validation_report()
    with open("intent_routing_validation.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nValidation report generated: intent_routing_validation.json")