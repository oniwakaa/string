#!/usr/bin/env python3
"""
Direct Test of Prompt Refinements

Tests improved prompt candidates by directly updating the classifier
and running focused tests on known failure cases.
"""

import json
import time
import logging
from typing import Dict, List, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DirectPromptTester:
    """Direct testing of improved prompts using existing classifier."""
    
    def __init__(self):
        self.known_failures = [
            {
                "prompt": "Research the history of Python decorators and insert a summary at the top of calculator_comprehensive.py",
                "expected_intent": "web_research",
                "current_result": "code_editing"
            },
            {
                "prompt": "Explain how the calculator class works and its design patterns", 
                "expected_intent": "codebase_query",
                "current_result": "code_analysis"
            },
            {
                "prompt": "Run unit tests on calculator_comprehensive.py and summarize the results",
                "expected_intent": "tool_execution",
                "current_result": "code_analysis"
            }
        ]
        
        # Additional edge cases for comprehensive testing
        self.edge_cases = [
            {"prompt": "Get Python documentation from the official website", "expected_intent": "web_research"},
            {"prompt": "Fetch API information from external sources", "expected_intent": "web_research"},
            {"prompt": "Execute all unit tests and report results", "expected_intent": "tool_execution"},
            {"prompt": "Run the code formatter on these files", "expected_intent": "tool_execution"},
            {"prompt": "How does the authentication system work?", "expected_intent": "codebase_query"},
            {"prompt": "Find the database connection configuration", "expected_intent": "codebase_query"},
            {"prompt": "Analyze code quality and suggest improvements", "expected_intent": "code_analysis"},
            {"prompt": "Review this code for security issues", "expected_intent": "code_analysis"}
        ]
        
        self.all_test_cases = self.known_failures + self.edge_cases
    
    def create_improved_prompt_template(self, strategy: str) -> str:
        """Create improved prompt template based on strategy."""
        
        if strategy == "enhanced_definitions":
            return """Classify user request into ONE intent:

web_research: Get external info (NOT code modification)
codebase_query: Understand code (NOT quality evaluation)  
code_generation: Create new code (NOT modify existing)
code_editing: Modify existing code (NOT create new)
code_analysis: Evaluate quality (NOT understand logic)
documentation: Add docs/comments (NOT code changes)
tool_execution: Run/execute/test (NOT inspect/analyze)

Request: {prompt}

Intent:"""
        
        elif strategy == "keyword_focused":
            return """Intent classification for: {prompt}

Categories with key indicators:
• web_research: research, history, fetch, external, web
• codebase_query: explain, how works, find, understand  
• code_generation: create, new, add, build, implement
• code_editing: optimize, fix, modify, update, refactor
• code_analysis: analyze, quality, structure, review
• documentation: docstring, comment, document, explain usage
• tool_execution: run, execute, test, command

Choose the best match:"""
        
        elif strategy == "action_focused":
            return """What does the user want to DO?

{prompt}

Pick ONE action type:
web_research = get info from external sources
codebase_query = understand existing code logic
code_generation = write new code from scratch
code_editing = change/improve existing code
code_analysis = check code quality/structure  
documentation = add explanations/comments
tool_execution = run/test/execute code

Answer:"""
        
        else:  # current minimal 
            return """Intent classification for: {prompt}

Categories: web_research, codebase_query, code_generation, code_editing, code_analysis, documentation, tool_execution

Choose the best match:"""
    
    def test_prompt_strategy(self, strategy_name: str, template: str) -> Dict[str, Any]:
        """Test a specific prompt strategy."""
        logger.info(f"\n🧪 Testing Strategy: {strategy_name}")
        
        # Temporarily patch the classifier to use new prompt
        try:
            from src.inference.intent_classifier import GemmaIntentClassifier
            
            # Create classifier instance
            classifier = GemmaIntentClassifier()
            
            # Store original template
            original_template = classifier._classification_prompt_template
            original_options = getattr(classifier, '_intent_options', '')
            
            # Update with new template
            classifier._classification_prompt_template = template
            classifier._intent_options = "web_research, codebase_query, code_generation, code_editing, code_analysis, documentation, tool_execution"
            
            results = []
            total_correct = 0
            total_time = 0
            
            for i, test_case in enumerate(self.all_test_cases):
                test_prompt = test_case["prompt"]
                expected = test_case["expected_intent"]
                
                logger.info(f"  Case {i+1}: {test_prompt[:50]}...")
                
                try:
                    start_time = time.time()
                    classification = classifier.classify(test_prompt)
                    classification_time = time.time() - start_time
                    
                    actual = classification.primary_intent
                    confidence = classification.confidence
                    is_correct = actual == expected
                    
                    if is_correct:
                        total_correct += 1
                    
                    total_time += classification_time
                    
                    results.append({
                        "prompt": test_prompt,
                        "expected": expected,
                        "actual": actual,
                        "confidence": confidence,
                        "correct": is_correct,
                        "time": classification_time
                    })
                    
                    status = "✅" if is_correct else "❌"
                    logger.info(f"    {status} Expected: {expected}, Got: {actual} (conf: {confidence:.2f})")
                    
                except Exception as e:
                    logger.error(f"    ❌ Error: {e}")
                    results.append({
                        "prompt": test_prompt,
                        "expected": expected,
                        "actual": "error",
                        "confidence": 0.0,
                        "correct": False,
                        "time": 0.0,
                        "error": str(e)
                    })
            
            # Restore original template
            classifier._classification_prompt_template = original_template
            classifier._intent_options = original_options
            
            accuracy = (total_correct / len(self.all_test_cases)) * 100
            avg_time = total_time / len(self.all_test_cases)
            
            logger.info(f"📊 Results: {total_correct}/{len(self.all_test_cases)} correct ({accuracy:.1f}% accuracy)")
            logger.info(f"⏱️ Average time: {avg_time:.2f}s")
            
            return {
                "strategy_name": strategy_name,
                "template": template,
                "total_cases": len(self.all_test_cases),
                "correct_cases": total_correct,
                "accuracy": accuracy,
                "average_time": avg_time,
                "detailed_results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Strategy {strategy_name} failed: {e}")
            return {
                "strategy_name": strategy_name,
                "template": template,
                "error": str(e),
                "accuracy": 0.0
            }
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test of all prompt strategies."""
        logger.info("🚀 Starting Comprehensive Prompt Strategy Testing")
        
        strategies = [
            ("current_minimal", "current_minimal"),
            ("enhanced_definitions", "enhanced_definitions"),
            ("keyword_focused", "keyword_focused"), 
            ("action_focused", "action_focused")
        ]
        
        results = {}
        
        for strategy_name, strategy_type in strategies:
            template = self.create_improved_prompt_template(strategy_type)
            result = self.test_prompt_strategy(strategy_name, template)
            results[strategy_name] = result
        
        # Find best performing strategy
        best_strategy = max(results.values(), key=lambda x: x.get("accuracy", 0))
        
        summary = {
            "test_overview": {
                "total_test_cases": len(self.all_test_cases),
                "known_failure_cases": len(self.known_failures),
                "edge_cases": len(self.edge_cases),
                "strategies_tested": len(strategies)
            },
            "strategy_results": results,
            "best_strategy": {
                "name": best_strategy["strategy_name"],
                "accuracy": best_strategy.get("accuracy", 0),
                "improvement": best_strategy.get("accuracy", 0) - results.get("current_minimal", {}).get("accuracy", 0)
            },
            "failure_analysis": self._analyze_remaining_failures(results)
        }
        
        return summary
    
    def _analyze_remaining_failures(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which cases are still failing across strategies."""
        failure_patterns = {}
        
        for strategy_name, result in results.items():
            if "detailed_results" not in result:
                continue
                
            for case in result["detailed_results"]:
                if not case.get("correct", False):
                    key = f"{case['expected']} → {case['actual']}"
                    if key not in failure_patterns:
                        failure_patterns[key] = {"count": 0, "examples": []}
                    failure_patterns[key]["count"] += 1
                    if len(failure_patterns[key]["examples"]) < 2:
                        failure_patterns[key]["examples"].append(case["prompt"][:50])
        
        return {
            "common_failure_patterns": failure_patterns,
            "most_problematic": max(failure_patterns.items(), key=lambda x: x[1]["count"]) if failure_patterns else None
        }
    
    def generate_report(self, summary: Dict[str, Any]) -> str:
        """Generate comprehensive test report."""
        report = "# Intent Classifier Prompt Refinement Test Results\n\n"
        
        # Overview
        overview = summary["test_overview"]
        report += f"## Test Overview\n"
        report += f"- **Total Test Cases**: {overview['total_test_cases']}\n"
        report += f"- **Known Failure Cases**: {overview['known_failure_cases']}\n"
        report += f"- **Edge Cases**: {overview['edge_cases']}\n"
        report += f"- **Strategies Tested**: {overview['strategies_tested']}\n\n"
        
        # Results Summary
        best = summary["best_strategy"]
        report += f"## Results Summary\n"
        report += f"🏆 **Best Strategy**: {best['name']} ({best['accuracy']:.1f}% accuracy)\n"
        report += f"📈 **Improvement**: +{best['improvement']:.1f}% over current minimal prompt\n\n"
        
        # Strategy Comparison
        report += f"## Strategy Comparison\n\n"
        strategies = summary["strategy_results"]
        
        for strategy_name, result in strategies.items():
            if "error" in result:
                report += f"### ❌ {strategy_name.replace('_', ' ').title()}\n"
                report += f"**Error**: {result['error']}\n\n"
            else:
                accuracy = result["accuracy"]
                symbol = "🏆" if strategy_name == best["name"] else "✅" if accuracy >= 70 else "⚠️"
                report += f"### {symbol} {strategy_name.replace('_', ' ').title()}\n"
                report += f"- **Accuracy**: {accuracy:.1f}% ({result['correct_cases']}/{result['total_cases']})\n"
                report += f"- **Average Time**: {result['average_time']:.2f}s\n"
                
                # Show specific improvements on known failures
                if "detailed_results" in result:
                    known_failure_fixes = 0
                    for case in result["detailed_results"][:len(self.known_failures)]:
                        if case.get("correct", False):
                            known_failure_fixes += 1
                    report += f"- **Known Failures Fixed**: {known_failure_fixes}/{len(self.known_failures)}\n"
                
                report += "\n"
        
        # Failure Analysis
        failure_analysis = summary["failure_analysis"]
        if failure_analysis["common_failure_patterns"]:
            report += f"## Remaining Classification Issues\n\n"
            for pattern, info in sorted(failure_analysis["common_failure_patterns"].items(), key=lambda x: x[1]["count"], reverse=True):
                report += f"- **{pattern}**: {info['count']} occurrences\n"
                for example in info["examples"]:
                    report += f"  - \"{example}...\"\n"
            report += "\n"
        
        # Recommendations
        report += f"## Recommendations\n\n"
        if best["improvement"] > 15:
            report += f"✅ **Immediate Implementation**: {best['name']} shows significant improvement (+{best['improvement']:.1f}%)\n"
        elif best["improvement"] > 5:
            report += f"✅ **Consider Implementation**: {best['name']} shows meaningful improvement (+{best['improvement']:.1f}%)\n"
        else:
            report += f"⚠️ **Further Refinement Needed**: Best improvement is only +{best['improvement']:.1f}%\n"
        
        if failure_analysis["most_problematic"]:
            pattern, info = failure_analysis["most_problematic"]
            report += f"\n🔍 **Focus Area**: {pattern} pattern appears in {info['count']} cases - needs targeted prompt refinement\n"
        
        return report
    
    def save_results(self, summary: Dict[str, Any]):
        """Save test results to files."""
        # Save JSON results
        with open("prompt_refinement_test_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        # Save markdown report
        report = self.generate_report(summary)
        with open("prompt_refinement_test_report.md", "w") as f:
            f.write(report)
        
        logger.info("📄 Results saved:")
        logger.info("  • prompt_refinement_test_results.json")
        logger.info("  • prompt_refinement_test_report.md")

def main():
    """Run direct prompt refinement testing."""
    tester = DirectPromptTester()
    
    try:
        # Run comprehensive test
        summary = tester.run_comprehensive_test()
        
        # Save results
        tester.save_results(summary)
        
        # Print summary
        print("\n" + "="*70)
        print("PROMPT REFINEMENT TEST RESULTS")
        print("="*70)
        
        best = summary["best_strategy"] 
        print(f"🏆 Best Strategy: {best['name']}")
        print(f"📊 Accuracy: {best['accuracy']:.1f}%")
        print(f"📈 Improvement: +{best['improvement']:.1f}%")
        
        print(f"\n📋 Strategy Performance:")
        for name, result in summary["strategy_results"].items():
            if "error" not in result:
                accuracy = result["accuracy"]
                symbol = "🏆" if name == best["name"] else "✅" if accuracy >= 70 else "⚠️"
                print(f"  {symbol} {name.replace('_', ' ').title()}: {accuracy:.1f}%")
        
        # Show if original failures were fixed
        current_result = summary["strategy_results"].get("current_minimal", {})
        best_result = summary["strategy_results"].get(best["name"], {})
        
        if "detailed_results" in current_result and "detailed_results" in best_result:
            current_failures = sum(1 for r in current_result["detailed_results"][:3] if not r.get("correct", False))
            best_failures = sum(1 for r in best_result["detailed_results"][:3] if not r.get("correct", False))
            fixed = current_failures - best_failures
            
            print(f"\n🔧 Known Failure Cases Fixed: {fixed}/3")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Testing failed: {e}")
        raise

if __name__ == "__main__":
    main()