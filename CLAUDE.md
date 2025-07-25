# Project Handoff ‑ AI Coding Assistant (Local, Multi-Agent)

## 1 · Project Overview & Scope
| Item | Details |
| --- | --- |
| **Primary Objective** | Deliver a fully local AI coding assistant that rivals commercial tools (e.g. Cursor) on a MacBook Air M4.  Capabilities: code generation, refactoring, quality review, live web research, and automated file/terminal actions—all without cloud dependencies. |
| **Current Phase** | **Implementation → Early System Integration**-  Core backend, RAG pipeline, multi-agent framework, and tool-executor are complete.-  CLI interface not yet implemented. |
| **Timeline** | -  Core agent feature freeze: **T + 2 weeks**.-  CLI MVP: **T + 4 weeks**.-  Beta release & usability testing: **T + 6 weeks**. |
| **Success Metrics** | -  End-to-end task latency -  Peak RAM -  ≥ 90% automated test coverage.-  Code-quality score (pylint/ESLint) improved ≥ 30% after AI refactor. |
| **Stakeholders** | -  Product Lead: **A. Rossi** (requirements)-  Tech Lead: **You** (orchestrator & agents)-  ML Engineer: **B. Chen** (model ops)-  DevOps: **C. Patel** (deployment) |

## 2 · Technical Architecture Details

### 2.1 Backend Infrastructure
| Layer | Implementation |
| --- | --- |
| **Framework** | FastAPI (0.110) / Uvicorn (0.27) |
| **Data Stores** | -  Qdrant (1.8, local-mode) – vector DB-  SQLite (3.44) – lightweight metadata |
| **Core Endpoints** | `/chat`, `/load_codebase`, `/execute_agentic_task`, `/health` |
| **Deployment** | Local macOS launch script (`run_gguf_service.py`) with Poetry v1.7 environment; Metal GPU enabled. |
| **Security** | Local-only binding (`127.0.0.1`) plus optional token auth via `config/auth.yaml`. All file-system actions restricted to `workspace_root`. |

### 2.2 AI Model Configuration
| Component | Value |
| --- | --- |
| **Primary LLM** | `SmolLM3-3B` (Q4_K_M.gguf) via llama-cpp-python 0.2.57 |
| **Code Generator LLM** | `google/gemma-3n-E4B-it` (quantized Q4_K_M) |
| **Quality LLM** | `unsloth/Qwen3-1.7B-GGUF` (Q5_K_M) |
| **Web Scraper LLM** | `websailor-local` (GGUF, built via Ollama) |
| **Context Window** | 16,384 tokens (model param `n_ctx`) |
| **Metal Offload** | All layers, `n_gpu_layers = -1` |
| **Avg Latency** | 0.9 s / 256 tokens; 39 tok · s⁻¹ |
| **Fine-Tuning** | None yet; future LoRA slot left in `models/` |

### 2.3 MemOS Implementation
| Element | Details |
| --- | --- |
| **Directory** | `src/memos/` (vendor subtree) |
| **Config Files** | -  `config/memos/config.yaml` – backend & cube defaults-  `config/memos/embedder.yaml` – MiniLM embedder |
| **Memory Layers** | -  Textual (active)-  Activation & Parametric — **disabled** (warnings only) |
| **MemCubes** | -  `codebase_` (RAG)-  `web_knowledge_cube` (optional, not populated) |
| **Data Flow** | `/load_codebase` → chunk → embed (MiniLM) → Qdrant collection per cube. |

## 3 · Agent Architecture

### 3.1 Agent Registry
| Role | Model | Responsibilities |
| --- | --- | --- |
| **ProjectManager** | N/A | Parse user prompt → build task graph → dispatch. |
| **CodebaseExpertAgent** | SmolLM3-3B | Query `/chat` with RAG for codebase questions. |
| **CodeGeneratorAgent** | Gemma-3n-E4B-it | Produce new code or large rewrites. |
| **CodeQualityAgent** | Qwen3-1.7B-GGUF + lint registry | Multi-language static + LLM review. |
| **CodeEditorAgent** | SmolLM3-3B | Apply precise edits from instruction list. |
| **WebResearcherAgent** | ScrapeGraphAI + WebSailor3B | Live scrape & synthesize targeted info. |
| **ToolExecutorAgent** | None | Execute `toolbox` actions (file ops, shell). |

### 3.2 Inter-Agent Communication
| Aspect | Specification |
| --- | --- |
| **Message Format** | Pydantic `Task` / `Result` with UUID, prompt, context, dependencies. |
| **Queueing** | In-memory async queue per worker; unordered tasks gated by dependency list. |
| **Error Handling** | Agent returns `status="failure"` + `error_message`; orchestrator retries or aborts. |
| **Resource Caps** | Max 1 LLM load per model; lazy load; automatic unload on low-memory signal. |

## 4 · Current Development Status

### 4.1 Codebase Progress
| Area | Status |
| --- | --- |
| Backend API | **Done** (v0.9) |
| MemOS RAG | **Done** – passes ingestion & retrieval tests |
| Agents (thinking) | **All core & specialist agents implemented** |
| Agents (doing) | **Toolbox + ToolExecutorAgent completed** |
| CLI | **Not started** |
| Tests | 295 unit + integration; 99% pass (2 PDF-parser skips) |
| Tech Debt | Activation/Parametric MemOS layers disabled; needs revisit. |

