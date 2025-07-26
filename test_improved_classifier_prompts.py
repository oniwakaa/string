#!/usr/bin/env python3
"""
Test Improved Classifier Prompts

Tests the improved prompt candidates against known failure cases to validate
classification accuracy improvements without model overload.
"""

import json
import time
import logging
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass 
class PromptTestResult:
    """Result of testing a single prompt candidate."""
    candidate_name: str
    prompt_template: str
    test_cases_passed: int
    test_cases_total: int
    accuracy: float
    average_time: float
    confidence_scores: List[float]
    detailed_results: List[Dict[str, Any]]

class ImprovedClassifierTester:
    """Tests improved classifier prompt candidates."""
    
    def __init__(self):
        self.model = None
        self._load_model()
        
        # Known failure cases from analysis
        self.failure_test_cases = [
            {
                "prompt": "Research the history of Python decorators and insert a summary at the top of calculator_comprehensive.py",
                "expected_intent": "web_research",
                "issue": "Contains 'insert' which confuses with code editing"
            },
            {
                "prompt": "Explain how the calculator class works and its design patterns", 
                "expected_intent": "codebase_query",
                "issue": "Contains 'explain' which confuses with analysis"
            },
            {
                "prompt": "Run unit tests on calculator_comprehensive.py and summarize the results",
                "expected_intent": "tool_execution", 
                "issue": "Contains 'summarize' which confuses with analysis"
            }
        ]
        
        # Additional edge cases to test
        self.edge_test_cases = [
            # Web research variations
            {
                "prompt": "Get information about Python async/await from documentation websites",
                "expected_intent": "web_research"
            },
            {
                "prompt": "Fetch the latest API documentation for this library from the web",
                "expected_intent": "web_research"
            },
            {
                "prompt": "Look up best practices for error handling online",
                "expected_intent": "web_research"
            },
            
            # Tool execution variations
            {
                "prompt": "Execute the test suite and report any failures",
                "expected_intent": "tool_execution"
            },
            {
                "prompt": "Run the linter on this code and fix any issues found",
                "expected_intent": "tool_execution"
            },
            {
                "prompt": "Test this function with various inputs",
                "expected_intent": "tool_execution"
            },
            
            # Codebase query variations
            {
                "prompt": "How does the authentication system work in this application?",
                "expected_intent": "codebase_query"
            },
            {
                "prompt": "Find where the database connection is established",
                "expected_intent": "codebase_query"
            },
            {
                "prompt": "What design patterns are used in the payment processing?",
                "expected_intent": "codebase_query"
            },
            
            # Ambiguous cases that should be handled correctly
            {
                "prompt": "Analyze this code and explain how it works",
                "expected_intent": "code_analysis",  # Analysis takes precedence over explanation
            },
            {
                "prompt": "Create comprehensive tests for the calculator functions",
                "expected_intent": "code_generation"  # Creating new code, not running existing tests
            },
            {
                "prompt": "Document the API endpoints and test them thoroughly",
                "expected_intent": "documentation"  # Documentation is primary action
            }
        ]
        
        # Combine all test cases
        self.all_test_cases = self.failure_test_cases + self.edge_test_cases
    
    def _load_model(self):
        """Load the Gemma3n model for testing."""
        try:
            from src.inference.intent_classifier import GemmaIntentClassifier
            # Create a temporary classifier just to load the model
            temp_classifier = GemmaIntentClassifier()
            self.model = temp_classifier.model
            logger.info("✅ Model loaded successfully for prompt testing")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    def _extract_intent_from_response(self, response_text: str, intent_list: List[str]) -> Tuple[str, float]:
        """Extract intent and confidence from model response."""
        response_lower = response_text.lower().strip()
        
        # Direct intent matching
        for intent in intent_list:
            if intent.lower() in response_lower:
                return intent, 0.9  # High confidence for direct match
        
        # Partial matching with underscores
        for intent in intent_list:
            intent_words = intent.replace("_", " ").lower()
            if intent_words in response_lower:
                return intent, 0.8  # Medium confidence for partial match
        
        # Look for key terms to infer intent
        if any(term in response_lower for term in ["research", "web", "fetch", "external", "history"]):
            return "web_research", 0.7
        elif any(term in response_lower for term in ["run", "execute", "test"]):
            return "tool_execution", 0.7
        elif any(term in response_lower for term in ["explain", "understand", "how", "find"]):
            return "codebase_query", 0.7
        elif any(term in response_lower for term in ["analyze", "analysis", "quality", "structure"]):
            return "code_analysis", 0.7
        elif any(term in response_lower for term in ["create", "generate", "new", "add"]):
            return "code_generation", 0.7
        elif any(term in response_lower for term in ["edit", "modify", "optimize", "fix"]):
            return "code_editing", 0.7
        elif any(term in response_lower for term in ["document", "docstring", "comment"]):
            return "documentation", 0.7
        
        return "general_query", 0.3  # Low confidence fallback
    
    def test_prompt_candidate(self, candidate_name: str, prompt_template: str) -> PromptTestResult:
        """Test a single prompt candidate against all test cases."""
        logger.info(f"\n🧪 Testing prompt candidate: {candidate_name}")
        
        intent_list = ["web_research", "codebase_query", "code_generation", "code_editing", 
                      "code_analysis", "documentation", "tool_execution"]
        
        detailed_results = []
        total_time = 0
        confidence_scores = []
        passed_cases = 0
        
        for i, test_case in enumerate(self.all_test_cases):
            test_prompt = test_case["prompt"]
            expected_intent = test_case["expected_intent"]
            
            logger.info(f"  Testing case {i+1}/{len(self.all_test_cases)}: {test_prompt[:50]}...")
            
            try:
                # Format the prompt
                if "{prompt}" in prompt_template:
                    formatted_prompt = prompt_template.format(prompt=test_prompt)
                else:
                    # Handle templates without placeholder
                    formatted_prompt = prompt_template + f"\n\nUser request: {test_prompt}\n\nIntent:"
                
                # Generate response
                start_time = time.time()
                response = self.model(
                    formatted_prompt,
                    max_tokens=20,
                    temperature=0.1,
                    top_p=0.9,
                    stop=["User:", "Intent:", "Categories:", "\n\n", "Request:"]
                )
                classification_time = time.time() - start_time
                total_time += classification_time
                
                # Extract intent and confidence
                response_text = response['choices'][0]['text'].strip()
                predicted_intent, confidence = self._extract_intent_from_response(response_text, intent_list)
                confidence_scores.append(confidence)
                
                # Check if prediction is correct
                is_correct = predicted_intent == expected_intent
                if is_correct:
                    passed_cases += 1
                
                # Store detailed result
                detailed_results.append({
                    "test_prompt": test_prompt,
                    "expected_intent": expected_intent,
                    "predicted_intent": predicted_intent,
                    "confidence": confidence,
                    "is_correct": is_correct,
                    "classification_time": classification_time,
                    "raw_response": response_text,
                    "issue_description": test_case.get("issue", "")
                })
                
                status = "✅" if is_correct else "❌"
                logger.info(f"    {status} Expected: {expected_intent}, Got: {predicted_intent} (conf: {confidence:.2f})")
                
            except Exception as e:
                logger.error(f"    ❌ Error testing case: {e}")
                detailed_results.append({
                    "test_prompt": test_prompt,
                    "expected_intent": expected_intent,
                    "predicted_intent": "error",
                    "confidence": 0.0,
                    "is_correct": False,
                    "classification_time": 0.0,
                    "raw_response": str(e),
                    "issue_description": test_case.get("issue", "")
                })
        
        # Calculate metrics
        accuracy = (passed_cases / len(self.all_test_cases)) * 100
        average_time = total_time / len(self.all_test_cases)
        
        result = PromptTestResult(
            candidate_name=candidate_name,
            prompt_template=prompt_template,
            test_cases_passed=passed_cases,
            test_cases_total=len(self.all_test_cases),
            accuracy=accuracy,
            average_time=average_time,
            confidence_scores=confidence_scores,
            detailed_results=detailed_results
        )
        
        logger.info(f"📊 Results: {passed_cases}/{len(self.all_test_cases)} passed ({accuracy:.1f}% accuracy)")
        logger.info(f"⏱️ Average time: {average_time:.2f}s")
        
        return result
    
    def test_all_candidates(self) -> List[PromptTestResult]:
        """Test all improved prompt candidates."""
        logger.info("🌟 Testing All Improved Prompt Candidates")
        
        # Load the improved candidates
        with open("classifier_improvement_recommendations.json", "r") as f:
            recommendations = json.load(f)
        
        candidates = [
            ("Enhanced Definitions", recommendations["improved_prompt_candidates"][0]),
            ("Keyword Focused", recommendations["improved_prompt_candidates"][1]), 
            ("Action Focused", recommendations["improved_prompt_candidates"][2])
        ]
        
        results = []
        for name, template in candidates:
            result = self.test_prompt_candidate(name, template)
            results.append(result)
        
        return results
    
    def compare_with_current_prompt(self, results: List[PromptTestResult]) -> Dict[str, Any]:
        """Compare improved prompts with current minimal prompt."""
        logger.info("🔄 Testing Current Minimal Prompt for Comparison")
        
        # Current minimal prompt
        current_prompt = """Intent classification for: {prompt}

Categories: {intent_list}

Choose the best match:"""
        
        intent_list_str = "web_research, codebase_query, code_generation, code_editing, code_analysis, documentation, tool_execution"
        current_formatted = current_prompt.replace("{intent_list}", intent_list_str)
        
        current_result = self.test_prompt_candidate("Current Minimal", current_formatted)
        
        # Compare results
        comparison = {
            "current_prompt": {
                "accuracy": current_result.accuracy,
                "average_time": current_result.average_time,
                "average_confidence": sum(current_result.confidence_scores) / len(current_result.confidence_scores)
            },
            "improved_prompts": []
        }
        
        for result in results:
            avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
            comparison["improved_prompts"].append({
                "name": result.candidate_name,
                "accuracy": result.accuracy,
                "average_time": result.average_time,
                "average_confidence": avg_confidence,
                "accuracy_improvement": result.accuracy - current_result.accuracy,
                "time_change": result.average_time - current_result.average_time
            })
        
        return comparison
    
    def generate_test_report(self, results: List[PromptTestResult], comparison: Dict[str, Any]) -> str:
        """Generate comprehensive test report."""
        report = "# Improved Classifier Prompt Test Results\n\n"
        
        # Overview
        report += "## Test Overview\n"
        report += f"- **Total Test Cases**: {len(self.all_test_cases)}\n"
        report += f"- **Known Failure Cases**: {len(self.failure_test_cases)}\n"
        report += f"- **Edge Cases**: {len(self.edge_test_cases)}\n"
        report += f"- **Prompt Candidates Tested**: {len(results)}\n\n"
        
        # Current vs Improved Comparison
        report += "## Performance Comparison\n\n"
        current = comparison["current_prompt"]
        report += f"### Current Minimal Prompt\n"
        report += f"- **Accuracy**: {current['accuracy']:.1f}%\n"
        report += f"- **Average Time**: {current['average_time']:.2f}s\n"
        report += f"- **Average Confidence**: {current['average_confidence']:.2f}\n\n"
        
        # Best performing candidate
        best_candidate = max(comparison["improved_prompts"], key=lambda x: x["accuracy"])
        report += f"### Best Performing Candidate: {best_candidate['name']}\n"
        report += f"- **Accuracy**: {best_candidate['accuracy']:.1f}% (+{best_candidate['accuracy_improvement']:.1f}%)\n"
        report += f"- **Average Time**: {best_candidate['average_time']:.2f}s ({best_candidate['time_change']:+.2f}s)\n"
        report += f"- **Average Confidence**: {best_candidate['average_confidence']:.2f}\n\n"
        
        # Detailed Results for Each Candidate
        report += "## Detailed Results by Candidate\n\n"
        for result in results:
            report += f"### {result.candidate_name}\n"
            report += f"- **Overall Accuracy**: {result.accuracy:.1f}% ({result.test_cases_passed}/{result.test_cases_total})\n"
            report += f"- **Average Time**: {result.average_time:.2f}s\n"
            
            # Breakdown by failure cases
            failure_case_results = result.detailed_results[:len(self.failure_test_cases)]
            failure_correct = sum(1 for r in failure_case_results if r["is_correct"])
            report += f"- **Known Failure Cases Fixed**: {failure_correct}/{len(self.failure_test_cases)}\n"
            
            # Show specific failures
            failed_cases = [r for r in result.detailed_results if not r["is_correct"]]
            if failed_cases:
                report += f"- **Still Failing**: {len(failed_cases)} cases\n"
                for case in failed_cases[:3]:  # Show first 3 failures
                    report += f"  - \"{case['test_prompt'][:50]}...\" → Expected: {case['expected_intent']}, Got: {case['predicted_intent']}\n"
            
            report += "\n"
        
        # Recommendations
        report += "## Recommendations\n\n"
        if best_candidate['accuracy_improvement'] > 10:
            report += f"✅ **Implement {best_candidate['name']}**: Shows significant improvement (+{best_candidate['accuracy_improvement']:.1f}% accuracy)\n\n"
        elif best_candidate['accuracy_improvement'] > 0:
            report += f"✅ **Consider {best_candidate['name']}**: Shows modest improvement (+{best_candidate['accuracy_improvement']:.1f}% accuracy)\n\n"
        else:
            report += "⚠️ **No Clear Winner**: All candidates show similar or worse performance than current prompt\n\n"
        
        # Analysis of remaining issues
        all_failed_cases = []
        for result in results:
            all_failed_cases.extend([r for r in result.detailed_results if not r["is_correct"]])
        
        if all_failed_cases:
            report += "### Remaining Classification Issues\n"
            common_failures = {}
            for case in all_failed_cases:
                key = f"{case['expected_intent']} → {case['predicted_intent']}"
                common_failures[key] = common_failures.get(key, 0) + 1
            
            for failure_type, count in sorted(common_failures.items(), key=lambda x: x[1], reverse=True):
                report += f"- **{failure_type}**: {count} occurrences\n"
        
        return report
    
    def save_results(self, results: List[PromptTestResult], comparison: Dict[str, Any]):
        """Save test results to files."""
        # Save detailed results
        results_data = {
            "test_summary": {
                "total_test_cases": len(self.all_test_cases),
                "known_failure_cases": len(self.failure_test_cases),
                "edge_cases": len(self.edge_test_cases),
                "candidates_tested": len(results)
            },
            "comparison": comparison,
            "detailed_results": [
                {
                    "candidate_name": r.candidate_name,
                    "accuracy": r.accuracy,
                    "average_time": r.average_time,
                    "test_cases_passed": r.test_cases_passed,
                    "test_cases_total": r.test_cases_total,
                    "confidence_scores": r.confidence_scores,
                    "detailed_results": r.detailed_results
                }
                for r in results
            ]
        }
        
        with open("improved_classifier_test_results.json", "w") as f:
            json.dump(results_data, f, indent=2)
        
        # Save human-readable report
        report = self.generate_test_report(results, comparison)
        with open("improved_classifier_test_report.md", "w") as f:
            f.write(report)
        
        logger.info("📄 Results saved:")
        logger.info("  • improved_classifier_test_results.json")
        logger.info("  • improved_classifier_test_report.md")

