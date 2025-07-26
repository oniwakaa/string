#!/usr/bin/env python3
"""
Test Improved Routing System

Tests the updated intent classifier and fallback logic on the 5 previously 
failed test cases to validate improvements.
"""

import json
import time
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedRoutingTester:
    """Tests the improved routing system on previously failed cases."""
    
    def __init__(self):
        # The 5 cases that previously failed
        self.test_cases = [
            {
                "test_id": "wr_001",
                "prompt": "Get the latest Python documentation from the official website",
                "expected_intent": "web_research",
                "previous_result": "documentation",
                "category": "edge_case"
            },
            {
                "test_id": "wr_002", 
                "prompt": "Fetch API information from external sources and libraries",
                "expected_intent": "web_research",
                "previous_result": "documentation",
                "category": "edge_case"
            },
            {
                "test_id": "te_001",
                "prompt": "Execute all unit tests and report any failures",
                "expected_intent": "tool_execution",
                "previous_result": "code_analysis",
                "category": "edge_case"
            },
            {
                "test_id": "te_003",
                "prompt": "Test this function with various input values",
                "expected_intent": "tool_execution",
                "previous_result": "code_analysis",
                "category": "edge_case"
            },
            {
                "test_id": "amb_004",
                "prompt": "Find and fix performance issues in the code",
                "expected_intent": "code_editing",
                "previous_result": "code_analysis",
                "category": "ambiguous"
            }
        ]
    
    def test_improved_routing(self) -> Dict[str, Any]:
        """Test the improved routing system."""
        logger.info("🧪 Testing improved routing system on previously failed cases...")
        
        try:
            from src.inference.intent_classifier import GemmaIntentClassifier
            classifier = GemmaIntentClassifier()
            
            results = []
            fixed_cases = 0
            total_time = 0
            
            for i, test_case in enumerate(self.test_cases):
                logger.info(f"Testing {i+1}/{len(self.test_cases)}: {test_case['test_id']}")
                logger.info(f"  Prompt: {test_case['prompt']}")
                logger.info(f"  Expected: {test_case['expected_intent']}, Previously got: {test_case['previous_result']}")
                
                try:
                    start_time = time.time()
                    classification = classifier.classify(test_case['prompt'])
                    classification_time = time.time() - start_time
                    total_time += classification_time
                    
                    actual_intent = classification.primary_intent
                    confidence = classification.confidence
                    is_fixed = actual_intent == test_case['expected_intent']
                    
                    if is_fixed:
                        fixed_cases += 1
                        status = "✅ FIXED"
                    else:
                        status = "❌ Still failing"
                    
                    logger.info(f"  Result: {actual_intent} (confidence: {confidence:.2f}) - {status}")
                    
                    # Check for metadata indicating corrections were made
                    metadata = classification.metadata or {}
                    if metadata.get('correction_applied'):
                        logger.info(f"  🔧 Correction applied: {metadata.get('original_intent')} → {actual_intent}")
                    
                    results.append({
                        "test_id": test_case['test_id'],
                        "prompt": test_case['prompt'],
                        "expected_intent": test_case['expected_intent'],
                        "previous_result": test_case['previous_result'],
                        "new_result": actual_intent,
                        "confidence": confidence,
                        "is_fixed": is_fixed,
                        "classification_time": classification_time,
                        "metadata": metadata,
                        "category": test_case['category']
                    })
                    
                except Exception as e:
                    logger.error(f"  ❌ Error: {e}")
                    results.append({
                        "test_id": test_case['test_id'],
                        "prompt": test_case['prompt'],
                        "expected_intent": test_case['expected_intent'],
                        "previous_result": test_case['previous_result'],
                        "new_result": "error",
                        "confidence": 0.0,
                        "is_fixed": False,
                        "classification_time": 0.0,
                        "error": str(e),
                        "category": test_case['category']
                    })
            
            # Calculate improvement metrics
            improvement_rate = (fixed_cases / len(self.test_cases)) * 100
            avg_time = total_time / len(self.test_cases)
            avg_confidence = sum(r['confidence'] for r in results if r['confidence'] > 0) / len([r for r in results if r['confidence'] > 0])
            
            return {
                "test_summary": {
                    "total_cases": len(self.test_cases),
                    "fixed_cases": fixed_cases,
                    "still_failing": len(self.test_cases) - fixed_cases,
                    "improvement_rate": improvement_rate,
                    "average_time": avg_time,
                    "average_confidence": avg_confidence
                },
                "detailed_results": results,
                "analysis": self._analyze_results(results)
            }
            
        except Exception as e:
            logger.error(f"❌ Testing failed: {e}")
            raise
    
    def _analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the test results for patterns."""
        
        # Group by outcome
        fixed_by_pattern = {}
        still_failing_by_pattern = {}
        
        for result in results:
            expected = result['expected_intent']
            previous = result['previous_result']
            new_result = result['new_result']
            pattern = f"{expected} (was {previous})"
            
            if result['is_fixed']:
                if pattern not in fixed_by_pattern:
                    fixed_by_pattern[pattern] = []
                fixed_by_pattern[pattern].append(result['test_id'])
            else:
                if pattern not in still_failing_by_pattern:
                    still_failing_by_pattern[pattern] = []
                still_failing_by_pattern[pattern].append({
                    'test_id': result['test_id'],
                    'new_result': new_result
                })
        
        # Analyze corrections applied
        corrections_applied = [r for r in results if r.get('metadata', {}).get('correction_applied')]
        
        return {
            "fixed_patterns": fixed_by_pattern,
            "still_failing_patterns": still_failing_by_pattern,
            "corrections_applied": len(corrections_applied),
            "correction_details": [
                {
                    'test_id': r['test_id'],
                    'original': r['metadata']['original_intent'],
                    'corrected': r['new_result']
                } for r in corrections_applied
            ]
        }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate test report."""
        report = "# Improved Routing System Test Results\n\n"
        
        summary = results['test_summary']
        analysis = results['analysis']
        
        # Overview
        report += "## Test Overview\n"
        report += f"- **Previously Failed Cases**: {summary['total_cases']}\n"
        report += f"- **Cases Fixed**: {summary['fixed_cases']}\n"
        report += f"- **Still Failing**: {summary['still_failing']}\n"
        report += f"- **Improvement Rate**: {summary['improvement_rate']:.1f}%\n"
        report += f"- **Average Time**: {summary['average_time']:.2f}s\n"
        report += f"- **Average Confidence**: {summary['average_confidence']:.2f}\n\n"
        
        # Detailed Results
        report += "## Detailed Results\n\n"
        for result in results['detailed_results']:
            status_symbol = "✅" if result['is_fixed'] else "❌"
            report += f"### {status_symbol} {result['test_id']} - {result['category'].title()}\n"
            report += f"**Prompt**: \"{result['prompt']}\"\n"
            report += f"**Expected**: {result['expected_intent']}\n"
            report += f"**Previous**: {result['previous_result']} → **New**: {result['new_result']}\n"
            report += f"**Confidence**: {result['confidence']:.2f}\n"
            
            if result.get('metadata', {}).get('correction_applied'):
                report += f"**🔧 Correction Applied**: {result['metadata']['original_intent']} → {result['new_result']}\n"
            
            if 'error' in result:
                report += f"**Error**: {result['error']}\n"
            
            report += "\n"
        
        # Analysis
        if analysis['fixed_patterns']:
            report += "## Successfully Fixed Patterns\n\n"
            for pattern, test_ids in analysis['fixed_patterns'].items():
                report += f"- **{pattern}**: {', '.join(test_ids)}\n"
            report += "\n"
        
        if analysis['still_failing_patterns']:
            report += "## Still Failing Patterns\n\n"
            for pattern, failures in analysis['still_failing_patterns'].items():
                report += f"- **{pattern}**:\n"
                for failure in failures:
                    report += f"  - {failure['test_id']}: now gets {failure['new_result']}\n"
            report += "\n"
        
        if analysis['corrections_applied'] > 0:
            report += "## Validation Corrections Applied\n\n"
            report += f"Total corrections: {analysis['corrections_applied']}\n\n"
            for correction in analysis['correction_details']:
                report += f"- **{correction['test_id']}**: {correction['original']} → {correction['corrected']}\n"
            report += "\n"
        
        # Summary
        if summary['improvement_rate'] >= 80:
            report += "## ✅ Excellent Improvement\n"
            report += "The routing improvements have successfully fixed most of the previously failing cases.\n"
        elif summary['improvement_rate'] >= 60:
            report += "## ✅ Good Improvement\n"
            report += "Significant routing improvements achieved, with further tuning recommended.\n"
        else:
            report += "## ⚠️ Limited Improvement\n"
            report += "Some routing improvements achieved, but additional work is needed.\n"
        
        return report
    
    def save_results(self, results: Dict[str, Any]):
        """Save test results."""
        # Save JSON results
        with open("improved_routing_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        # Save markdown report
        report = self.generate_report(results)
        with open("improved_routing_test_report.md", "w") as f:
            f.write(report)
        
        logger.info("📄 Results saved:")
        logger.info("  • improved_routing_test_results.json")
        logger.info("  • improved_routing_test_report.md")

def main():
    """Run improved routing system test."""
    tester = ImprovedRoutingTester()
    
    try:
        # Run test
        results = tester.test_improved_routing()
        
        # Save results
        tester.save_results(results)
        
        # Print summary
        print("\n" + "="*70)
        print("IMPROVED ROUTING SYSTEM TEST RESULTS")
        print("="*70)
        
        summary = results['test_summary']
        print(f"📊 Cases Fixed: {summary['fixed_cases']}/{summary['total_cases']} ({summary['improvement_rate']:.1f}%)")
        print(f"⏱️ Avg Time: {summary['average_time']:.2f}s")
        print(f"🎯 Avg Confidence: {summary['average_confidence']:.2f}")
        
        analysis = results['analysis']
        if analysis['corrections_applied'] > 0:
            print(f"🔧 Corrections Applied: {analysis['corrections_applied']}")
        
        print(f"\n📋 Results by Case:")
        for result in results['detailed_results']:
            status = "✅ FIXED" if result['is_fixed'] else "❌ FAIL"
            print(f"  {result['test_id']}: {status} ({result['new_result']})")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Testing failed: {e}")
        raise

if __name__ == "__main__":
    main()