#!/usr/bin/env python3
"""
Create Comprehensive Classifier Regression Suite

Creates a comprehensive test suite for intent classification that covers
edge cases, ambiguous prompts, and all intent categories with confidence tracking.
"""

import json
import time
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RegressionTestCase:
    """Single regression test case for intent classification."""
    id: str
    prompt: str
    expected_intent: str
    category: str  # 'known_failure', 'edge_case', 'ambiguous', 'standard'
    difficulty: str  # 'easy', 'medium', 'hard'
    description: str
    keywords: List[str]
    expected_confidence_min: float = 0.7

class ClassifierRegressionSuite:
    """Comprehensive regression test suite for intent classifier."""
    
    def __init__(self):
        self.test_cases: List[RegressionTestCase] = []
        self._build_comprehensive_test_suite()
    
    def _build_comprehensive_test_suite(self):
        """Build comprehensive test suite covering all scenarios."""
        
        # Known failure cases (previously misclassified)
        known_failures = [
            RegressionTestCase(
                id="kf_001",
                prompt="Research the history of Python decorators and insert a summary at the top of calculator.py",
                expected_intent="web_research",
                category="known_failure",
                difficulty="hard",
                description="Web research with code modification context - should prioritize external data retrieval",
                keywords=["research", "history", "insert", "summary"],
                expected_confidence_min=0.8
            ),
            RegressionTestCase(
                id="kf_002", 
                prompt="Explain how the calculator class works and its design patterns",
                expected_intent="codebase_query",
                category="known_failure",
                difficulty="hard",
                description="Understanding request vs analysis - should prioritize comprehension over critique",
                keywords=["explain", "how", "works", "design patterns"],
                expected_confidence_min=0.8
            ),
            RegressionTestCase(
                id="kf_003",
                prompt="Run unit tests on calculator.py and summarize the results",
                expected_intent="tool_execution",
                category="known_failure", 
                difficulty="hard",
                description="Execution request with analysis context - should prioritize action over inspection",
                keywords=["run", "unit tests", "summarize", "results"],
                expected_confidence_min=0.8
            )
        ]
        
        # Web research edge cases
        web_research_cases = [
            RegressionTestCase(
                id="wr_001",
                prompt="Get the latest Python documentation from the official website",
                expected_intent="web_research",
                category="edge_case",
                difficulty="medium",
                description="Clear external data retrieval",
                keywords=["get", "documentation", "website"]
            ),
            RegressionTestCase(
                id="wr_002",
                prompt="Fetch API information from external sources and libraries",
                expected_intent="web_research",
                category="edge_case", 
                difficulty="medium",
                description="External source emphasis",
                keywords=["fetch", "external sources"]
            ),
            RegressionTestCase(
                id="wr_003",
                prompt="Look up best practices for error handling online",
                expected_intent="web_research",
                category="edge_case",
                difficulty="easy",
                description="Online lookup indicator",
                keywords=["look up", "online"]
            ),
            RegressionTestCase(
                id="wr_004",
                prompt="scrape data from https://example.com/api",
                expected_intent="web_research", 
                category="standard",
                difficulty="easy",
                description="Direct web scraping with URL",
                keywords=["scrape", "https://"]
            )
        ]
        
        # Tool execution edge cases
        tool_execution_cases = [
            RegressionTestCase(
                id="te_001",
                prompt="Execute all unit tests and report any failures",
                expected_intent="tool_execution",
                category="edge_case",
                difficulty="medium",
                description="Execution with reporting context",
                keywords=["execute", "unit tests", "report"]
            ),
            RegressionTestCase(
                id="te_002",
                prompt="Run the linter on this code and fix any issues found",
                expected_intent="tool_execution",
                category="edge_case",
                difficulty="medium", 
                description="Tool execution with follow-up actions",
                keywords=["run", "linter", "fix"]
            ),
            RegressionTestCase(
                id="te_003",
                prompt="Test this function with various input values",
                expected_intent="tool_execution",
                category="edge_case",
                difficulty="medium",
                description="Function testing request",
                keywords=["test", "function", "input"]
            ),
            RegressionTestCase(
                id="te_004",
                prompt="run python main.py and show the output",
                expected_intent="tool_execution",
                category="standard",
                difficulty="easy",
                description="Direct command execution",
                keywords=["run", "python", "output"]
            )
        ]
        
        # Codebase query edge cases  
        codebase_query_cases = [
            RegressionTestCase(
                id="cq_001",
                prompt="How does the authentication system work in this application?",
                expected_intent="codebase_query",
                category="edge_case",
                difficulty="medium",
                description="System understanding request",
                keywords=["how does", "work", "system"]
            ),
            RegressionTestCase(
                id="cq_002",
                prompt="Find where the database connection is established",
                expected_intent="codebase_query",
                category="edge_case",
                difficulty="medium",
                description="Code location request",
                keywords=["find", "where", "database"]
            ),
            RegressionTestCase(
                id="cq_003",
                prompt="What design patterns are used in the payment processing?",
                expected_intent="codebase_query",
                category="edge_case",
                difficulty="medium",
                description="Pattern identification request",
                keywords=["what", "design patterns", "used"]
            ),
            RegressionTestCase(
                id="cq_004",
                prompt="show me the implementation of the login function",
                expected_intent="codebase_query",
                category="standard",
                difficulty="easy",
                description="Direct implementation request",
                keywords=["show", "implementation", "function"]
            )
        ]
        
        # Code analysis edge cases
        code_analysis_cases = [
            RegressionTestCase(
                id="ca_001",
                prompt="Analyze this code for potential security vulnerabilities",
                expected_intent="code_analysis",
                category="edge_case",
                difficulty="medium",
                description="Security analysis request",
                keywords=["analyze", "security", "vulnerabilities"]
            ),
            RegressionTestCase(
                id="ca_002",
                prompt="Review the code quality and suggest improvements",
                expected_intent="code_analysis",
                category="edge_case",
                difficulty="medium",
                description="Quality review request",
                keywords=["review", "quality", "improvements"]
            ),
            RegressionTestCase(
                id="ca_003",
                prompt="Check this implementation for performance bottlenecks",
                expected_intent="code_analysis",
                category="edge_case",
                difficulty="medium",
                description="Performance analysis request",
                keywords=["check", "performance", "bottlenecks"]
            ),
            RegressionTestCase(
                id="ca_004",
                prompt="analyze the code structure and architecture",
                expected_intent="code_analysis",
                category="standard",
                difficulty="easy",
                description="Structural analysis request",
                keywords=["analyze", "structure", "architecture"]
            )
        ]
        
        # Code generation cases
        code_generation_cases = [
            RegressionTestCase(
                id="cg_001",
                prompt="Create a new REST API endpoint for user management",
                expected_intent="code_generation",
                category="standard",
                difficulty="easy",
                description="New code creation request",
                keywords=["create", "new", "API endpoint"]
            ),
            RegressionTestCase(
                id="cg_002",
                prompt="Generate a Python function to validate email addresses",
                expected_intent="code_generation",
                category="standard",
                difficulty="easy",
                description="Function generation request",
                keywords=["generate", "function", "validate"]
            ),
            RegressionTestCase(
                id="cg_003",
                prompt="Build a React component for data visualization",
                expected_intent="code_generation",
                category="standard",
                difficulty="easy",
                description="Component creation request",
                keywords=["build", "component", "React"]
            )
        ]
        
        # Code editing cases
        code_editing_cases = [
            RegressionTestCase(
                id="ce_001",
                prompt="Optimize the database query for better performance",
                expected_intent="code_editing",
                category="standard",
                difficulty="easy",
                description="Performance optimization request",
                keywords=["optimize", "database", "performance"]
            ),
            RegressionTestCase(
                id="ce_002",
                prompt="Fix the bug in the authentication middleware",
                expected_intent="code_editing",
                category="standard",
                difficulty="easy",
                description="Bug fix request",
                keywords=["fix", "bug", "authentication"]
            ),
            RegressionTestCase(
                id="ce_003",
                prompt="Refactor this method to improve readability",
                expected_intent="code_editing",
                category="standard",
                difficulty="easy",
                description="Refactoring request",
                keywords=["refactor", "method", "readability"]
            )
        ]
        
        # Documentation cases
        documentation_cases = [
            RegressionTestCase(
                id="doc_001",
                prompt="Add comprehensive docstrings to all public methods",
                expected_intent="documentation",
                category="standard",
                difficulty="easy",
                description="Docstring addition request",
                keywords=["add", "docstrings", "methods"]
            ),
            RegressionTestCase(
                id="doc_002",
                prompt="Document the API endpoints with usage examples",
                expected_intent="documentation",
                category="standard",
                difficulty="easy",
                description="API documentation request",
                keywords=["document", "API", "examples"]
            ),
            RegressionTestCase(
                id="doc_003",
                prompt="Create inline comments explaining the algorithm",
                expected_intent="documentation",
                category="standard",
                difficulty="easy",
                description="Comment creation request",
                keywords=["create", "comments", "explaining"]
            )
        ]
        
        # Ambiguous cases that test edge boundaries
        ambiguous_cases = [
            RegressionTestCase(
                id="amb_001",
                prompt="Analyze this code and explain how it works",
                expected_intent="code_analysis",  # Analysis takes precedence
                category="ambiguous",
                difficulty="hard",
                description="Analysis vs explanation ambiguity - analysis should win",
                keywords=["analyze", "explain", "how works"],
                expected_confidence_min=0.6
            ),
            RegressionTestCase(
                id="amb_002",
                prompt="Create comprehensive tests for the calculator functions",
                expected_intent="code_generation",  # Creating new code, not running tests
                category="ambiguous",
                difficulty="hard",
                description="Test creation vs execution ambiguity - creation should win",
                keywords=["create", "tests", "functions"],
                expected_confidence_min=0.6
            ),
            RegressionTestCase(
                id="amb_003",
                prompt="Document the API endpoints and test them thoroughly",
                expected_intent="documentation",  # Documentation is primary action
                category="ambiguous",
                difficulty="hard",
                description="Documentation vs testing ambiguity - documentation should win",
                keywords=["document", "API", "test"],
                expected_confidence_min=0.6
            ),
            RegressionTestCase(
                id="amb_004",
                prompt="Find and fix performance issues in the code",
                expected_intent="code_editing",  # Fix takes precedence over find
                category="ambiguous",
                difficulty="hard",
                description="Query vs editing ambiguity - editing should win",
                keywords=["find", "fix", "performance"],
                expected_confidence_min=0.6
            )
        ]
        
        # Combine all test cases
        self.test_cases = (
            known_failures + 
            web_research_cases + 
            tool_execution_cases + 
            codebase_query_cases + 
            code_analysis_cases + 
            code_generation_cases + 
            code_editing_cases + 
            documentation_cases + 
            ambiguous_cases
        )
        
        logger.info(f"Built comprehensive test suite with {len(self.test_cases)} test cases")
        logger.info(f"Categories: {self._get_category_counts()}")
    
    def _get_category_counts(self) -> Dict[str, int]:
        """Get count of test cases by category."""
        counts = {}
        for case in self.test_cases:
            counts[case.category] = counts.get(case.category, 0) + 1
        return counts
    
    def run_regression_test(self) -> Dict[str, Any]:
        """Run the complete regression test suite."""
        logger.info("🧪 Running Comprehensive Classifier Regression Test")
        
        try:
            from src.inference.intent_classifier import GemmaIntentClassifier
            classifier = GemmaIntentClassifier()
            
            total_cases = len(self.test_cases)
            passed_cases = 0
            failed_cases = []
            results_by_category = {}
            results_by_difficulty = {}
            confidence_scores = []
            total_time = 0
            
            for i, test_case in enumerate(self.test_cases):
                logger.info(f"Testing {i+1}/{total_cases}: {test_case.id} - {test_case.prompt[:50]}...")
                
                try:
                    start_time = time.time()
                    classification = classifier.classify(test_case.prompt)
                    classification_time = time.time() - start_time
                    total_time += classification_time
                    
                    actual_intent = classification.primary_intent
                    confidence = classification.confidence
                    confidence_scores.append(confidence)
                    
                    is_correct = actual_intent == test_case.expected_intent
                    meets_confidence = confidence >= test_case.expected_confidence_min
                    
                    if is_correct and meets_confidence:
                        passed_cases += 1
                        status = "✅"
                    else:
                        failed_cases.append({
                            "test_case": test_case,
                            "actual_intent": actual_intent,
                            "confidence": confidence,
                            "intent_correct": is_correct,
                            "confidence_sufficient": meets_confidence
                        })
                        status = "❌"
                    
                    # Track by category
                    if test_case.category not in results_by_category:
                        results_by_category[test_case.category] = {"total": 0, "passed": 0}
                    results_by_category[test_case.category]["total"] += 1
                    if is_correct and meets_confidence:
                        results_by_category[test_case.category]["passed"] += 1
                    
                    # Track by difficulty
                    if test_case.difficulty not in results_by_difficulty:
                        results_by_difficulty[test_case.difficulty] = {"total": 0, "passed": 0}
                    results_by_difficulty[test_case.difficulty]["total"] += 1
                    if is_correct and meets_confidence:
                        results_by_difficulty[test_case.difficulty]["passed"] += 1
                    
                    logger.info(f"  {status} Expected: {test_case.expected_intent}, Got: {actual_intent} (conf: {confidence:.2f})")
                    
                except Exception as e:
                    logger.error(f"  ❌ Error: {e}")
                    failed_cases.append({
                        "test_case": test_case,
                        "error": str(e),
                        "actual_intent": "error",
                        "confidence": 0.0,
                        "intent_correct": False,
                        "confidence_sufficient": False
                    })
            
            # Calculate metrics
            accuracy = (passed_cases / total_cases) * 100
            average_time = total_time / total_cases
            average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            results = {
                "test_summary": {
                    "total_cases": total_cases,
                    "passed_cases": passed_cases,
                    "failed_cases": len(failed_cases),
                    "accuracy": accuracy,
                    "average_time": average_time,
                    "average_confidence": average_confidence
                },
                "results_by_category": {
                    cat: {
                        "accuracy": (data["passed"] / data["total"]) * 100,
                        "passed": data["passed"],
                        "total": data["total"]
                    }
                    for cat, data in results_by_category.items()
                },
                "results_by_difficulty": {
                    diff: {
                        "accuracy": (data["passed"] / data["total"]) * 100,
                        "passed": data["passed"],
                        "total": data["total"]
                    }
                    for diff, data in results_by_difficulty.items()
                },
                "failed_cases": failed_cases,
                "confidence_analysis": {
                    "average": average_confidence,
                    "min": min(confidence_scores) if confidence_scores else 0,
                    "max": max(confidence_scores) if confidence_scores else 0,
                    "below_threshold": len([c for c in confidence_scores if c < 0.7])
                }
            }
            
            logger.info(f"📊 Regression Test Complete: {passed_cases}/{total_cases} passed ({accuracy:.1f}%)")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Regression test failed: {e}")
            raise
    
    def save_test_suite(self):
        """Save the test suite to a JSON file for future use."""
        test_suite_data = {
            "version": "1.0",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Comprehensive intent classifier regression test suite",
            "total_cases": len(self.test_cases),
            "categories": self._get_category_counts(),
            "test_cases": [asdict(case) for case in self.test_cases]
        }
        
        with open("classifier_regression_test_suite.json", "w") as f:
            json.dump(test_suite_data, f, indent=2)
        
        logger.info(f"💾 Test suite saved to classifier_regression_test_suite.json")
    
    def generate_regression_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive regression test report."""
        report = "# Intent Classifier Regression Test Report\n\n"
        
        # Overview
        summary = results["test_summary"]
        report += f"## Test Overview\n"
        report += f"- **Total Test Cases**: {summary['total_cases']}\n"
        report += f"- **Passed**: {summary['passed_cases']}\n"
        report += f"- **Failed**: {summary['failed_cases']}\n"
        report += f"- **Overall Accuracy**: {summary['accuracy']:.1f}%\n"
        report += f"- **Average Classification Time**: {summary['average_time']:.2f}s\n"
        report += f"- **Average Confidence**: {summary['average_confidence']:.2f}\n\n"
        
        # Performance by Category
        report += f"## Performance by Category\n\n"
        for category, data in results["results_by_category"].items():
            symbol = "✅" if data["accuracy"] >= 80 else "⚠️" if data["accuracy"] >= 60 else "❌"
            report += f"- {symbol} **{category.replace('_', ' ').title()}**: {data['accuracy']:.1f}% ({data['passed']}/{data['total']})\n"
        
        # Performance by Difficulty
        report += f"\n## Performance by Difficulty\n\n"
        for difficulty, data in results["results_by_difficulty"].items():
            symbol = "✅" if data["accuracy"] >= 80 else "⚠️" if data["accuracy"] >= 60 else "❌"
            report += f"- {symbol} **{difficulty.title()}**: {data['accuracy']:.1f}% ({data['passed']}/{data['total']})\n"
        
        # Failed Cases Analysis
        if results["failed_cases"]:
            report += f"\n## Failed Cases Analysis ({len(results['failed_cases'])} cases)\n\n"
            
            # Group failures by type
            failure_types = {}
            for failure in results["failed_cases"]:
                if "error" in failure:
                    failure_type = "error"
                elif not failure["intent_correct"]:
                    expected = failure["test_case"].expected_intent
                    actual = failure["actual_intent"]
                    failure_type = f"{expected} → {actual}"
                else:
                    failure_type = "low_confidence"
                
                if failure_type not in failure_types:
                    failure_types[failure_type] = []
                failure_types[failure_type].append(failure)
            
            for failure_type, failures in failure_types.items():
                report += f"### {failure_type} ({len(failures)} cases)\n\n"
                for failure in failures[:3]:  # Show first 3 examples
                    case = failure["test_case"]
                    report += f"- **{case.id}**: \"{case.prompt[:60]}...\"\n"
                    if "error" not in failure:
                        report += f"  - Expected: {case.expected_intent}, Got: {failure['actual_intent']}\n"
                        report += f"  - Confidence: {failure['confidence']:.2f} (min: {case.expected_confidence_min:.2f})\n"
                report += "\n"
        
        # Confidence Analysis
        conf_analysis = results["confidence_analysis"]
        report += f"## Confidence Analysis\n"
        report += f"- **Average Confidence**: {conf_analysis['average']:.2f}\n"
        report += f"- **Confidence Range**: {conf_analysis['min']:.2f} - {conf_analysis['max']:.2f}\n"
        report += f"- **Below Threshold (0.7)**: {conf_analysis['below_threshold']} cases\n\n"
        
        # Recommendations
        report += f"## Recommendations\n\n"
        if summary["accuracy"] >= 85:
            report += "✅ **Excellent Performance**: Classifier is performing well across all categories\n"
        elif summary["accuracy"] >= 70:
            report += "✅ **Good Performance**: Minor improvements needed for edge cases\n"
        else:
            report += "⚠️ **Needs Improvement**: Significant classification issues remain\n"
        
        # Category-specific recommendations
        for category, data in results["results_by_category"].items():
            if data["accuracy"] < 70:
                report += f"- 🔧 **{category.replace('_', ' ').title()}**: Needs attention ({data['accuracy']:.1f}% accuracy)\n"
        
        return report

def main():
    """Run the classifier regression test suite."""
    suite = ClassifierRegressionSuite()
    
    try:
        # Save test suite
        suite.save_test_suite()
        
        # Run regression test
        results = suite.run_regression_test()
        
        # Generate report
        report = suite.generate_regression_report(results)
        
        # Save results
        with open("classifier_regression_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        with open("classifier_regression_report.md", "w") as f:
            f.write(report)
        
        # Print summary
        print("\n" + "="*70)
        print("CLASSIFIER REGRESSION TEST RESULTS")
        print("="*70)
        
        summary = results["test_summary"]
        print(f"📊 Overall: {summary['passed_cases']}/{summary['total_cases']} passed ({summary['accuracy']:.1f}%)")
        print(f"⏱️ Avg Time: {summary['average_time']:.2f}s")
        print(f"🎯 Avg Confidence: {summary['average_confidence']:.2f}")
        
        print(f"\n📈 By Category:")
        for category, data in results["results_by_category"].items():
            symbol = "✅" if data["accuracy"] >= 80 else "⚠️" if data["accuracy"] >= 60 else "❌"
            print(f"  {symbol} {category.replace('_', ' ').title()}: {data['accuracy']:.1f}%")
        
        print(f"\n📄 Generated Files:")
        print(f"  • classifier_regression_test_suite.json")
        print(f"  • classifier_regression_results.json")
        print(f"  • classifier_regression_report.md")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Regression testing failed: {e}")
        raise

if __name__ == "__main__":
    main()