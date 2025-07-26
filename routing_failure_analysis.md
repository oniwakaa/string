# Routing Failure Analysis Report

## Analysis Overview
- **Total Routing Failures**: 5
- **High Confidence Errors**: 5
- **Most Problematic Pattern**: web_research → documentation

## Individual Failure Analysis

### wr_001 - Edge_Case Case
**Prompt**: "Get the latest Python documentation from the official website"
**Expected**: web_research → **Got**: documentation (confidence: 0.90)
**Issue**: Prompt contains 'documentation' keyword, causing confusion with documentation intent
**Fix**: Strengthen web_research prompt template to prioritize external source indicators (website, fetch, get from) over content type

### wr_002 - Edge_Case Case
**Prompt**: "Fetch API information from external sources and libraries"
**Expected**: web_research → **Got**: documentation (confidence: 0.90)
**Issue**: External source indicators not strong enough in prompt template
**Fix**: Add explicit 'external source' vs 'internal doc creation' distinction in prompt template

### te_001 - Edge_Case Case
**Prompt**: "Execute all unit tests and report any failures"
**Expected**: tool_execution → **Got**: code_analysis (confidence: 0.90)
**Issue**: 'Report' keyword associated with analysis rather than execution output
**Fix**: Clarify in tool_execution template that execution includes reporting results, not just analysis

### te_003 - Edge_Case Case
**Prompt**: "Test this function with various input values"
**Expected**: tool_execution → **Got**: code_analysis (confidence: 0.90)
**Issue**: 'Test function' phrase interpreted as code analysis rather than test execution
**Fix**: Add specific execution keywords (run, execute, perform) to tool_execution template to distinguish from analysis

### amb_004 - Ambiguous Case
**Prompt**: "Find and fix performance issues in the code"
**Expected**: code_editing → **Got**: code_analysis (confidence: 0.90)
**Issue**: 'Find and fix' interpreted as analysis first, missing the editing action
**Fix**: Update code_editing template to emphasize that 'fix' implies modification action, not just identification

## Common Confusion Patterns

### web_research → documentation (2 cases)
- **Average Confidence**: 0.90
- **Common Keywords**: from
- **Test Cases**: wr_001, wr_002
- **Root Cause**: Content type keywords (documentation, API) override source location keywords (website, external)

### tool_execution → code_analysis (2 cases)
- **Average Confidence**: 0.90
- **Common Keywords**: 
- **Test Cases**: te_001, te_003
- **Root Cause**: Analysis verbs (test, report) interpreted as passive observation rather than active execution

### code_editing → code_analysis (1 cases)
- **Average Confidence**: 0.90
- **Common Keywords**: 
- **Test Cases**: amb_004
- **Root Cause**: Multi-step actions (find and fix) prioritize discovery phase over modification phase

## Recommended Mapping Fixes

### Fix 1: Update web_research Template
**Issue**: Confused with documentation intent when content type is mentioned
**Current**: Get external info (NOT code modification)
**Improved**: Get info from external websites/sources (NOT create internal docs)
**Add Examples**:
- "fetch latest docs from official website"
- "scrape API info from external sources"
- "get documentation from web"
**Add Negative Examples**:
- NOT: create documentation
- NOT: document existing code
- NOT: write API docs

### Fix 2: Update tool_execution Template
**Issue**: Confused with code_analysis when reporting or testing is mentioned
**Current**: Run/execute/test (NOT inspect/analyze)
**Improved**: Run/execute/perform actions that produce output (NOT passive review)
**Add Examples**:
- "execute tests and show results"
- "run function with test inputs"
- "perform unit tests"
**Add Negative Examples**:
- NOT: analyze test results
- NOT: review function logic
- NOT: inspect code quality

### Fix 3: Update code_editing Template
**Issue**: Multi-step phrases like 'find and fix' prioritize discovery over modification
**Current**: Modify existing code (NOT create new)
**Improved**: Change/modify/fix code files (NOT just identify issues)
**Add Examples**:
- "find and fix the bug"
- "locate and resolve performance issues"
- "identify and correct the error"
**Add Negative Examples**:
- NOT: analyze for issues
- NOT: review code quality
- NOT: inspect without changing

### Fix 4: Confidence Validation Rules
**Issue**: 5 failures had high confidence (>0.85), indicating systematic misclassification
**Affected Intents**: web_research, code_editing, tool_execution
**Recommendation**: Consider adding validation step for high-confidence classifications that fall into common confusion patterns
**Validation Rules**:
- If web_research classified but contains 'documentation', verify external source indicators
- If code_analysis classified but contains action verbs (run, execute, fix), verify intended outcome
- If classification confidence > 0.9 but result seems wrong, trigger clarification

## Implementation Priority

1. **HIGH**: Update prompt templates for web_research, tool_execution, and code_editing
2. **MEDIUM**: Add confidence validation rules for high-confidence misclassifications
3. **LOW**: Monitor routing accuracy after template updates

