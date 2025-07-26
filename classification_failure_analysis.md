# Intent Classification Failure Analysis Report

## Overview
- **Total Classifications**: 8
- **Failures**: 3
- **Successes**: 5
- **Failure Rate**: 37.5%

## Failure Type Breakdown

### Web Research Confusion (1 cases)

**Prompt**: Research the history of Python decorators and insert a summary at the top of calculator_comprehensive.py
- Expected: `web_research` → `WebResearchAgent`
- Actual: `code_editing` → `CodeEditorAgent`
- Confidence: 0.90
- Time: 0.64s

### Query Vs Analysis Confusion (1 cases)

**Prompt**: Explain how the calculator class works and its design patterns
- Expected: `codebase_query` → `CodebaseExpertAgent`
- Actual: `code_analysis` → `CodeQualityAgent`
- Confidence: 0.90
- Time: 0.71s

### Execution Vs Analysis Confusion (1 cases)

**Prompt**: Run unit tests on calculator_comprehensive.py and summarize the results
- Expected: `tool_execution` → `ToolExecutorAgent`
- Actual: `code_analysis` → `CodeQualityAgent`
- Confidence: 0.90
- Time: 0.61s

## Confidence Analysis
- **Failed Classifications Average Confidence**: 0.90
- **Successful Classifications Average Confidence**: 0.90
- **Failed Confidence Range**: 0.90 - 0.90
- **Success Confidence Range**: 0.90 - 0.90

## Timing Analysis
- **Failed Classifications Average Time**: 0.65s
- **Successful Classifications Average Time**: 2.26s