def main():
    """Run improved classifier prompt testing."""
    tester = ImprovedClassifierTester()
    
    try:
        # Test all improved candidates
        results = tester.test_all_candidates()
        
        # Compare with current prompt
        comparison = tester.compare_with_current_prompt(results)
        
        # Save results
        tester.save_results(results, comparison)
        
        # Print summary
        print("\n" + "="*70)
        print("IMPROVED CLASSIFIER PROMPT TEST SUMMARY")
        print("="*70)
        
        current_acc = comparison["current_prompt"]["accuracy"]
        print(f"📊 Current Prompt Accuracy: {current_acc:.1f}%")
        
        print(f"\n🧪 Candidate Results:")
        for candidate in comparison["improved_prompts"]:
            improvement = candidate["accuracy_improvement"]
            symbol = "🔥" if improvement > 10 else "✅" if improvement > 0 else "❌"
            print(f"  {symbol} {candidate['name']}: {candidate['accuracy']:.1f}% ({improvement:+.1f}%)")
        
        # Find best candidate
        best = max(comparison["improved_prompts"], key=lambda x: x["accuracy"])
        print(f"\n🏆 Best Candidate: {best['name']}")
        print(f"  📈 Accuracy: {best['accuracy']:.1f}% (+{best['accuracy_improvement']:.1f}%)")
        print(f"  ⏱️ Time: {best['average_time']:.2f}s")
        
        return results, comparison
        
    except Exception as e:
        logger.error(f"❌ Testing failed: {e}")
        raise

if __name__ == "__main__":
    main()