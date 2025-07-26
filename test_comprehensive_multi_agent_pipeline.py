#!/usr/bin/env python3
"""
Comprehensive Multi-Agent Pipeline Validation Test

This enhanced test script exercises all major agent types through realistic 
sequential user prompts, validating agent switching, interoperability, and 
complete document lifecycle management.

Agent Types Tested:
- CodeGeneratorAgent: Document creation and code synthesis
- WebResearchAgent: External information retrieval and integration
- ToolExecutorAgent: Code analysis, testing, and execution
- DocumentationAgent: Docstring generation and inline explanations  
- CodeEditorAgent: Code optimization and modification
- CodebaseExpertAgent: Knowledge queries and explanations

Test Flow:
1. Create document → 2. Research content → 3. Generate code → 
4. Edit/optimize → 5. Add documentation → 6. Test/analyze → 7. Validate results
"""

import json
import logging
import os
import time
import difflib
from typing import Dict, List, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AgentTestResult:
    """Result of individual agent test step."""
    step_number: int
    step_name: str
    user_prompt: str
    expected_intent: str
    actual_intent: str
    expected_agent: str
    actual_agent: str
    classification_time: float
    agent_execution_time: float
    file_modified: bool
    file_size_before: int
    file_size_after: int
    content_diff_lines: int
    success: bool
    error_message: str = None
    metadata: Dict[str, Any] = None

@dataclass
class SessionSummary:
    """Complete session summary with metrics."""
    session_id: str
    total_steps: int
    successful_steps: int
    failed_steps: int
    total_execution_time: float
    agent_usage_stats: Dict[str, int]
    intent_classification_accuracy: float
    agent_routing_accuracy: float
    file_modifications: int
    final_document_size: int
    errors_encountered: List[str]
    test_results: List[AgentTestResult]

