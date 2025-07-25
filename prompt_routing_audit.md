# Prompt Routing Audit Report

## Overview
This report documents all prompt handling mechanisms in the current implementation of the multi-agent AI coding assistant. The routing logic is primarily concentrated in the `ProjectManager._decompose_prompt()` method in `agents/orchestrator.py`.

## Current Routing Mechanism
The system uses a **keyword-based rule engine** to decompose user prompts into execution plans. The routing logic follows a hierarchical pattern matching approach with hardcoded keyword lists.

## Routing Logic Analysis

### 1. Web Research Routing (Lines 900-922)
**Keywords:** `'scrape', 'web', 'website', 'url', 'fetch', 'extract from', 'get from', 'ricerca web', 'scraping', 'website content', 'page content', 'estrai da', 'ottieni da'`

**Agent:** `web_researcher`

**Secondary Actions:** If combined with `'analizza', 'genera', 'crea', 'modifica', 'analyze', 'generate', 'create', 'modify'`, adds `code_generator` as step 2.

### 2. Code Editing Routing (Lines 923-950)
**Primary Keywords:** `'modifica', 'edit', 'cambia', 'change', 'fix', 'correggi', 'aggiorna', 'update', 'refactor', 'rifattorizza', 'migliora', 'improve', 'applica', 'apply', 'bug'`

**Context Keywords:** `'file', 'function', 'class', 'method', 'nel progetto', 'in the project', 'the '`

**Workflow:**
- If context keywords present: `codebase_expert` → `code_editor`
- Otherwise: Direct `code_editor`

### 3. Codebase Knowledge Queries (Lines 952-973)
**Keywords:** `'trova', 'cerca', 'dove', 'come funziona', 'che cosa fa', 'explain', 'find', 'search', 'where', 'how does', 'what does', 'show me', 'mostrami', 'function', 'funzione', 'class', 'classe', 'method', 'metodo', 'file', 'directory', 'cartella'`

**Agent:** `codebase_expert`

**Secondary Actions:** If combined with `'modifica', 'cambia', 'aggiorna', 'migliora', 'modify', 'change', 'improve'`, adds `code_generator` as step 2.

### 4. Code Generation Routing (Lines 974-1018)
**Primary Keywords:** `'genera', 'crea', 'scrivi', 'implementa', 'develop', 'build', 'create'`

**Context Keywords:** `'basandoti', 'usando', 'integra', 'estendi', 'based on', 'using', 'integrate', 'extend', 'similar to', 'simile a', 'like', 'come'`

**Workflow:**
- If context keywords present: `codebase_expert` → `code_generator`
- Otherwise: Direct `code_generator`

**Post-processing:**
- If contains `'analizza', 'verifica', 'controlla', 'review'`: adds `code_quality_analyzer`
- If contains `'documenta', 'documentation', 'spiega', 'descrivi'`: adds `documentation`

### 5. Code Analysis Routing (Lines 1019-1054)
**Keywords:** `'analizza', 'verifica', 'controlla', 'review', 'audit'`

**Context Keywords:** `'file', 'function', 'class', 'method', 'nel progetto', 'in the project'`

**Workflow:**
- If context keywords present: `codebase_expert` → `code_quality_analyzer`
- Otherwise: Direct `code_quality_analyzer`

**Follow-up Actions:** If contains `'fix', 'correggi', 'applica', 'apply', 'resolve', 'risolvi', 'migliora', 'improve'`, adds `code_editor` with dependencies on both previous steps.

### 6. Documentation Routing (Lines 1055-1079)
**Keywords:** `'documenta', 'documentation', 'spiega', 'descrivi'`

**Context Keywords:** `'function', 'class', 'method', 'api', 'nel progetto', 'in the project'`

**Workflow:**
- If context keywords present: `codebase_expert` → `documentation`
- Otherwise: Direct `documentation`

### 7. Default Fallback (Lines 1081-1094)
If no specific patterns match, the system defaults to:
1. `codebase_expert` - Search for relevant context
2. `code_generator` - Generate based on prompt and context

## Edge Cases and Limitations

### 1. Language Mixing
- System supports both Italian and English keywords
- Mixed language prompts may not be properly captured

### 2. Ambiguous Prompts
- Multiple matching patterns can lead to unexpected routing
- No confidence scoring or conflict resolution

### 3. Context Loss
- Keywords must match exactly (case-insensitive)
- Synonyms or variations not captured
- Semantic understanding is absent

### 4. Tool Execution Integration
The system also includes a `tool_executor` agent, but routing to it is handled differently:
- Not directly invoked via keyword matching
- Triggered by `next_action` metadata from other agents
- Found in `_handle_next_action()` method (lines 1502-1575)

### 5. Prompt Enhancement
Additional prompt modification occurs in:
- `CodeGeneratorAgent._format_gemma_prompt()` (lines 112-166)
- `ProjectManager._enhance_agent_prompt_with_context()` (lines 1357-1420)
- `ProjectManager._prepare_code_editor_context()` (lines 1421-1500)

## Hardcoded Lists Summary

| Category | Keyword Count | Languages |
|----------|---------------|-----------|
| Web Research | 13 | English, Italian |
| Code Editing | 14 | English, Italian |
| Codebase Query | 17 | English, Italian |
| Code Generation | 7 | English, Italian |
| Context Modifiers | 12 | English, Italian |
| Analysis | 5 | English, Italian |
| Documentation | 4 | English, Italian |
| Fix/Apply | 8 | English, Italian |

**Total Unique Keywords:** ~84 keywords across all categories

## Routing Decision Tree
```
User Prompt
    ├── Contains Web Keywords? → web_researcher
    │   └── Contains Action Keywords? → + code_generator
    ├── Contains Edit Keywords? → 
    │   ├── Has Context? → codebase_expert → code_editor
    │   └── No Context → code_editor
    ├── Contains Search Keywords? → codebase_expert
    │   └── Contains Modify? → + code_generator
    ├── Contains Generate Keywords? →
    │   ├── Has Context? → codebase_expert → code_generator
    │   └── No Context → code_generator
    │   └── Post-process:
    │       ├── Has Analysis? → + code_quality_analyzer
    │       └── Has Documentation? → + documentation
    ├── Contains Analysis Keywords? →
    │   ├── Has Context? → codebase_expert → code_quality_analyzer
    │   └── No Context → code_quality_analyzer
    │   └── Has Fix Keywords? → + code_editor
    ├── Contains Documentation Keywords? →
    │   ├── Has Context? → codebase_expert → documentation
    │   └── No Context → documentation
    └── Default → codebase_expert → code_generator
```

## Recommendations for Model-Based Routing
1. Replace keyword lists with intent classification
2. Add confidence scoring for ambiguous cases
3. Support semantic understanding beyond exact matches
4. Enable multi-intent detection
5. Implement context-aware routing based on conversation history
6. Add support for custom intents and agent mappings