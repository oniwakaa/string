### Project Overview & Scope
- Primary Objective
  - Package-first backend + MemOS-enabled service that starts reliably via pipx (Python 3.11), reads models/config from STRING_HOME, and returns correct /health with MemOS initialized.
- Current Phase
  - Phase 1: Stabilize health reporting, align model keys, and enforce explicit initialization order.
- Timeline
  - Current work date: 2025-08-13. Additional stabilization needed next session.
- Success Metrics
  - /health returns initialized=true and no AttributeError.
  - /load_codebase indexes files; /chat shows memory_enhanced=true with memories_count>0.
  - No CWD coupling; all runtime assets under STRING_HOME.
- Stakeholders (name → role)
  - @carlo → Operator
  - @backend-eng → Backend & packaging
  - @ml-eng → Models & HF downloads
  - @memos-eng → MemOS integration

### Technical Architecture
#### Backend Infrastructure
- Framework & stack
  - FastAPI + Uvicorn service, llama-cpp-python for GGUF, MemOS adapters.
- Database schema location
  - Qdrant persisted under ./~/.string/storage/qdrant_storage (empty at time of test).
- Key API endpoints
  - GET /health, GET /status, POST /load_codebase, POST /execute_agentic_task, POST /chat.
- Deployment & hosting details
  - Installed via pipx; entrypoints: string-cli, run_gguf_service. Runtime home: STRING_HOME=./~/.string.
- Security & auth summary
  - Not in scope here (TBD).

#### AI Model Configuration
- LLaMA version & size
  - Manifest entries present: SmolLM3-3B-Q4_K_M (~1.78 GB), gemma-3n-E4B-it-Q5_K_S (~4.61 GB), Qwen3-1.7B-Q5_K_M (~1.17 GB), plus embeddings.
- Quantization / fine-tuning status
  - Using provided quantized GGUFs (as above). No fine-tune data observed.
- Hardware utilization (GPU/NPU)
  - macOS arm64 with Metal-enabled llama-cpp-python (Metal may be available).
- Inference perf metrics (token/s, latency)
  - TBD.

#### MemOS Implementation
- Directory layout
  - MemOS modules under ./string_ai_coding_assistant/memos/... with configs and memory layers.
- Config file paths
  - Models manifest at ./~/.string/config/models.json; models under ./~/.string/models.
- Memory layers (textual / activation / parametric)
  - Present in code; inactive at runtime: logs show “No MemCube available” and memos.status=error.
- Data storage & retrieval patterns
  - Intended Qdrant usage at ./~/.string/storage/qdrant_storage. Currently empty and not receiving indexed points.

### Agent Architecture
- Agent Types & Responsibilities
  - Code Generation Agent: code generation (model selection TBD).
  - Context Management Agent: codebase RAG/memory (currently falling back).
  - Quality Assurance Agent: code analysis (TBD).
  - Orchestration Layer: ProjectManager routes tasks; invokes /execute_agentic_task.
- Inter-Agent Communication
  - Message schema: JSON (prompt, user_id, project_id).
  - Priority queue rules: TBD.
  - Error-handling flow
    - Fallback to rag_system when MemOS unavailable.
  - Resource allocation logic
    - ModelManager managed; MemOS intended to create per-project cubes (not happening yet).

### Current Development Status
- Code Implementation Progress (completed modules, WIP)
  - Packaging fixes for model path and health guards completed; MemOS initialization still failing.
- Testing & QA (coverage %, failing cases)
  - Manual end-to-end black-box tests only; no coverage reported. /health returns 200 but initialized=false.
- Known Issues / Technical Debt
  - Health/status payload contains stale error "'ModelManager' object has no attribute 'get_memory_stats'" despite guards.
  - Model key alias requests (e.g., "SmolLM3-3B") mismatch manifest canonical keys (e.g., "SmolLM3-3B-Q4_K_M") caused earlier init failures.
  - MemOS cube not created; /load_codebase reports “No MemCube available”; memory_enhanced=false from CLI.

### Performance Metrics
- Latency (p95)
  - TBD.
- Resource utilization (CPU/GPU/RAM)
  - TBD.
- Throughput (req/min)
  - TBD.
- Context retention accuracy
  - Memory not engaged; TBD after fix.
- User acceptance (if tracked)
  - TBD.

### Development Environment
- Dependencies & versions
  - Python 3.11 via pipx; llama-cpp-python 0.3.15; FastAPI 0.116.1; httpx 0.28.1.
- Hardware requirements
  - macOS arm64; Metal build for llama-cpp-python supported.
- IDE / tooling configs
  - Cursor. Pipx-managed venv at ./~/.local/pipx/venvs/string-ai-coding-assistant.
- Essential env vars (./.env.example path)
  - STRING_HOME (defaults to ./~/.string). SERVICE_HOST/SERVICE_PORT used for CLI health checks.

### File Structure Snapshot
```
tree -L 2
```
- Note: Fresh snapshot recommended after packaging edits. Current session used targeted file reads.

