# Agent-Intent Mapping Audit Report

## Audit Overview
- **Total Issues Found**: 3
- **High Severity**: 0
- **Medium Severity**: 0
- **Low Severity**: 3
- **Registry Stats**: 8 intents, 7 agents, 4 workflows

## Priority Recommendations

## Agent Utilization Analysis

**codebase_expert** - ✅ Balanced Utilization
- Primary intents (2): codebase_query, general_query
- Average confidence threshold: 0.53

**web_researcher** - ⚡ Low Utilization
- Primary intents (1): web_research
- Average confidence threshold: 0.70

**code_generator** - ⚡ Low Utilization
- Primary intents (1): code_generation
- Average confidence threshold: 0.80

**code_editor** - ⚡ Low Utilization
- Primary intents (1): code_editing
- Average confidence threshold: 0.75

**code_quality_analyzer** - ⚡ Low Utilization
- Primary intents (1): code_analysis
- Average confidence threshold: 0.70

**documentation** - ⚡ Low Utilization
- Primary intents (1): documentation
- Average confidence threshold: 0.80

**tool_executor** - ⚡ Low Utilization
- Primary intents (1): tool_execution
- Average confidence threshold: 0.90

## Detailed Issues by Type

### Threshold Inconsistency (1 issues)
- ℹ️ **information retrieval_group**: Similar intents ['codebase_query', 'general_query'] have inconsistent thresholds: [0.75, 0.3]
  *Recommendation*: Consider aligning thresholds for similar intent types

### Missing Workflows (1 issues)
- ℹ️ **system**: Complex intents without workflows: ['code_editing']
  *Recommendation*: Consider creating workflows for multi-step intents

### Potentially Missing Intents (1 issues)
- ℹ️ **system**: Common intents that might be missing: ['file_management', 'project_setup', 'debugging', 'testing', 'deployment', 'performance_optimization', 'security_audit']
  *Recommendation*: Consider adding these intents if they align with user needs

