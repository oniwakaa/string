#!/usr/bin/env python3
"""
Intent Classification Failure Analysis

Analyzes misclassified prompts from the comprehensive multi-agent pipeline test
to identify patterns and develop improved classification strategies.
"""

import json
import logging
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MisclassificationCase:
    """Represents a single misclassification case."""
    prompt: str
    expected_intent: str
    actual_intent: str
    expected_agent: str
    actual_agent: str
    confidence: float
    raw_response: str
    classification_time: float
    
    def get_failure_type(self) -> str:
        """Categorize the type of classification failure."""
        if self.expected_intent == "web_research" and self.actual_intent == "code_editing":
            return "web_research_confusion"
        elif self.expected_intent == "codebase_query" and self.actual_intent == "code_analysis":
            return "query_vs_analysis_confusion"
        elif self.expected_intent == "tool_execution" and self.actual_intent == "code_analysis":
            return "execution_vs_analysis_confusion"
        else:
            return "other_confusion"

class ClassificationFailureAnalyzer:
    """Analyzes classification failures and generates improvement recommendations."""
    
    def __init__(self):
        self.failure_cases: List[MisclassificationCase] = []
        self.success_cases: List[MisclassificationCase] = []
        
    def load_test_results(self, results_file: str):
        """Load test results from comprehensive pipeline test."""
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
            
            detailed_results = data.get("detailed_results", [])
            
            for result in detailed_results:
                case = MisclassificationCase(
                    prompt=result["user_prompt"],
                    expected_intent=result["expected_intent"],
                    actual_intent=result["actual_intent"],
                    expected_agent=result["expected_agent"],
                    actual_agent=result["actual_agent"],
                    confidence=result.get("metadata", {}).get("classification_confidence", 0.0),
                    raw_response=result.get("metadata", {}).get("agent_result", {}).get("raw_response", ""),
                    classification_time=result["classification_time"]
                )
                
                if result["expected_intent"] == result["actual_intent"]:
                    self.success_cases.append(case)
                else:
                    self.failure_cases.append(case)
                    
            logger.info(f"Loaded {len(self.success_cases)} successful and {len(self.failure_cases)} failed classifications")
            
        except Exception as e:
            logger.error(f"Failed to load test results: {e}")
            raise
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in classification failures."""
        analysis = {
            "total_failures": len(self.failure_cases),
            "total_successes": len(self.success_cases),
            "failure_rate": len(self.failure_cases) / (len(self.failure_cases) + len(self.success_cases)) * 100,
            "failure_types": {},
            "prompt_analysis": {},
            "confidence_analysis": {},
            "timing_analysis": {}
        }
        
        # Categorize failure types
        for case in self.failure_cases:
            failure_type = case.get_failure_type()
            if failure_type not in analysis["failure_types"]:
                analysis["failure_types"][failure_type] = []
            analysis["failure_types"][failure_type].append(case)
        
        # Analyze prompt characteristics
        for case in self.failure_cases:
            prompt_lower = case.prompt.lower()
            
            # Extract key characteristics
            characteristics = {
                "contains_research": any(word in prompt_lower for word in ["research", "history", "information", "summary"]),
                "contains_run": any(word in prompt_lower for word in ["run", "execute", "test", "tests"]),
                "contains_explain": any(word in prompt_lower for word in ["explain", "how", "works", "describe"]),
                "contains_analyze": any(word in prompt_lower for word in ["analyze", "analysis", "quality", "structure"]),
                "contains_web_terms": any(word in prompt_lower for word in ["website", "web", "url", "scrape", "fetch"]),
                "contains_file_ref": any(word in prompt_lower for word in [".py", "file", "calculator"]),
                "word_count": len(case.prompt.split()),
                "has_specific_action": any(word in prompt_lower for word in ["insert", "add", "create", "optimize"])
            }
            
            analysis["prompt_analysis"][case.prompt] = {
                "expected": case.expected_intent,
                "actual": case.actual_intent,
                "characteristics": characteristics
            }
        
        # Confidence analysis
        failure_confidences = [case.confidence for case in self.failure_cases]
        success_confidences = [case.confidence for case in self.success_cases]
        
        analysis["confidence_analysis"] = {
            "failure_avg_confidence": sum(failure_confidences) / len(failure_confidences) if failure_confidences else 0,
            "success_avg_confidence": sum(success_confidences) / len(success_confidences) if success_confidences else 0,
            "failure_confidence_range": (min(failure_confidences), max(failure_confidences)) if failure_confidences else (0, 0),
            "success_confidence_range": (min(success_confidences), max(success_confidences)) if success_confidences else (0, 0)
        }
        
        # Timing analysis
        failure_times = [case.classification_time for case in self.failure_cases]
        success_times = [case.classification_time for case in self.success_cases]
        
        analysis["timing_analysis"] = {
            "failure_avg_time": sum(failure_times) / len(failure_times) if failure_times else 0,
            "success_avg_time": sum(success_times) / len(success_times) if success_times else 0
        }
        
        return analysis
    
    def generate_detailed_failure_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a detailed report of classification failures."""
        report = "# Intent Classification Failure Analysis Report\n\n"
        
        # Overview
        report += f"## Overview\n"
        report += f"- **Total Classifications**: {analysis['total_failures'] + analysis['total_successes']}\n"
        report += f"- **Failures**: {analysis['total_failures']}\n"
        report += f"- **Successes**: {analysis['total_successes']}\n"
        report += f"- **Failure Rate**: {analysis['failure_rate']:.1f}%\n\n"
        
        # Failure Type Analysis
        report += f"## Failure Type Breakdown\n\n"
        for failure_type, cases in analysis["failure_types"].items():
            report += f"### {failure_type.replace('_', ' ').title()} ({len(cases)} cases)\n\n"
            
            for case in cases:
                report += f"**Prompt**: {case.prompt}\n"
                report += f"- Expected: `{case.expected_intent}` → `{case.expected_agent}`\n"
                report += f"- Actual: `{case.actual_intent}` → `{case.actual_agent}`\n"
                report += f"- Confidence: {case.confidence:.2f}\n"
                report += f"- Time: {case.classification_time:.2f}s\n\n"
        
        # Confidence Analysis
        report += f"## Confidence Analysis\n"
        report += f"- **Failed Classifications Average Confidence**: {analysis['confidence_analysis']['failure_avg_confidence']:.2f}\n"
        report += f"- **Successful Classifications Average Confidence**: {analysis['confidence_analysis']['success_avg_confidence']:.2f}\n"
        report += f"- **Failed Confidence Range**: {analysis['confidence_analysis']['failure_confidence_range'][0]:.2f} - {analysis['confidence_analysis']['failure_confidence_range'][1]:.2f}\n"
        report += f"- **Success Confidence Range**: {analysis['confidence_analysis']['success_confidence_range'][0]:.2f} - {analysis['confidence_analysis']['success_confidence_range'][1]:.2f}\n\n"
        
        # Timing Analysis
        report += f"## Timing Analysis\n"
        report += f"- **Failed Classifications Average Time**: {analysis['timing_analysis']['failure_avg_time']:.2f}s\n"
        report += f"- **Successful Classifications Average Time**: {analysis['timing_analysis']['success_avg_time']:.2f}s\n\n"
        
        return report
    
    def identify_prompt_improvement_strategies(self, analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """Identify strategies to improve prompt classification."""
        strategies = {
            "web_research_improvements": [],
            "tool_execution_improvements": [],  
            "codebase_query_improvements": [],
            "general_improvements": []
        }
        
        # Analyze web research failures
        web_research_failures = analysis["failure_types"].get("web_research_confusion", [])
        if web_research_failures:
            strategies["web_research_improvements"].extend([
                "Add explicit 'research', 'history', 'information retrieval' keywords",
                "Distinguish between 'insert summary' (web research) vs 'modify code' (editing)",
                "Include examples of external data retrieval vs code modification",
                "Emphasize web/external source indicators"
            ])
        
        # Analyze tool execution failures  
        execution_failures = analysis["failure_types"].get("execution_vs_analysis_confusion", [])
        if execution_failures:
            strategies["tool_execution_improvements"].extend([
                "Clarify 'run', 'execute', 'test' as action keywords vs 'analyze' as inspection",
                "Distinguish between performing actions vs examining code",
                "Add examples showing execution commands vs analysis requests",
                "Emphasize result generation vs quality assessment"
            ])
        
        # Analyze codebase query failures
        query_failures = analysis["failure_types"].get("query_vs_analysis_confusion", [])
        if query_failures:
            strategies["codebase_query_improvements"].extend([
                "Distinguish 'explain how X works' (query) vs 'analyze quality' (analysis)", 
                "Clarify understanding requests vs quality assessment",
                "Add examples of knowledge queries vs code evaluation",
                "Emphasize comprehension vs critique"
            ])
        
        # General improvements
        strategies["general_improvements"].extend([
            "Provide mutually exclusive intent definitions",
            "Include negative examples (what each intent is NOT)",
            "Add keyword indicators for each intent type",
            "Maintain minimal prompt length while adding specificity"
        ])
        
        return strategies
    
    def generate_improved_classifier_prompts(self, strategies: Dict[str, List[str]]) -> List[str]:
        """Generate improved classifier prompt candidates based on analysis."""
        
        # Current intents from registry
        intents_with_examples = {
            "web_research": "fetch external information (e.g., 'research Python history', 'get documentation from web')",
            "codebase_query": "understand existing code (e.g., 'explain how this works', 'find the login function')", 
            "code_generation": "create new code (e.g., 'add power method', 'create calculator class')",
            "code_editing": "modify existing code (e.g., 'optimize performance', 'fix bug', 'refactor method')",
            "code_analysis": "evaluate code quality (e.g., 'analyze structure', 'check for issues')",
            "documentation": "add docs/comments (e.g., 'add docstrings', 'document API')",
            "tool_execution": "run commands/tests (e.g., 'run unit tests', 'execute code')"
        }
        
        # Candidate 1: Enhanced definitions with negative examples
        candidate_1 = f"""Classify user request into ONE intent:

web_research: Get external info (NOT code modification)
codebase_query: Understand code (NOT quality evaluation)  
code_generation: Create new code (NOT modify existing)
code_editing: Modify existing code (NOT create new)
code_analysis: Evaluate quality (NOT understand logic)
documentation: Add docs/comments (NOT code changes)
tool_execution: Run/execute/test (NOT inspect/analyze)

Request: {{prompt}}

Intent:"""
        
        # Candidate 2: Keyword-focused with clear distinctions
        candidate_2 = f"""Intent classification for: {{prompt}}

Categories with key indicators:
• web_research: research, history, fetch, external, web
• codebase_query: explain, how works, find, understand  
• code_generation: create, new, add, build, implement
• code_editing: optimize, fix, modify, update, refactor
• code_analysis: analyze, quality, structure, review
• documentation: docstring, comment, document, explain usage
• tool_execution: run, execute, test, command

Choose the best match:"""

        # Candidate 3: Action-focused distinctions
        candidate_3 = f"""What does the user want to DO?

{{prompt}}

Pick ONE action type:
web_research = get info from external sources
codebase_query = understand existing code logic
code_generation = write new code from scratch
code_editing = change/improve existing code
code_analysis = check code quality/structure  
documentation = add explanations/comments
tool_execution = run/test/execute code

Answer:"""

        return [candidate_1, candidate_2, candidate_3]

def main():
    """Run classification failure analysis."""
    analyzer = ClassificationFailureAnalyzer()
    
    # Load test results
    results_file = "test_workspace_comprehensive/comprehensive_test_results_multi_agent_1753511119.json"
    
    if not Path(results_file).exists():
        logger.error(f"Test results file not found: {results_file}")
        return
    
    analyzer.load_test_results(results_file)
    
    # Analyze failure patterns
    analysis = analyzer.analyze_failure_patterns()
    
    # Generate detailed report
    report = analyzer.generate_detailed_failure_report(analysis)
    
    # Save analysis report
    with open("classification_failure_analysis.md", "w") as f:
        f.write(report)
    
    # Identify improvement strategies
    strategies = analyzer.identify_prompt_improvement_strategies(analysis)
    
    # Generate improved prompt candidates
    improved_prompts = analyzer.generate_improved_classifier_prompts(strategies)
    
    # Save improvement recommendations
    with open("classifier_improvement_recommendations.json", "w") as f:
        json.dump({
            "analysis_summary": {
                "total_failures": analysis["total_failures"],
                "failure_rate": analysis["failure_rate"],
                "main_failure_types": list(analysis["failure_types"].keys())
            },
            "improvement_strategies": strategies,
            "improved_prompt_candidates": improved_prompts
        }, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("CLASSIFICATION FAILURE ANALYSIS SUMMARY")
    print("="*60)
    print(f"📊 Total Classifications: {analysis['total_failures'] + analysis['total_successes']}")
    print(f"❌ Failures: {analysis['total_failures']} ({analysis['failure_rate']:.1f}%)")
    print(f"✅ Successes: {analysis['total_successes']}")
    
    print(f"\n🔍 Main Failure Types:")
    for failure_type, cases in analysis["failure_types"].items():
        print(f"  • {failure_type.replace('_', ' ').title()}: {len(cases)} cases")
    
    print(f"\n📈 Confidence Analysis:")
    print(f"  • Failed Classifications: {analysis['confidence_analysis']['failure_avg_confidence']:.2f} avg confidence")
    print(f"  • Successful Classifications: {analysis['confidence_analysis']['success_avg_confidence']:.2f} avg confidence")
    
    print(f"\n💡 Key Improvement Areas:")
    print(f"  • Web research vs code editing distinction")
    print(f"  • Tool execution vs code analysis distinction")
    print(f"  • Codebase queries vs quality analysis distinction")
    
    print(f"\n📄 Generated Files:")
    print(f"  • classification_failure_analysis.md")
    print(f"  • classifier_improvement_recommendations.json")
    
    return analysis, strategies, improved_prompts

if __name__ == "__main__":
    main()