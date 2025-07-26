#!/usr/bin/env python3
"""
Agent-Intent Mapping Audit and Analysis

This script audits the current agent-intent registry for overlaps, ambiguities,
and routing issues. It analyzes the configuration and suggests improvements.
"""

import json
import yaml
import logging
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MappingIssue:
    """Represents an issue found in the agent-intent mapping."""
    issue_type: str
    severity: str
    intent: str
    description: str
    recommendation: str

@dataclass
class AgentMapping:
    """Represents an agent's capabilities and current mappings."""
    agent_name: str
    primary_intents: List[str]
    secondary_intents: List[str]
    capabilities: List[str]
    confidence_thresholds: Dict[str, float]
    resource_intensive: bool

class AgentMappingAuditor:
    """Audits the agent-intent registry for issues and improvements."""
    
    def __init__(self, registry_path: str = "config/agent_intent_registry.yaml"):
        self.registry_path = registry_path
        self.registry = self._load_registry()
        self.intents = self.registry.get('intents', {})
        self.agents = self.registry.get('agents', {})
        self.workflows = self.registry.get('workflows', {})
        self.issues: List[MappingIssue] = []
        
    def _load_registry(self) -> Dict[str, Any]:
        """Load the agent intent registry."""
        try:
            with open(self.registry_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}
    
    def audit_all(self) -> Dict[str, Any]:
        """Run comprehensive audit of agent-intent mappings."""
        logger.info("🔍 Starting comprehensive agent-intent mapping audit...")
        
        # Run all audit checks
        self._audit_intent_agent_mappings()
        self._audit_agent_capabilities()
        self._audit_confidence_thresholds()
        self._audit_fallback_logic()
        self._audit_workflow_conflicts()
        self._analyze_missing_mappings()
        
        # Generate summary
        summary = self._generate_audit_summary()
        
        logger.info(f"📊 Audit complete. Found {len(self.issues)} issues.")
        return summary
    
    def _audit_intent_agent_mappings(self):
        """Audit basic intent-to-agent mappings for issues."""
        logger.info("🎯 Auditing intent-agent mappings...")
        
        # Track agent usage
        agent_usage = {}
        invalid_agents = []
        
        for intent_name, intent_config in self.intents.items():
            primary_agent = intent_config.get('primary_agent')
            fallback_agent = intent_config.get('fallback_agent')
            
            # Check primary agent exists
            if primary_agent:
                if primary_agent not in self.agents:
                    invalid_agents.append((intent_name, primary_agent))
                    self.issues.append(MappingIssue(
                        issue_type="invalid_agent",
                        severity="high",
                        intent=intent_name,
                        description=f"Primary agent '{primary_agent}' not defined in agents section",
                        recommendation=f"Add '{primary_agent}' to agents section or update mapping"
                    ))
                else:
                    agent_usage[primary_agent] = agent_usage.get(primary_agent, 0) + 10  # Primary = 10 points
            
            # Check fallback agent exists
            if fallback_agent and fallback_agent not in self.agents:
                self.issues.append(MappingIssue(
                    issue_type="invalid_fallback",
                    severity="medium",
                    intent=intent_name,
                    description=f"Fallback agent '{fallback_agent}' not defined",
                    recommendation=f"Add '{fallback_agent}' to agents section or remove fallback"
                ))
        
        # Check for over-utilized agents
        for agent, usage in agent_usage.items():
            if usage > 30:  # Arbitrary threshold for over-utilization
                primary_intents = [i for i, c in self.intents.items() if c.get('primary_agent') == agent]
                self.issues.append(MappingIssue(
                    issue_type="agent_overload",
                    severity="medium",
                    intent=f"multiple_intents",
                    description=f"Agent '{agent}' is primary for {len(primary_intents)} intents: {primary_intents}",
                    recommendation="Consider splitting responsibilities or creating specialized agents"
                ))
    
    def _audit_agent_capabilities(self):
        """Audit agent capabilities alignment with assigned intents."""
        logger.info("🛠️ Auditing agent capabilities alignment...")
        
        # Expected capabilities for each intent type
        intent_capability_map = {
            'web_research': ['web_scraping', 'content_extraction', 'url_fetching'],
            'codebase_query': ['rag_search', 'code_retrieval', 'pattern_matching'],
            'code_generation': ['code_synthesis', 'implementation', 'boilerplate_generation'],
            'code_editing': ['precise_edits', 'refactoring', 'bug_fixes'],
            'code_analysis': ['static_analysis', 'linting', 'security_checks', 'llm_review'],
            'documentation': ['tech_writing', 'api_docs', 'usage_examples'],
            'tool_execution': ['file_operations', 'terminal_commands', 'system_actions']
        }
        
        for intent_name, intent_config in self.intents.items():
            primary_agent = intent_config.get('primary_agent')
            if not primary_agent or primary_agent not in self.agents:
                continue
                
            agent_capabilities = self.agents[primary_agent].get('capabilities', [])
            expected_capabilities = intent_capability_map.get(intent_name, [])
            
            # Check if agent has required capabilities
            missing_capabilities = [cap for cap in expected_capabilities if cap not in agent_capabilities]
            if missing_capabilities:
                self.issues.append(MappingIssue(
                    issue_type="capability_mismatch",
                    severity="medium",
                    intent=intent_name,
                    description=f"Agent '{primary_agent}' missing capabilities: {missing_capabilities}",
                    recommendation=f"Add missing capabilities to agent or reassign intent"
                ))
            
            # Check for unnecessary capabilities (might indicate wrong agent assignment)
            unnecessary = [cap for cap in agent_capabilities if cap not in expected_capabilities and expected_capabilities]
            if len(unnecessary) > len(expected_capabilities):  # More unnecessary than necessary
                self.issues.append(MappingIssue(
                    issue_type="capability_bloat",
                    severity="low",
                    intent=intent_name,
                    description=f"Agent '{primary_agent}' has many unrelated capabilities: {unnecessary}",
                    recommendation="Consider using more specialized agent or creating new agent"
                ))
    
    def _audit_confidence_thresholds(self):
        """Audit confidence threshold settings for each intent."""
        logger.info("📊 Auditing confidence thresholds...")
        
        # Analyze threshold distribution
        thresholds = []
        problematic_thresholds = []
        
        for intent_name, intent_config in self.intents.items():
            threshold = intent_config.get('confidence_threshold', 0.7)
            thresholds.append(threshold)
            
            # Check for problematic thresholds
            if threshold > 0.95:
                problematic_thresholds.append((intent_name, threshold, "too_high"))
                self.issues.append(MappingIssue(
                    issue_type="threshold_too_high",
                    severity="medium",
                    intent=intent_name,
                    description=f"Confidence threshold {threshold} is very high, may cause false negatives",
                    recommendation="Consider lowering threshold or improving classification prompts"
                ))
            elif threshold < 0.3:
                problematic_thresholds.append((intent_name, threshold, "too_low"))
                self.issues.append(MappingIssue(
                    issue_type="threshold_too_low",
                    severity="medium",
                    intent=intent_name,
                    description=f"Confidence threshold {threshold} is very low, may cause false positives",
                    recommendation="Consider raising threshold or adding validation steps"
                ))
        
        # Check for clustering issues
        avg_threshold = sum(thresholds) / len(thresholds) if thresholds else 0.7
        
        # Identify intents that should have similar thresholds but don't
        similar_intents = [
            (['code_generation', 'code_editing'], "code modification"),
            (['code_analysis', 'documentation'], "code review"),
            (['codebase_query', 'general_query'], "information retrieval")
        ]
        
        for intent_group, group_name in similar_intents:
            group_thresholds = []
            for intent in intent_group:
                if intent in self.intents:
                    group_thresholds.append(self.intents[intent].get('confidence_threshold', 0.7))
            
            if len(group_thresholds) > 1:
                threshold_range = max(group_thresholds) - min(group_thresholds)
                if threshold_range > 0.2:  # Significant difference
                    self.issues.append(MappingIssue(
                        issue_type="threshold_inconsistency",
                        severity="low",
                        intent=f"{group_name}_group",
                        description=f"Similar intents {intent_group} have inconsistent thresholds: {group_thresholds}",
                        recommendation="Consider aligning thresholds for similar intent types"
                    ))
    
    def _audit_fallback_logic(self):
        """Audit fallback mechanisms and error handling."""
        logger.info("🛡️ Auditing fallback logic...")
        
        # Check if there's a proper fallback intent
        fallback_intents = [name for name, config in self.intents.items() if config.get('is_fallback', False)]
        
        if not fallback_intents:
            self.issues.append(MappingIssue(
                issue_type="missing_fallback",
                severity="high",
                intent="system",
                description="No fallback intent defined for handling unclear classifications",
                recommendation="Add a general_query or fallback intent with is_fallback: true"
            ))
        elif len(fallback_intents) > 1:
            self.issues.append(MappingIssue(
                issue_type="multiple_fallbacks",
                severity="medium",
                intent="system",
                description=f"Multiple fallback intents defined: {fallback_intents}",
                recommendation="Consolidate to single fallback intent to avoid confusion"
            ))
        
        # Check for circular fallback references
        for intent_name, intent_config in self.intents.items():
            fallback_agent = intent_config.get('fallback_agent')
            primary_agent = intent_config.get('primary_agent')
            
            if fallback_agent == primary_agent:
                self.issues.append(MappingIssue(
                    issue_type="circular_fallback",
                    severity="medium",
                    intent=intent_name,
                    description=f"Intent has same primary and fallback agent: {primary_agent}",
                    recommendation="Use different agent for fallback or remove fallback_agent"
                ))
    
    def _audit_workflow_conflicts(self):
        """Audit workflow definitions for conflicts with intent mappings."""
        logger.info("🔄 Auditing workflow configurations...")
        
        # Track workflow trigger coverage
        workflow_triggers = set()
        for workflow_name, workflow_config in self.workflows.items():
            triggers = workflow_config.get('trigger_intents', [])
            workflow_triggers.update(triggers)
            
            # Check if workflow agents match intent mappings
            workflow_steps = workflow_config.get('workflow', [])
            for step in workflow_steps:
                step_agent = step.get('agent')
                if step.get('step') == 1:  # First step should match primary intent agent
                    for trigger in triggers:
                        if trigger in self.intents:
                            primary_agent = self.intents[trigger].get('primary_agent')
                            if step_agent != primary_agent:
                                self.issues.append(MappingIssue(
                                    issue_type="workflow_agent_mismatch",
                                    severity="medium",
                                    intent=trigger,
                                    description=f"Workflow '{workflow_name}' step 1 uses '{step_agent}' but intent maps to '{primary_agent}'",
                                    recommendation="Align workflow first step with intent primary agent"
                                ))
        
        # Check for intents that might need workflows but don't have them
        complex_intents = []
        for intent_name, intent_config in self.intents.items():
            if (intent_config.get('requires_context_check') or 
                intent_config.get('post_analysis_intents') or
                intent_config.get('prerequisite_intent')):
                if intent_name not in workflow_triggers:
                    complex_intents.append(intent_name)
        
        if complex_intents:
            self.issues.append(MappingIssue(
                issue_type="missing_workflows",
                severity="low",
                intent="system",
                description=f"Complex intents without workflows: {complex_intents}",
                recommendation="Consider creating workflows for multi-step intents"
            ))
    
    def _analyze_missing_mappings(self):
        """Analyze potential missing intent-agent mappings."""
        logger.info("🔍 Analyzing missing mappings...")
        
        # Check for agents without primary intent assignments
        assigned_agents = set()
        for intent_config in self.intents.values():
            if intent_config.get('primary_agent'):
                assigned_agents.add(intent_config['primary_agent'])
        
        unassigned_agents = set(self.agents.keys()) - assigned_agents
        if unassigned_agents:
            self.issues.append(MappingIssue(
                issue_type="unassigned_agents",
                severity="low",
                intent="system",
                description=f"Agents without primary intent assignments: {list(unassigned_agents)}",
                recommendation="Assign intents to agents or remove unused agent definitions"
            ))
        
        # Common intents that might be missing
        potential_missing_intents = [
            'file_management',
            'project_setup',
            'debugging',
            'testing',
            'deployment',
            'performance_optimization',
            'security_audit'
        ]
        
        existing_intents = set(self.intents.keys())
        truly_missing = [intent for intent in potential_missing_intents if intent not in existing_intents]
        
        if truly_missing:
            self.issues.append(MappingIssue(
                issue_type="potentially_missing_intents",
                severity="low",
                intent="system",
                description=f"Common intents that might be missing: {truly_missing}",
                recommendation="Consider adding these intents if they align with user needs"
            ))
    
    def _generate_audit_summary(self) -> Dict[str, Any]:
        """Generate comprehensive audit summary."""
        
        # Categorize issues by severity
        issues_by_severity = {'high': [], 'medium': [], 'low': []}
        issues_by_type = {}
        
        for issue in self.issues:
            issues_by_severity[issue.severity].append(issue)
            if issue.issue_type not in issues_by_type:
                issues_by_type[issue.issue_type] = []
            issues_by_type[issue.issue_type].append(issue)
        
        # Generate agent usage statistics
        agent_stats = {}
        for intent_name, intent_config in self.intents.items():
            primary_agent = intent_config.get('primary_agent')
            if primary_agent:
                if primary_agent not in agent_stats:
                    agent_stats[primary_agent] = {'primary_intents': [], 'avg_threshold': 0}
                agent_stats[primary_agent]['primary_intents'].append(intent_name)
                agent_stats[primary_agent]['avg_threshold'] += intent_config.get('confidence_threshold', 0.7)
        
        # Calculate averages
        for agent, stats in agent_stats.items():
            if stats['primary_intents']:
                stats['avg_threshold'] /= len(stats['primary_intents'])
        
        return {
            'audit_summary': {
                'total_issues': len(self.issues),
                'high_severity': len(issues_by_severity['high']),
                'medium_severity': len(issues_by_severity['medium']),
                'low_severity': len(issues_by_severity['low']),
                'total_intents': len(self.intents),
                'total_agents': len(self.agents),
                'total_workflows': len(self.workflows)
            },
            'issues_by_severity': issues_by_severity,
            'issues_by_type': issues_by_type,
            'agent_utilization': agent_stats,
            'recommendations': self._generate_priority_recommendations()
        }
    
    def _generate_priority_recommendations(self) -> List[Dict[str, Any]]:
        """Generate prioritized recommendations for fixes."""
        high_priority = [issue for issue in self.issues if issue.severity == 'high']
        medium_priority = [issue for issue in self.issues if issue.severity == 'medium']
        
        recommendations = []
        
        # High priority fixes
        for issue in high_priority:
            recommendations.append({
                'priority': 'HIGH',
                'issue_type': issue.issue_type,
                'intent': issue.intent,
                'action': issue.recommendation,
                'impact': 'Critical system functionality'
            })
        
        # Medium priority grouped by type
        issue_type_counts = {}
        for issue in medium_priority:
            issue_type_counts[issue.issue_type] = issue_type_counts.get(issue.issue_type, 0) + 1
        
        # Focus on most frequent medium issues
        for issue_type, count in sorted(issue_type_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 1:  # Multiple instances of same issue type
                examples = [issue for issue in medium_priority if issue.issue_type == issue_type][:2]
                recommendations.append({
                    'priority': 'MEDIUM',
                    'issue_type': issue_type,
                    'count': count,
                    'action': f"Fix {count} instances of {issue_type}",
                    'examples': [{'intent': ex.intent, 'recommendation': ex.recommendation} for ex in examples],
                    'impact': 'Improved routing accuracy and reliability'
                })
        
        return recommendations
    
    def generate_report(self, summary: Dict[str, Any]) -> str:
        """Generate comprehensive audit report."""
        report = "# Agent-Intent Mapping Audit Report\n\n"
        
        # Overview
        audit_summary = summary['audit_summary']
        report += "## Audit Overview\n"
        report += f"- **Total Issues Found**: {audit_summary['total_issues']}\n"
        report += f"- **High Severity**: {audit_summary['high_severity']}\n"
        report += f"- **Medium Severity**: {audit_summary['medium_severity']}\n"
        report += f"- **Low Severity**: {audit_summary['low_severity']}\n"
        report += f"- **Registry Stats**: {audit_summary['total_intents']} intents, {audit_summary['total_agents']} agents, {audit_summary['total_workflows']} workflows\n\n"
        
        # Priority Recommendations
        report += "## Priority Recommendations\n\n"
        for rec in summary['recommendations']:
            priority_symbol = "🔥" if rec['priority'] == 'HIGH' else "⚠️"
            report += f"### {priority_symbol} {rec['priority']} PRIORITY\n"
            report += f"**Issue Type**: {rec['issue_type']}\n"
            
            if 'count' in rec:
                report += f"**Instances**: {rec['count']}\n"
                report += f"**Action**: {rec['action']}\n"
                if 'examples' in rec:
                    report += "**Examples**:\n"
                    for ex in rec['examples']:
                        report += f"- {ex['intent']}: {ex['recommendation']}\n"
            else:
                report += f"**Intent**: {rec['intent']}\n"
                report += f"**Action**: {rec['action']}\n"
            
            report += f"**Impact**: {rec['impact']}\n\n"
        
        # Agent Utilization Analysis
        report += "## Agent Utilization Analysis\n\n"
        agent_stats = summary['agent_utilization']
        for agent, stats in sorted(agent_stats.items(), key=lambda x: len(x[1]['primary_intents']), reverse=True):
            intent_count = len(stats['primary_intents'])
            avg_threshold = stats['avg_threshold']
            
            utilization_level = "🔥 High" if intent_count > 2 else "✅ Balanced" if intent_count == 2 else "⚡ Low"
            
            report += f"**{agent}** - {utilization_level} Utilization\n"
            report += f"- Primary intents ({intent_count}): {', '.join(stats['primary_intents'])}\n"
            report += f"- Average confidence threshold: {avg_threshold:.2f}\n\n"
        
        # Detailed Issues by Type
        issues_by_type = summary['issues_by_type']
        if issues_by_type:
            report += "## Detailed Issues by Type\n\n"
            for issue_type, issues in issues_by_type.items():
                report += f"### {issue_type.replace('_', ' ').title()} ({len(issues)} issues)\n"
                for issue in issues[:3]:  # Show first 3 examples
                    severity_symbol = "🔥" if issue.severity == 'high' else "⚠️" if issue.severity == 'medium' else "ℹ️"
                    report += f"- {severity_symbol} **{issue.intent}**: {issue.description}\n"
                    report += f"  *Recommendation*: {issue.recommendation}\n"
                
                if len(issues) > 3:
                    report += f"  ... and {len(issues) - 3} more\n"
                report += "\n"
        
        return report
    
    def save_results(self, summary: Dict[str, Any]):
        """Save audit results to files."""
        # Save JSON results
        with open("agent_mapping_audit_results.json", "w") as f:
            # Convert dataclasses to dicts for JSON serialization
            json_summary = {}
            for key, value in summary.items():
                if key in ['issues_by_severity', 'issues_by_type']:
                    json_summary[key] = {}
                    for subkey, subvalue in value.items():
                        json_summary[key][subkey] = [
                            {
                                'issue_type': issue.issue_type,
                                'severity': issue.severity,
                                'intent': issue.intent,
                                'description': issue.description,
                                'recommendation': issue.recommendation
                            } for issue in subvalue
                        ]
                else:
                    json_summary[key] = value
            
            json.dump(json_summary, f, indent=2)
        
        # Save markdown report
        report = self.generate_report(summary)
        with open("agent_mapping_audit_report.md", "w") as f:
            f.write(report)
        
        logger.info("📄 Audit results saved:")
        logger.info("  • agent_mapping_audit_results.json")
        logger.info("  • agent_mapping_audit_report.md")

def main():
    """Run agent-intent mapping audit."""
    auditor = AgentMappingAuditor()
    
    try:
        # Run comprehensive audit
        summary = auditor.audit_all()
        
        # Save results
        auditor.save_results(summary)
        
        # Print summary
        print("\n" + "="*70)
        print("AGENT-INTENT MAPPING AUDIT RESULTS")
        print("="*70)
        
        audit_summary = summary['audit_summary']
        print(f"📊 Total Issues: {audit_summary['total_issues']}")
        print(f"🔥 High Severity: {audit_summary['high_severity']}")
        print(f"⚠️ Medium Severity: {audit_summary['medium_severity']}")
        print(f"ℹ️ Low Severity: {audit_summary['low_severity']}")
        
        print(f"\n📈 Registry Stats:")
        print(f"  • Intents: {audit_summary['total_intents']}")
        print(f"  • Agents: {audit_summary['total_agents']}")
        print(f"  • Workflows: {audit_summary['total_workflows']}")
        
        print(f"\n🎯 Top Priority Actions:")
        for i, rec in enumerate(summary['recommendations'][:3], 1):
            priority_symbol = "🔥" if rec['priority'] == 'HIGH' else "⚠️"
            print(f"  {i}. {priority_symbol} {rec['issue_type']}: {rec['action']}")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Audit failed: {e}")
        raise

if __name__ == "__main__":
    main()