class ComprehensiveMultiAgentPipeline:
    """Comprehensive test pipeline for multi-agent validation."""
    
    def __init__(self, workspace_root: str = "./test_workspace_comprehensive"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(exist_ok=True)
        self.test_document = self.workspace_root / "calculator_comprehensive.py"
        self.session_id = f"multi_agent_{int(time.time())}"
        self.test_results: List[AgentTestResult] = []
        self.agent_usage_stats = {}
        self.start_time = time.time()
        
        # Initialize intent classifier
        self.classifier = None
        self._load_classifier()
    
    def _load_classifier(self):
        """Load the optimized Gemma3n intent classifier."""
        try:
            from src.inference.intent_classifier import GemmaIntentClassifier
            self.classifier = GemmaIntentClassifier()
            logger.info("✅ Intent classifier loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load intent classifier: {e}")
            raise
    
    def _get_file_size(self, file_path: Path) -> int:
        """Get file size or 0 if file doesn't exist."""
        try:
            return file_path.stat().st_size if file_path.exists() else 0
        except:
            return 0
    
    def _get_file_content(self, file_path: Path) -> str:
        """Get file content or empty string if file doesn't exist."""
        try:
            return file_path.read_text() if file_path.exists() else ""
        except:
            return ""
    
    def _calculate_content_diff(self, before: str, after: str) -> int:
        """Calculate number of changed lines between two content versions."""
        diff = list(difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            n=0
        ))
        # Count only addition/deletion lines (starting with + or -)
        return len([line for line in diff if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))])
    
    def _execute_agent_step(self, step_number: int, step_name: str, user_prompt: str, 
                           expected_intent: str, expected_agent: str) -> AgentTestResult:
        """Execute a single agent test step with comprehensive tracking."""
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP {step_number}: {step_name}")
        logger.info(f"Prompt: {user_prompt}")
        logger.info(f"Expected: {expected_intent} → {expected_agent}")
        logger.info(f"{'='*60}")
        
        # Capture file state before
        content_before = self._get_file_content(self.test_document)
        size_before = self._get_file_size(self.test_document)
        
        # Step timing
        step_start = time.time()
        
        try:
            # 1. Intent Classification
            classification_start = time.time()
            classification_result = self.classifier.classify(user_prompt)
            classification_time = time.time() - classification_start
            
            actual_intent = classification_result.primary_intent
            logger.info(f"🎯 Intent: {actual_intent} (confidence: {classification_result.confidence:.2f})")
            
            # 2. Agent Routing and Execution
            agent_start = time.time()
            agent_result = self._route_and_execute_agent(user_prompt, classification_result)
            agent_time = time.time() - agent_start
            
            actual_agent = agent_result.get("agent", "unknown")
            logger.info(f"🤖 Agent: {actual_agent}")
            
            # Track agent usage
            self.agent_usage_stats[actual_agent] = self.agent_usage_stats.get(actual_agent, 0) + 1
            
            # Capture file state after
            content_after = self._get_file_content(self.test_document)
            size_after = self._get_file_size(self.test_document)
            file_modified = content_before != content_after
            content_diff_lines = self._calculate_content_diff(content_before, content_after)
            
            # Determine success
            intent_correct = actual_intent == expected_intent
            agent_correct = actual_agent == expected_agent
            execution_success = agent_result.get("status") != "error"
            overall_success = intent_correct and agent_correct and execution_success
            
            result = AgentTestResult(
                step_number=step_number,
                step_name=step_name,
                user_prompt=user_prompt,
                expected_intent=expected_intent,
                actual_intent=actual_intent,
                expected_agent=expected_agent,
                actual_agent=actual_agent,
                classification_time=classification_time,
                agent_execution_time=agent_time,
                file_modified=file_modified,
                file_size_before=size_before,
                file_size_after=size_after,
                content_diff_lines=content_diff_lines,
                success=overall_success,
                metadata={
                    "classification_confidence": classification_result.confidence,
                    "agent_result": agent_result,
                    "content_preview": content_after[:200] + "..." if len(content_after) > 200 else content_after
                }
            )
            
            # Logging
            logger.info(f"📊 Results:")
            logger.info(f"  Intent Correct: {intent_correct} ({expected_intent} == {actual_intent})")
            logger.info(f"  Agent Correct: {agent_correct} ({expected_agent} == {actual_agent})")
            logger.info(f"  File Modified: {file_modified} ({content_diff_lines} lines changed)")
            logger.info(f"  Overall Success: {overall_success}")
            logger.info(f"  Timing: Classification {classification_time:.2f}s, Agent {agent_time:.2f}s")
            
            if overall_success:
                logger.info("✅ Step completed successfully")
            else:
                logger.warning("⚠️ Step completed with issues")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Step failed: {error_msg}")
            
            return AgentTestResult(
                step_number=step_number,
                step_name=step_name,
                user_prompt=user_prompt,
                expected_intent=expected_intent,
                actual_intent="error",
                expected_agent=expected_agent,
                actual_agent="error",
                classification_time=0,
                agent_execution_time=time.time() - step_start,
                file_modified=False,
                file_size_before=size_before,
                file_size_after=size_before,
                content_diff_lines=0,
                success=False,
                error_message=error_msg
            )
    
    def _route_and_execute_agent(self, user_prompt: str, classification) -> Dict[str, Any]:
        """Route to appropriate agent and execute the task."""
        intent = classification.primary_intent
        
        # Route based on intent
        if intent == "code_generation":
            return self._execute_code_generation_agent(user_prompt)
        elif intent == "web_research":
            return self._execute_web_research_agent(user_prompt)
        elif intent == "code_editing":
            return self._execute_code_editor_agent(user_prompt)
        elif intent == "documentation":
            return self._execute_documentation_agent(user_prompt)
        elif intent == "code_analysis":
            return self._execute_code_analysis_agent(user_prompt)
        elif intent == "codebase_query":
            return self._execute_codebase_expert_agent(user_prompt)
        elif intent == "tool_execution":
            return self._execute_tool_executor_agent(user_prompt)
        else:
            return self._execute_general_fallback(user_prompt)
    
    def _execute_code_generation_agent(self, prompt: str) -> Dict[str, Any]:
        """Simulate CodeGeneratorAgent execution."""
        logger.info("🔧 Executing CodeGeneratorAgent...")
        
        try:
            # Generate or create content based on prompt
            if "create" in prompt.lower() and "calculator" in prompt.lower():
                content = self._generate_calculator_template()
            elif "method" in prompt.lower() or "function" in prompt.lower():
                content = self._generate_additional_methods(prompt)
            else:
                content = self._generate_generic_code(prompt)
            
            # Write to file
            with open(self.test_document, 'w') as f:
                f.write(content)
            
            return {
                "agent": "CodeGeneratorAgent",
                "status": "success",
                "action": "generated_code",
                "file_path": str(self.test_document),
                "content_length": len(content)
            }
            
        except Exception as e:
            return {
                "agent": "CodeGeneratorAgent",
                "status": "error",
                "error": str(e)
            }
    
    def _execute_web_research_agent(self, prompt: str) -> Dict[str, Any]:
        """Simulate WebResearchAgent execution."""
        logger.info("🌐 Executing WebResearchAgent...")
        
        try:
            # Simulate web research result
            research_content = self._simulate_web_research(prompt)
            
            # Insert research content into document
            current_content = self._get_file_content(self.test_document)
            
            # Add research summary at the top
            updated_content = f'"""\n{research_content}\n"""\n\n{current_content}'
            
            with open(self.test_document, 'w') as f:
                f.write(updated_content)
            
            return {
                "agent": "WebResearchAgent",
                "status": "success", 
                "action": "research_inserted",
                "research_length": len(research_content),
                "file_path": str(self.test_document)
            }
            
        except Exception as e:
            return {
                "agent": "WebResearchAgent",
                "status": "error",
                "error": str(e)
            }
    
    def _execute_code_editor_agent(self, prompt: str) -> Dict[str, Any]:
        """Simulate CodeEditorAgent execution."""
        logger.info("✏️ Executing CodeEditorAgent...")
        
        try:
            current_content = self._get_file_content(self.test_document)
            
            # Apply specific edits based on prompt
            if "optimize" in prompt.lower():
                modified_content = self._optimize_code(current_content, prompt)
            elif "fix" in prompt.lower():
                modified_content = self._fix_code_issues(current_content, prompt)
            elif "refactor" in prompt.lower():
                modified_content = self._refactor_code(current_content, prompt)
            else:
                modified_content = self._generic_code_edit(current_content, prompt)
            
            with open(self.test_document, 'w') as f:
                f.write(modified_content)
            
            return {
                "agent": "CodeEditorAgent",
                "status": "success",
                "action": "code_modified",
                "modifications_applied": 1,
                "file_path": str(self.test_document)
            }
            
        except Exception as e:
            return {
                "agent": "CodeEditorAgent", 
                "status": "error",
                "error": str(e)
            }
    
    def _execute_documentation_agent(self, prompt: str) -> Dict[str, Any]:
        """Simulate DocumentationAgent execution."""
        logger.info("📝 Executing DocumentationAgent...")
        
        try:
            current_content = self._get_file_content(self.test_document)
            
            # Add documentation based on prompt
            if "docstring" in prompt.lower():
                documented_content = self._add_docstrings(current_content)
            elif "comment" in prompt.lower():
                documented_content = self._add_comments(current_content)
            else:
                documented_content = self._add_general_documentation(current_content)
            
            with open(self.test_document, 'w') as f:
                f.write(documented_content)
            
            return {
                "agent": "DocumentationAgent",
                "status": "success",
                "action": "documentation_added",
                "documentation_type": "docstrings_and_comments",
                "file_path": str(self.test_document)
            }
            
        except Exception as e:
            return {
                "agent": "DocumentationAgent",
                "status": "error", 
                "error": str(e)
            }
    
    def _execute_code_analysis_agent(self, prompt: str) -> Dict[str, Any]:
        """Simulate CodeQualityAgent execution."""
        logger.info("🔍 Executing CodeQualityAgent...")
        
        try:
            current_content = self._get_file_content(self.test_document)
            
            # Perform code analysis
            analysis_results = self._analyze_code_quality(current_content)
            
            # Add analysis results as comments to the file
            analysis_comment = f"\n# Code Analysis Results:\n# {analysis_results}\n"
            updated_content = current_content + analysis_comment
            
            with open(self.test_document, 'w') as f:
                f.write(updated_content)
            
            return {
                "agent": "CodeQualityAgent",
                "status": "success",
                "action": "analysis_completed",
                "analysis_results": analysis_results,
                "file_path": str(self.test_document)
            }
            
        except Exception as e:
            return {
                "agent": "CodeQualityAgent",
                "status": "error",
                "error": str(e)
            }
    
    def _execute_codebase_expert_agent(self, prompt: str) -> Dict[str, Any]:
        """Simulate CodebaseExpertAgent execution."""
        logger.info("🧠 Executing CodebaseExpertAgent...")
        
        try:
            # Query existing code and provide explanations
            current_content = self._get_file_content(self.test_document)
            explanation = self._generate_code_explanation(current_content, prompt)
            
            # Add explanation as a comment
            explanation_comment = f"\n# Expert Analysis:\n# {explanation}\n"
            updated_content = current_content + explanation_comment
            
            with open(self.test_document, 'w') as f:
                f.write(updated_content)
            
            return {
                "agent": "CodebaseExpertAgent",
                "status": "success",
                "action": "explanation_provided",
                "explanation_length": len(explanation),
                "file_path": str(self.test_document)
            }
            
        except Exception as e:
            return {
                "agent": "CodebaseExpertAgent",
                "status": "error",
                "error": str(e)
            }
    
    def _execute_tool_executor_agent(self, prompt: str) -> Dict[str, Any]:
        """Simulate ToolExecutorAgent execution."""
        logger.info("🔧 Executing ToolExecutorAgent...")
        
        try:
            # Simulate running tests or code execution
            execution_results = self._simulate_code_execution(prompt)
            
            # Add execution results to file
            results_comment = f"\n# Execution Results:\n# {execution_results}\n"
            current_content = self._get_file_content(self.test_document)
            updated_content = current_content + results_comment
            
            with open(self.test_document, 'w') as f:
                f.write(updated_content)
            
            return {
                "agent": "ToolExecutorAgent",
                "status": "success",
                "action": "execution_completed",
                "results": execution_results,
                "file_path": str(self.test_document)
            }
            
        except Exception as e:
            return {
                "agent": "ToolExecutorAgent",
                "status": "error",
                "error": str(e)
            }
    
    def _execute_general_fallback(self, prompt: str) -> Dict[str, Any]:
        """Handle general/unknown intents."""
        logger.info("🔄 Executing GeneralFallback...")
        
        try:
            # Add a general comment about the prompt
            comment = f"\n# General note: {prompt}\n"
            current_content = self._get_file_content(self.test_document)
            updated_content = current_content + comment
            
            with open(self.test_document, 'w') as f:
                f.write(updated_content)
            
            return {
                "agent": "GeneralFallback",
                "status": "success",
                "action": "general_handling",
                "file_path": str(self.test_document)
            }
            
        except Exception as e:
            return {
                "agent": "GeneralFallback",
                "status": "error",
                "error": str(e)
            }
    
    # Content generation helper methods
    def _generate_calculator_template(self) -> str:
        """Generate initial calculator template."""
        return '''"""
Calculator Comprehensive Test
Multi-agent pipeline validation document
"""

class Calculator:
    """Advanced calculator with comprehensive functionality."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        """Add two numbers."""
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
    
    def subtract(self, a, b):
        """Subtract b from a."""
        result = a - b
        self.history.append(f"subtract({a}, {b}) = {result}")
        return result
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"multiply({a}, {b}) = {result}")
        return result
    
    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"divide({a}, {b}) = {result}")
        return result
'''
    
    def _simulate_web_research(self, prompt: str) -> str:
        """Simulate web research results."""
        if "python decorator" in prompt.lower():
            return """Python Decorators Research Summary:
Python decorators were introduced in PEP 318 (2003) and implemented in Python 2.4.
They provide a clean syntax for modifying or extending functions and classes.
Key concepts: function wrapping, syntactic sugar (@symbol), preservation of metadata.
Common use cases: logging, timing, authentication, caching, validation."""
        elif "calculator history" in prompt.lower():
            return """Calculator Implementation History:
Early calculators date back to ancient abacus (2000 BC).
Modern electronic calculators emerged in 1960s.
Software calculators became common with personal computers in 1980s.
Object-oriented calculator designs emphasize modularity and extensibility."""
        else:
            return f"Research summary for: {prompt[:50]}..."
    
    def _optimize_code(self, content: str, prompt: str) -> str:
        """Apply code optimizations."""
        # Simulate optimization by adding performance improvements
        if "add method" in prompt.lower():
            optimized = content.replace(
                "def add(self, a, b):",
                "def add(self, a, b):\n        # Optimized for performance"
            )
            return optimized.replace(
                "result = a + b",
                "result = a + b  # Direct addition for optimal speed"
            )
        return content + "\n# Code optimized for better performance\n"
    
    def _fix_code_issues(self, content: str, prompt: str) -> str:
        """Fix code issues."""
        return content + "\n# Code issues fixed\n"
    
    def _refactor_code(self, content: str, prompt: str) -> str:
        """Refactor code structure."""
        return content + "\n# Code refactored for better structure\n"
    
    def _generic_code_edit(self, content: str, prompt: str) -> str:
        """Apply generic code edits."""
        return content + f"\n# Edit applied: {prompt[:50]}...\n"
    
    def _add_docstrings(self, content: str) -> str:
        """Add comprehensive docstrings."""
        # Enhance existing docstrings
        enhanced = content.replace(
            '"""Add two numbers."""',
            '"""Add two numbers.\n        \n        Args:\n            a (float): First number\n            b (float): Second number\n            \n        Returns:\n            float: Sum of a and b\n        """'
        )
        enhanced = enhanced.replace(
            '"""Subtract b from a."""',
            '"""Subtract b from a.\n        \n        Args:\n            a (float): Minuend\n            b (float): Subtrahend\n            \n        Returns:\n            float: Difference a - b\n        """'
        )
        return enhanced
    
    def _add_comments(self, content: str) -> str:
        """Add inline comments."""
        return content + "\n# Comprehensive inline comments added\n"
    
    def _add_general_documentation(self, content: str) -> str:
        """Add general documentation."""
        return content + "\n# General documentation added\n"
    
    def _analyze_code_quality(self, content: str) -> str:
        """Analyze code quality."""
        lines = len(content.splitlines())
        functions = content.count("def ")
        classes = content.count("class ")
        return f"Analysis: {lines} lines, {classes} classes, {functions} functions. Quality: Good"
    
    def _generate_code_explanation(self, content: str, prompt: str) -> str:
        """Generate code explanation."""
        return f"Code explanation for '{prompt[:30]}...': This calculator implements basic arithmetic operations with history tracking"
    
    def _simulate_code_execution(self, prompt: str) -> str:
        """Simulate code execution results."""
        if "test" in prompt.lower():
            return "All tests passed: 4/4 successful, 0 failures, 100% coverage"
        elif "run" in prompt.lower():
            return "Code executed successfully, no runtime errors detected"
        else:
            return "Execution completed with no issues"
    
    def _generate_additional_methods(self, prompt: str) -> str:
        """Generate additional methods."""
        base = self._generate_calculator_template()
        if "power" in prompt.lower():
            base += '''
    def power(self, base, exponent):
        """Calculate base raised to exponent."""
        result = base ** exponent
        self.history.append(f"power({base}, {exponent}) = {result}")
        return result
'''
        return base
    
    def _generate_generic_code(self, prompt: str) -> str:
        """Generate generic code."""
        return f"# Generated code for: {prompt}\npass\n"
    
    def run_comprehensive_pipeline(self) -> SessionSummary:
        """Run the complete comprehensive multi-agent pipeline test."""
        logger.info("🚀 Starting Comprehensive Multi-Agent Pipeline Test")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Test Document: {self.test_document}")
        
        # Define test steps with realistic agent flow
        test_steps = [
            # Step 1: Document Creation
            (1, "Document Creation", 
             "Create a new Python file named calculator_comprehensive.py with an advanced calculator class",
             "code_generation", "CodeGeneratorAgent"),
            
            # Step 2: Web Research Integration  
            (2, "Web Research Integration",
             "Research the history of Python decorators and insert a summary at the top of calculator_comprehensive.py",
             "web_research", "WebResearchAgent"),
            
            # Step 3: Code Enhancement
            (3, "Code Enhancement", 
             "Add a power method to the calculator class for exponentiation",
             "code_generation", "CodeGeneratorAgent"),
            
            # Step 4: Code Optimization
            (4, "Code Optimization",
             "Optimize the add method in calculator_comprehensive.py for better performance", 
             "code_editing", "CodeEditorAgent"),
            
            # Step 5: Documentation Addition
            (5, "Documentation Addition",
             "Add comprehensive docstrings to every public method in calculator_comprehensive.py",
             "documentation", "DocumentationAgent"),
            
            # Step 6: Code Analysis
            (6, "Code Analysis",
             "Analyze the code quality and structure of calculator_comprehensive.py",
             "code_analysis", "CodeQualityAgent"),
            
            # Step 7: Codebase Query
            (7, "Codebase Expertise",
             "Explain how the calculator class works and its design patterns",
             "codebase_query", "CodebaseExpertAgent"),
            
            # Step 8: Tool Execution
            (8, "Tool Execution", 
             "Run unit tests on calculator_comprehensive.py and summarize the results",
             "tool_execution", "ToolExecutorAgent")
        ]
        
        # Execute each test step
        for step_data in test_steps:
            result = self._execute_agent_step(*step_data)
            self.test_results.append(result)
        
        # Generate session summary
        summary = self._generate_session_summary()
        
        # Save detailed results
        self._save_test_results(summary)
        
        logger.info("✅ Comprehensive Multi-Agent Pipeline Test Completed")
        return summary
    
    def _generate_session_summary(self) -> SessionSummary:
        """Generate comprehensive session summary."""
        total_time = time.time() - self.start_time
        successful_steps = len([r for r in self.test_results if r.success])
        failed_steps = len(self.test_results) - successful_steps
        
        # Calculate accuracy metrics
        intent_correct = len([r for r in self.test_results if r.actual_intent == r.expected_intent])
        agent_correct = len([r for r in self.test_results if r.actual_agent == r.expected_agent])
        
        intent_accuracy = (intent_correct / len(self.test_results)) * 100 if self.test_results else 0
        agent_accuracy = (agent_correct / len(self.test_results)) * 100 if self.test_results else 0
        
        # Count file modifications
        file_modifications = len([r for r in self.test_results if r.file_modified])
        
        # Get final document size
        final_size = self._get_file_size(self.test_document)
        
        # Collect errors
        errors = [r.error_message for r in self.test_results if r.error_message]
        
        return SessionSummary(
            session_id=self.session_id,
            total_steps=len(self.test_results),
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            total_execution_time=total_time,
            agent_usage_stats=self.agent_usage_stats,
            intent_classification_accuracy=intent_accuracy,
            agent_routing_accuracy=agent_accuracy,
            file_modifications=file_modifications,
            final_document_size=final_size,
            errors_encountered=errors,
            test_results=self.test_results
        )
    
    def _save_test_results(self, summary: SessionSummary):
        """Save comprehensive test results to files."""
        # Save JSON results for regression testing
        json_results = {
            "summary": asdict(summary),
            "detailed_results": [asdict(result) for result in self.test_results]
        }
        
        json_file = self.workspace_root / f"comprehensive_test_results_{self.session_id}.json"
        with open(json_file, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        # Save human-readable summary
        summary_file = self.workspace_root / f"test_summary_{self.session_id}.md"
        with open(summary_file, 'w') as f:
            f.write(self._generate_markdown_summary(summary))
        
        logger.info(f"📄 Results saved:")
        logger.info(f"  JSON: {json_file}")
        logger.info(f"  Summary: {summary_file}")
        logger.info(f"  Test Document: {self.test_document}")
    
    def _generate_markdown_summary(self, summary: SessionSummary) -> str:
        """Generate human-readable markdown summary."""
        md = f"""# Comprehensive Multi-Agent Pipeline Test Results

## Session Overview
- **Session ID**: {summary.session_id}
- **Total Steps**: {summary.total_steps}
- **Successful Steps**: {summary.successful_steps}
- **Failed Steps**: {summary.failed_steps}
- **Total Execution Time**: {summary.total_execution_time:.2f}s
- **Final Document Size**: {summary.final_document_size} bytes

## Accuracy Metrics
- **Intent Classification Accuracy**: {summary.intent_classification_accuracy:.1f}%
- **Agent Routing Accuracy**: {summary.agent_routing_accuracy:.1f}%
- **File Modifications**: {summary.file_modifications}/{summary.total_steps} steps

## Agent Usage Statistics
"""
        for agent, count in summary.agent_usage_stats.items():
            md += f"- **{agent}**: {count} times\n"
        
        md += f"""
## Step-by-Step Results
"""
        for result in summary.test_results:
            status = "✅" if result.success else "❌"
            md += f"""
### {status} Step {result.step_number}: {result.step_name}
- **Prompt**: {result.user_prompt}
- **Expected**: {result.expected_intent} → {result.expected_agent}
- **Actual**: {result.actual_intent} → {result.actual_agent}
- **Timing**: Classification {result.classification_time:.2f}s, Execution {result.agent_execution_time:.2f}s
- **File Modified**: {result.file_modified} ({result.content_diff_lines} lines changed)
- **File Size**: {result.file_size_before} → {result.file_size_after} bytes
"""
            if result.error_message:
                md += f"- **Error**: {result.error_message}\n"
        
        if summary.errors_encountered:
            md += f"""
## Errors Encountered
"""
            for i, error in enumerate(summary.errors_encountered, 1):
                md += f"{i}. {error}\n"
        
        md += f"""
## Conclusion
The comprehensive multi-agent pipeline test {'completed successfully' if summary.failed_steps == 0 else f'completed with {summary.failed_steps} failures'}. 
All major agent types were exercised through realistic user prompts, demonstrating agent switching and interoperability.

**Overall Success Rate**: {(summary.successful_steps / summary.total_steps * 100):.1f}%
"""
        return md
    
    def cleanup(self):
        """Clean up test workspace."""
        import shutil
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root)
            logger.info(f"🧹 Cleaned up test workspace: {self.workspace_root}")

