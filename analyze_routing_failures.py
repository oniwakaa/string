#!/usr/bin/env python3
"""
Analyze Routing Failures from Regression Test

This script analyzes the 5 failed cases from the regression test to understand
routing issues and suggest specific mapping rule adjustments.
"""

import json
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RoutingFailure:
    """Represents a routing failure case."""
    test_id: str
    prompt: str
    expected_intent: str
    actual_intent: str
    confidence: float
    category: str
    difficulty: str
    issue_analysis: str
    suggested_fix: str

class RoutingFailureAnalyzer:
    """Analyzes routing failures and suggests mapping improvements."""
    
    def __init__(self):
        # Based on the regression test output, these are the known failures
        self.failed_cases = [
            {
                "test_id": "wr_001",
                "prompt": "Get the latest Python documentation from the official website",
                "expected_intent": "web_research", 
                "actual_intent": "documentation",
                "confidence": 0.90,
                "category": "edge_case",
                "difficulty": "medium"
            },
            {
                "test_id": "wr_002", 
                "prompt": "Fetch API information from external sources and libraries",
                "expected_intent": "web_research",
                "actual_intent": "documentation", 
                "confidence": 0.90,
                "category": "edge_case",
                "difficulty": "medium"
            },
            {
                "test_id": "te_001",
                "prompt": "Execute all unit tests and report any failures",
                "expected_intent": "tool_execution",
                "actual_intent": "code_analysis",
                "confidence": 0.90,
                "category": "edge_case", 
                "difficulty": "medium"
            },
            {
                "test_id": "te_003",
                "prompt": "Test this function with various input values",
                "expected_intent": "tool_execution",
                "actual_intent": "code_analysis",
                "confidence": 0.90,
                "category": "edge_case",
                "difficulty": "medium"
            },
            {
                "test_id": "amb_004",
                "prompt": "Find and fix performance issues in the code",
                "expected_intent": "code_editing",
                "actual_intent": "code_analysis",
                "confidence": 0.90,
                "category": "ambiguous",
                "difficulty": "hard"
            }
        ]
        
        self.routing_failures = []
        
    def analyze_failures(self) -> Dict[str, Any]:
        """Analyze each failure case to understand routing issues."""
        logger.info("🔍 Analyzing routing failures from regression test...")
        
        for case in self.failed_cases:
            analysis = self._analyze_single_failure(case)
            self.routing_failures.append(analysis)
        
        # Analyze patterns across failures
        patterns = self._identify_failure_patterns()
        
        # Generate specific mapping fixes
        mapping_fixes = self._generate_mapping_fixes()
        
        return {
            "failure_analysis": {
                "total_failures": len(self.routing_failures),
                "individual_analyses": [self._failure_to_dict(f) for f in self.routing_failures],
                "common_patterns": patterns,
                "mapping_fixes": mapping_fixes
            }
        }
    
    def _analyze_single_failure(self, case: Dict[str, Any]) -> RoutingFailure:
        """Analyze a single routing failure case."""
        test_id = case["test_id"]
        prompt = case["prompt"]
        expected = case["expected_intent"]
        actual = case["actual_intent"]
        confidence = case["confidence"]
        
        # Analyze the specific confusion
        issue_analysis, suggested_fix = self._diagnose_confusion(prompt, expected, actual, confidence)
        
        return RoutingFailure(
            test_id=test_id,
            prompt=prompt,
            expected_intent=expected,
            actual_intent=actual,
            confidence=confidence,
            category=case["category"],
            difficulty=case["difficulty"],
            issue_analysis=issue_analysis,
            suggested_fix=suggested_fix
        )
    
    def _diagnose_confusion(self, prompt: str, expected: str, actual: str, confidence: float) -> Tuple[str, str]:
        """Diagnose the specific cause of routing confusion."""
        
        # Web research vs documentation confusion
        if expected == "web_research" and actual == "documentation":
            if "documentation" in prompt.lower():
                issue = f"Prompt contains 'documentation' keyword, causing confusion with documentation intent"
                fix = "Strengthen web_research prompt template to prioritize external source indicators (website, fetch, get from) over content type"
            else:
                issue = f"External source indicators not strong enough in prompt template"
                fix = "Add explicit 'external source' vs 'internal doc creation' distinction in prompt template"
        
        # Tool execution vs code analysis confusion  
        elif expected == "tool_execution" and actual == "code_analysis":
            if "test" in prompt.lower() and "function" in prompt.lower():
                issue = f"'Test function' phrase interpreted as code analysis rather than test execution"
                fix = "Add specific execution keywords (run, execute, perform) to tool_execution template to distinguish from analysis"
            elif "report" in prompt.lower():
                issue = f"'Report' keyword associated with analysis rather than execution output"
                fix = "Clarify in tool_execution template that execution includes reporting results, not just analysis"
            else:
                issue = f"Action words not clearly distinguished from analysis words"
                fix = "Strengthen action-oriented language in tool_execution vs passive analysis language"
        
        # Code editing vs code analysis confusion
        elif expected == "code_editing" and actual == "code_analysis":
            if "find" in prompt.lower() and "fix" in prompt.lower():
                issue = f"'Find and fix' interpreted as analysis first, missing the editing action"
                fix = "Update code_editing template to emphasize that 'fix' implies modification action, not just identification"
            else:
                issue = f"Analysis component overshadowing modification intent"
                fix = "Strengthen modification verbs (fix, change, modify, update) in code_editing template"
        
        else:
            issue = f"Unexpected confusion between {expected} and {actual}"
            fix = f"Add specific negative examples to distinguish {expected} from {actual}"
        
        return issue, fix
    
    def _identify_failure_patterns(self) -> Dict[str, Any]:
        """Identify common patterns across routing failures."""
        
        # Group by confusion type
        confusion_patterns = {}
        for failure in self.routing_failures:
            confusion_key = f"{failure.expected_intent} → {failure.actual_intent}"
            if confusion_key not in confusion_patterns:
                confusion_patterns[confusion_key] = []
            confusion_patterns[confusion_key].append(failure)
        
        # Analyze each pattern
        pattern_analysis = {}
        for pattern, failures in confusion_patterns.items():
            common_keywords = self._find_common_keywords(failures)
            avg_confidence = sum(f.confidence for f in failures) / len(failures)
            
            pattern_analysis[pattern] = {
                "frequency": len(failures),
                "avg_confidence": avg_confidence,
                "common_keywords": common_keywords,
                "test_ids": [f.test_id for f in failures],
                "root_cause": self._identify_root_cause(failures)
            }
        
        return {
            "confusion_patterns": pattern_analysis,
            "most_problematic": max(confusion_patterns.items(), key=lambda x: len(x[1]))[0] if confusion_patterns else None,
            "high_confidence_errors": [f for f in self.routing_failures if f.confidence > 0.85]
        }
    
    def _find_common_keywords(self, failures: List[RoutingFailure]) -> List[str]:
        """Find keywords common across failure cases."""
        all_words = []
        for failure in failures:
            words = [word.lower().strip(".,!?") for word in failure.prompt.split()]
            all_words.extend(words)
        
        # Count word frequency
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Return words that appear in multiple cases
        common_words = [word for word, count in word_counts.items() if count > 1 and len(word) > 3]
        return common_words[:5]  # Top 5 common words
    
    def _identify_root_cause(self, failures: List[RoutingFailure]) -> str:
        """Identify the root cause for a group of similar failures."""
        if not failures:
            return "Unknown"
        
        expected = failures[0].expected_intent
        actual = failures[0].actual_intent
        
        if expected == "web_research" and actual == "documentation":
            return "Content type keywords (documentation, API) override source location keywords (website, external)"
        elif expected == "tool_execution" and actual == "code_analysis":
            return "Analysis verbs (test, report) interpreted as passive observation rather than active execution"
        elif expected == "code_editing" and actual == "code_analysis":
            return "Multi-step actions (find and fix) prioritize discovery phase over modification phase"
        else:
            return f"Semantic overlap between {expected} and {actual} intents"
    
    def _generate_mapping_fixes(self) -> List[Dict[str, Any]]:
        """Generate specific fixes for the agent-intent registry."""
        
        fixes = []
        
        # Fix 1: Strengthen web_research vs documentation distinction
        web_doc_failures = [f for f in self.routing_failures if f.expected_intent == "web_research" and f.actual_intent == "documentation"]
        if web_doc_failures:
            fixes.append({
                "fix_type": "prompt_template_update",
                "target_intent": "web_research",
                "issue": "Confused with documentation intent when content type is mentioned",
                "current_definition": "Get external info (NOT code modification)",
                "improved_definition": "Get info from external websites/sources (NOT create internal docs)",
                "additional_examples": [
                    "fetch latest docs from official website", 
                    "scrape API info from external sources",
                    "get documentation from web"
                ],
                "negative_examples": [
                    "NOT: create documentation",
                    "NOT: document existing code", 
                    "NOT: write API docs"
                ]
            })
        
        # Fix 2: Strengthen tool_execution vs code_analysis distinction  
        tool_analysis_failures = [f for f in self.routing_failures if f.expected_intent == "tool_execution" and f.actual_intent == "code_analysis"]
        if tool_analysis_failures:
            fixes.append({
                "fix_type": "prompt_template_update", 
                "target_intent": "tool_execution",
                "issue": "Confused with code_analysis when reporting or testing is mentioned",
                "current_definition": "Run/execute/test (NOT inspect/analyze)",
                "improved_definition": "Run/execute/perform actions that produce output (NOT passive review)",
                "additional_examples": [
                    "execute tests and show results",
                    "run function with test inputs", 
                    "perform unit tests"
                ],
                "negative_examples": [
                    "NOT: analyze test results",
                    "NOT: review function logic",
                    "NOT: inspect code quality"
                ]
            })
        
        # Fix 3: Strengthen code_editing vs code_analysis distinction
        edit_analysis_failures = [f for f in self.routing_failures if f.expected_intent == "code_editing" and f.actual_intent == "code_analysis"]
        if edit_analysis_failures:
            fixes.append({
                "fix_type": "prompt_template_update",
                "target_intent": "code_editing", 
                "issue": "Multi-step phrases like 'find and fix' prioritize discovery over modification",
                "current_definition": "Modify existing code (NOT create new)",
                "improved_definition": "Change/modify/fix code files (NOT just identify issues)",
                "additional_examples": [
                    "find and fix the bug",
                    "locate and resolve performance issues",
                    "identify and correct the error"
                ],
                "negative_examples": [
                    "NOT: analyze for issues",
                    "NOT: review code quality", 
                    "NOT: inspect without changing"
                ]
            })
        
        # Fix 4: Adjust confidence thresholds
        high_confidence_errors = [f for f in self.routing_failures if f.confidence > 0.85]
        if high_confidence_errors:
            fixes.append({
                "fix_type": "confidence_threshold_adjustment",
                "issue": f"{len(high_confidence_errors)} failures had high confidence (>0.85), indicating systematic misclassification",
                "affected_intents": list(set(f.expected_intent for f in high_confidence_errors)),
                "recommendation": "Consider adding validation step for high-confidence classifications that fall into common confusion patterns",
                "validation_rules": [
                    "If web_research classified but contains 'documentation', verify external source indicators",
                    "If code_analysis classified but contains action verbs (run, execute, fix), verify intended outcome",
                    "If classification confidence > 0.9 but result seems wrong, trigger clarification"
                ]
            })
        
        return fixes
    
    def _failure_to_dict(self, failure: RoutingFailure) -> Dict[str, Any]:
        """Convert RoutingFailure to dictionary for JSON serialization."""
        return {
            "test_id": failure.test_id,
            "prompt": failure.prompt,
            "expected_intent": failure.expected_intent,
            "actual_intent": failure.actual_intent,
            "confidence": failure.confidence,
            "category": failure.category,
            "difficulty": failure.difficulty,
            "issue_analysis": failure.issue_analysis,
            "suggested_fix": failure.suggested_fix
        }
    
    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """Generate comprehensive routing failure analysis report."""
        
        report = "# Routing Failure Analysis Report\n\n"
        
        failure_data = analysis["failure_analysis"]
        
        # Overview
        report += "## Analysis Overview\n"
        report += f"- **Total Routing Failures**: {failure_data['total_failures']}\n"
        report += f"- **High Confidence Errors**: {len([f for f in failure_data['individual_analyses'] if f['confidence'] > 0.85])}\n"
        report += f"- **Most Problematic Pattern**: {failure_data['common_patterns'].get('most_problematic', 'None')}\n\n"
        
        # Individual Failure Analysis
        report += "## Individual Failure Analysis\n\n"
        for failure in failure_data["individual_analyses"]:
            report += f"### {failure['test_id']} - {failure['category'].title()} Case\n"
            report += f"**Prompt**: \"{failure['prompt']}\"\n"
            report += f"**Expected**: {failure['expected_intent']} → **Got**: {failure['actual_intent']} (confidence: {failure['confidence']:.2f})\n"
            report += f"**Issue**: {failure['issue_analysis']}\n"
            report += f"**Fix**: {failure['suggested_fix']}\n\n"
        
        # Pattern Analysis
        patterns = failure_data["common_patterns"]["confusion_patterns"]
        if patterns:
            report += "## Common Confusion Patterns\n\n"
            for pattern, data in sorted(patterns.items(), key=lambda x: x[1]["frequency"], reverse=True):
                report += f"### {pattern} ({data['frequency']} cases)\n"
                report += f"- **Average Confidence**: {data['avg_confidence']:.2f}\n"
                report += f"- **Common Keywords**: {', '.join(data['common_keywords'])}\n"
                report += f"- **Test Cases**: {', '.join(data['test_ids'])}\n"
                report += f"- **Root Cause**: {data['root_cause']}\n\n"
        
        # Specific Mapping Fixes
        fixes = failure_data["mapping_fixes"]
        if fixes:
            report += "## Recommended Mapping Fixes\n\n"
            for i, fix in enumerate(fixes, 1):
                if fix["fix_type"] == "prompt_template_update":
                    report += f"### Fix {i}: Update {fix['target_intent']} Template\n"
                    report += f"**Issue**: {fix['issue']}\n"
                    report += f"**Current**: {fix['current_definition']}\n"
                    report += f"**Improved**: {fix['improved_definition']}\n"
                    
                    if "additional_examples" in fix:
                        report += f"**Add Examples**:\n"
                        for example in fix["additional_examples"]:
                            report += f"- \"{example}\"\n"
                    
                    if "negative_examples" in fix:
                        report += f"**Add Negative Examples**:\n"
                        for example in fix["negative_examples"]:
                            report += f"- {example}\n"
                    
                elif fix["fix_type"] == "confidence_threshold_adjustment":
                    report += f"### Fix {i}: Confidence Validation Rules\n"
                    report += f"**Issue**: {fix['issue']}\n"
                    report += f"**Affected Intents**: {', '.join(fix['affected_intents'])}\n"
                    report += f"**Recommendation**: {fix['recommendation']}\n"
                    
                    if "validation_rules" in fix:
                        report += f"**Validation Rules**:\n"
                        for rule in fix["validation_rules"]:
                            report += f"- {rule}\n"
                
                report += "\n"
        
        # Implementation Priority
        report += "## Implementation Priority\n\n"
        report += "1. **HIGH**: Update prompt templates for web_research, tool_execution, and code_editing\n"
        report += "2. **MEDIUM**: Add confidence validation rules for high-confidence misclassifications\n"
        report += "3. **LOW**: Monitor routing accuracy after template updates\n\n"
        
        return report
    
    def save_results(self, analysis: Dict[str, Any]):
        """Save analysis results to files."""
        # Save markdown report only (JSON has serialization issues)
        report = self.generate_report(analysis)
        with open("routing_failure_analysis.md", "w") as f:
            f.write(report)
        
        logger.info("📄 Analysis results saved:")
        logger.info("  • routing_failure_analysis.md")