### Session Change Log (13-Aug-2025)
| File | Change | Reason | Status |
|------|--------|--------|--------|
| ./cli/main.py | Removed `color_system` arg from `Console.print(...)`. | Fix CLI crash: “TypeError: Console.print() got an unexpected keyword argument 'color_system'”. | Done |
| ./models/manager.py | Added `_normalize_model_key` mapping aliases to manifest keys; added `get_memory_stats()` shim. | Align requested model names with manifest; satisfy health/status optional stats. | Done |
| ./src/core/resource_manager.py | Fallback to “SmolLM3” when “SmolLM3-3B” not present; fallback to “Qwen3” when embedding key missing. | Prevent model key mismatches causing init failures. | Done |
| ./string_ai_coding_assistant/backend/gguf_memory_service.py | Guarded model manager stats in `get_service_status`; added `service.error` propagation; added `model.info.model_name`. | Remove invalid hard dependency on missing methods; enrich health payload. | Done |
| ./gguf_memory_service.py (legacy) | Guarded `model_manager.get_memory_stats()`; added safe fallback. | Prevent stale AttributeError if legacy module is imported. | Done |

### Next Steps & Owner
- @backend-eng: Add a transient debug field in `get_service_status()` to include `__file__` to confirm which module path backs the running service. Remove after verification.
- @backend-eng: Ensure only packaged backend entry is used by CLI (confirm `string_ai_coding_assistant.backend.service:main` is the target; no legacy `./gguf_memory_service.py` import).
- @backend-eng: In `MemOSService.startup`, set `_is_initialized=True` only after successful LLM + MemOS init; set `_last_error` on any failure and surface in health; verify model key used is canonical (e.g., "SmolLM3-3B-Q4_K_M").
- @memos-eng: Wire MemOS cube creation via `ProjectMemoryManager` so `/load_codebase` indexes into Qdrant; assert files_loaded>0 and no "No MemCube available".
- @ml-eng: Confirm ./~/.string/config/models.json contains canonical keys used by code; verify real *.gguf present under ./~/.string/models; keep `local_dir_use_symlinks=False` semantics if re-downloading.
- @carlo: Reinstall via pipx using Python 3.11; restart; run black-box checks listed below; attach logs.

Latest steps summary (13-Aug-2025)
- Enforced Python 3.11 pipx install and reinstall; `which -a string-cli` points to ./~/.local/bin/string-cli; `string-cli --version` OK.
- Health guards added; installed pipx `model_manager` reports `has get_memory_stats: True`.
- /health still shows error string: "'ModelManager' object has no attribute 'get_memory_stats'".
- /status shows same error; `service.initialized=false`; `model.loaded=false`; `memos.status=error`.

Blocking errors (verbatim, sources)
- Health/status payload:
  - "error": "'ModelManager' object has no attribute 'get_memory_stats'" (GET /health, GET /status).
- Load codebase:
  - “⚠️ [Skip] No MemCube available …” and response shows `files_loaded: 0`, `files_failed: 270`, many `"reason":"No MemCube available"` (./string_ai_coding_assistant/backend/gguf_memory_service.py logs).
- Earlier startup (pre-fix) model mismatch:
  - “Model 'SmolLM3-3B' not found in configuration. Available: SmolLM3-3B-Q4_K_M, SmolLM3, …” (./string_ai_coding_assistant/backend/project_memory_manager.py via ResourceManager).

Black-box verification checklist (post-fix)
- Confirm running module path for get_service_status (temporary field).
- Restart and check:
  - `string-cli stop-backend || true`
  - `string-cli start-backend`
  - `curl -s http://127.0.0.1:8000/status | jq`
  - Expected: no `'get_memory_stats'` error; `service.initialized` true or last_error with actionable cause.
- Load + chat:
  - `string-cli load ./` (within a small repo)
  - `string-cli --skip-checks "What is this project? Main files?"`
  - Expected: `memory_enhanced: true`, `memories_count > 0` once MemOS cube exists and Qdrant receives points.

Environment & models status (facts from session)
- STRING_HOME: ./~/.string
- Models present; real *.gguf sizes (no symlinks).
- Qdrant and memory_cubes directories exist but are empty; no indexed data.

Why the current error persists
- The installed code contains guards; pipx `model_manager` exposes `get_memory_stats`.
- Health/status still show the old error string, strongly indicating:
  - The running service sets `service.error` from a different codepath/module (likely legacy import) or
  - A stale `_last_error` value is being returned without re-evaluation post-guard.

Owner actions to unblock
- @backend-eng: Add `status['service']['module'] = __file__` temporarily in `get_service_status` to prove which module is responding; remove after.
- @backend-eng: Ensure CLI starts packaged entry `string_ai_coding_assistant.backend.service:main`; remove any path-based probing; confirm with `pipx list` and which `run_gguf_service`.
- @memos-eng: Implement MemOS cube creation in startup; verify Qdrant collections under ./~/.string/storage/qdrant_storage; re-run `/load_codebase`.

This document reflects only verified facts and outputs from this session as of 2025-08-13.