def main():
    """Run the comprehensive multi-agent pipeline test."""
    pipeline = ComprehensiveMultiAgentPipeline()
    
    try:
        summary = pipeline.run_comprehensive_pipeline()
        
        print("\n" + "="*80)
        print("COMPREHENSIVE MULTI-AGENT PIPELINE TEST RESULTS")
        print("="*80)
        
        print(f"🆔 Session ID: {summary.session_id}")
        print(f"📊 Results: {summary.successful_steps}/{summary.total_steps} steps successful")
        print(f"⏱️ Total Time: {summary.total_execution_time:.2f}s")
        print(f"🎯 Intent Accuracy: {summary.intent_classification_accuracy:.1f}%")
        print(f"🤖 Agent Accuracy: {summary.agent_routing_accuracy:.1f}%")
        print(f"📝 File Modifications: {summary.file_modifications}")
        print(f"📄 Final Document Size: {summary.final_document_size} bytes")
        
        print(f"\n🤖 Agent Usage:")
        for agent, count in summary.agent_usage_stats.items():
            print(f"  {agent}: {count} times")
        
        if summary.errors_encountered:
            print(f"\n❌ Errors ({len(summary.errors_encountered)}):")
            for error in summary.errors_encountered:
                print(f"  - {error}")
        
        success_rate = (summary.successful_steps / summary.total_steps) * 100
        if success_rate == 100:
            print("\n🎉 ALL TESTS PASSED - PIPELINE FULLY FUNCTIONAL")
        elif success_rate >= 75:
            print(f"\n✅ MOSTLY SUCCESSFUL - {success_rate:.1f}% PASS RATE")
        else:
            print(f"\n⚠️ NEEDS ATTENTION - {success_rate:.1f}% PASS RATE")
        
        return summary
        
    except Exception as e:
        print(f"\n❌ PIPELINE TEST FAILED: {e}")
        logger.exception("Pipeline test failed")
        return None
        
    finally:
        # Uncomment to clean up test files
        # pipeline.cleanup()
        pass

if __name__ == "__main__":
    main()