def main():
    """Run routing failure analysis."""
    analyzer = RoutingFailureAnalyzer()
    
    try:
        # Analyze failures
        analysis = analyzer.analyze_failures()
        
        # Save results
        analyzer.save_results(analysis)
        
        # Print summary
        print("\n" + "="*70)
        print("ROUTING FAILURE ANALYSIS RESULTS")
        print("="*70)
        
        failure_data = analysis["failure_analysis"]
        print(f"📊 Total Failures Analyzed: {failure_data['total_failures']}")
        
        patterns = failure_data["common_patterns"]["confusion_patterns"]
        print(f"\n🔄 Confusion Patterns:")
        for pattern, data in sorted(patterns.items(), key=lambda x: x[1]["frequency"], reverse=True):
            print(f"  • {pattern}: {data['frequency']} cases (avg conf: {data['avg_confidence']:.2f})")
        
        print(f"\n🛠️ Mapping Fixes Generated: {len(failure_data['mapping_fixes'])}")
        for i, fix in enumerate(failure_data['mapping_fixes'], 1):
            if fix["fix_type"] == "prompt_template_update":
                print(f"  {i}. Update {fix['target_intent']} template")
            else:
                print(f"  {i}. {fix['fix_type']}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise

if __name__ == "__main__":
    main()