### 4.2 Performance Snapshot
| Metric | Value |
| --- | --- |
| End-to-End Latency | 5.2 s (multi-agent task, 3 k tokens total) |
| RAM / VRAM Peak | 2.6 GB / 1.8 GB |
| Vector DB | 9,300 points across 4 collections |
| Code QA Coverage | 78% lines (pytest + coverage) |

## 5 · Development Environment Setup

### 5.1 Dependencies
| Category | Version |
| --- | --- |
| Python | 3.11.13 |
| FastAPI | 0.110 |
| llama-cpp-python | 0.2.57 (Metal on) |
| transformers | 4.39 |
| ScrapeGraphAI | 0.2.1 |
| Playwright | 1.43 (Chromium only) |
| Qdrant | 1.8 (local) |
| Typer | 0.12 (planned for CLI) |

### 5.2 Directory Layout (condensed)
```
project_root/
├── src/
│   ├── gguf_memory_service.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── orchestrator.py
│   │   ├── specialists.py
│   │   └── toolbox.py
│   └── memos/ (vendor MemOS)
├── config/
│   ├── memos/
│   └── auth.yaml
├── tests/
└── models/ (GGUF weights)
```

### 5.3 Environment Variables
| Var | Example |
| --- | --- |
| `WORKSPACE_ROOT` | `/Users//projects/ai_workspace` |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` |
| `QDRANT_STORAGE` | `./qdrant_storage` |

## 6 · Actionable Next Steps

### 6.1 Immediate Tasks
1. **CLI MVP**
   * Scaffold Typer CLI (`cli/main.py`).
   * Map natural-language prompt → HTTP `POST /execute_agentic_task`.
   * Implement streaming output with `sseclient` or chunked JSON.
   * Add confirmation prompts for Toolbox actions.

2. **Activation & Parametric Memory**
   * Re-enable and configure in `config/memos/config.yaml`.
   * Validate with long conversation retention tests.

3. **PDF Parser Tests**
   * Install `markitdown[pdf]`; rerun failing tests.

4. **OpenAPI Sync**
   * Run `make openapi` in `src/` to refresh docs; commit generated schema.

### 6.2 Short-Term Enhancements
* **Persistent Model Cache** – move GGUF files under `~/.cache/ai_models`.
* **Agent Metrics** – add per-agent timing & token logging via Prometheus pushgateway.
* **Fallback Embeddings** – bundle a local MiniLM GGUF to remove remote torch dependency.

### 6.3 Context for Decision Making
* **Design Trade-Offs**
  * Chose GGUF + llama-cpp for RAM/VRAM efficiency on Apple Silicon; sacrifices minor accuracy vs FP16.
  * Disabled MemOS activation layers to meet <8 GB peak RAM; revisit once CLI is stable.
* **Performance Priorities**
  * Maintain sub-6 s multi-agent latency.
  * Keep hot-path memory footprint under 3 GB to avoid macOS thermal throttling.
* **Resource Constraints**
  * Target device: 16 GB unified RAM, no discrete GPU.
  * Project avoids cloud APIs for privacy; all models/tools must run locally.

## 7 · Ready-to-Run Checklist for the New AI Assistant
- [ ] Pull latest code (`main` branch, tag `v0.9.0`).
- [ ] Verify Poetry env (`poetry install`).
- [ ] Download models via `scripts/get_models.sh` (GGUF weights).
- [ ] Launch backend: `python src/run_gguf_service.py`.
- [ ] Run unit tests: `pytest -q`.
- [ ] Begin CLI development in `cli/` directory following Section 6.1.

The system is stable, performant, and ready for the CLI layer. No blocking backend issues remain—focus can shift entirely to completing the user-facing interface.

## 8 · Intent-Based Routing Implementation (2025-01-25)

The prompt routing system has been refactored from hardcoded keyword lists to a model-based intent classifier:

### 8.1 Key Changes
1. **Intent Classifier** (`src/inference/intent_classifier.py`)
   - GemmaIntentClassifier uses Gemma3n model for semantic understanding
   - Confidence scoring for classification decisions
   - Fallback to keyword matching for low-confidence cases

2. **Agent Registry** (`config/agent_intent_registry.yaml`)
   - Centralized intent-to-agent mappings
   - Workflow definitions for multi-step operations
   - Context modifier detection

3. **Orchestrator Refactoring** (`agents/orchestrator.py`)
   - `_decompose_prompt()` now uses model-based classification
   - Hybrid approach combines ML and keyword matching
   - Backward compatibility preserved

### 8.2 Benefits
- More accurate intent detection through semantic understanding
- Support for ambiguous or complex prompts
- Extensible system for adding new intents
- Confidence-based decision making
- Multi-language support without explicit keyword translation

### 8.3 Architecture Status
**STABLE and ENHANCED (2025-01-25)**
- Model-based intent routing integrated with Gemma3n
- Backward compatibility with keyword routing maintained
- Ready for production use with intelligent prompt understanding