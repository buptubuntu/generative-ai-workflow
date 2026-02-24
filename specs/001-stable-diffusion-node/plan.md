# Implementation Plan: Stable Diffusion Node

**Branch**: `001-stable-diffusion-node` | **Date**: 2026-02-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-stable-diffusion-node/spec.md`

## Summary

Add a `StableDiffusionNode` class that extends the existing `WorkflowNode` ABC, enabling local text-to-image generation within generative AI workflows. The node accepts prompt templates with `{variable}` substitution (consistent with `LLMNode`), runs inference entirely on-device using a shared model singleton per model identifier, saves output as UUID-named PNG files, and emits structured logs and metrics at full parity with `LLMNode`. No changes to the workflow engine or runner are required.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Existing: `pydantic>=2.0`, `structlog>=24.0` (already in project)
- New: `diffusers>=0.30.0`, `torch>=2.1.0`, `Pillow>=10.0.0`, `accelerate>=0.26.0`, `transformers>=4.40.0`

**Storage**: Local filesystem — UUID-named PNG files written to a configurable output directory (default: `./generated_images/`); model weights pre-downloaded by user
**Testing**: `pytest`, `pytest-asyncio` (already in project); mock `diffusers` pipeline in unit tests
**Target Platform**: Linux/macOS; NVIDIA CUDA GPU (primary), Apple Silicon MPS, or CPU fallback
**Project Type**: Single Python library (framework extension — adds to `src/generative_ai_workflow/`)
**Performance Goals**: Image generation ≤60s on GPU for 512×512 at 20 inference steps (SC-002)
**Constraints**: No external network calls during inference (FR-006); one image per node execution; model weights must be pre-downloaded; output filename guaranteed unique (UUID)
**Scale/Scope**: Single model singleton per model identifier within a process; single image per execution; thread safety via per-singleton inference lock

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` (current version: v1.5.1).

### ✅ Principle I: Interface-First Design
- [x] `StableDiffusionNode` extends `WorkflowNode` ABC — plugs into existing interface
- [x] `ModelRegistry` exposes a module-level interface for model lifecycle; pipeline hidden behind it
- [x] `GeneratedImage` is a Pydantic data contract between node and downstream consumers
- [x] No breaking interface changes — new class only; existing engine/runner unchanged

### ✅ Principle II: Documented Public Interfaces
- [x] `StableDiffusionNode`, `GeneratedImage`, `ModelConfig` will have full docstrings (purpose, params, returns, exceptions, examples) matching existing codebase style
- [x] Type annotations throughout, consistent with `node.py` and `providers/base.py`
- [x] At least one usage example in `StableDiffusionNode` class docstring
- [x] Threading behaviour of `ModelRegistry` documented (serialized inference, lock scope)

### ✅ Principle III: SOLID Principles
- [x] Single Responsibility: `StableDiffusionNode` — generation orchestration; `ModelRegistry` — model lifecycle; `GeneratedImage` — output data contract
- [x] Open/Closed: Extends `WorkflowNode` without modifying it
- [x] Liskov Substitution: `StableDiffusionNode` is a drop-in `WorkflowNode` — passes all engine contracts
- [x] Dependency Inversion: Node accesses models via `ModelRegistry` interface, not concrete pipeline directly

> **Justified violation**: `ModelRegistry` uses a module-level singleton dict. Pure DI would require passing the registry through the engine (modifying engine internals), which violates FR-001 ("no modifications to the engine"). This follows the same pattern as `PluginRegistry` already in the framework. See Complexity Tracking.

### ✅ Principle IV: Observability (AI-Specific)
**Traditional Observability:**
- [x] Structured logging via existing `get_logger()` / structlog — node start, completion, failure events
- [x] Duration metric emitted per execution (`generation_duration_ms`)
- [x] Node name included in all log events for correlation

**AI-Specific Observability (with justified deviation):**
- [x] **Image generation metrics** (substitutes for token tracking — N/A for diffusion models):
  - `inference_steps` (analogous to `total_tokens` — primary cost driver)
  - `resolution` (`{width}x{height}`)
  - `guidance_scale`
  - `device_type` (cuda/mps/cpu — affects throughput)
  - `generation_duration_ms` (latency)
- [x] **Node interaction logging**: model identifier, generation parameters, success/failure status, duration
- [x] **Workflow state tracking**: start/complete/failed events consistent with `LLMNode` pattern

> **Justified deviation from token tracking**: Stable Diffusion does not use tokens. Image generation cost is driven by `inference_steps × resolution × model_size`, not token count. Equivalent metrics are defined above and emitted in the same structured format. See Complexity Tracking.

### ✅ Principle V: Configurable But Convention First
- [x] All parameters have documented defaults: `width=512`, `height=512`, `num_inference_steps=20`, `guidance_scale=7.5`, `output_dir="./generated_images"`
- [x] Construction-time validation with clear `ValueError` messages (FR-011)
- [x] No configuration explosion — only parameters that materially affect output are exposed

### ✅ Principle VI: Unit Tests (AI-Specific)
- [x] **Pure logic** (prompt template rendering, parameter validation, file path construction): deterministic tests, exact assertions
- [x] **Generation integration code**: `StableDiffusionPipeline` mocked/patched in all unit tests — no real model calls
- [x] **Mock model pipeline** returns a predictable PIL Image (1×1 white PNG) so output handling can be verified without a real model
- [x] Test cases per SC-006: successful generation, non-critical failure, missing template variable, invalid construction params, empty prompt after substitution

### ✅ Principle VII: Integration Tests (AI-Specific)
- [x] **Tiered execution strategy** (hardware-gated, not cost-gated — local model is $0):
  - Commit hooks / CI: unit tests only (mocked pipeline, no model loaded)
  - Integration tests: skip automatically if no GPU and no model weights present (pytest marker + skip condition)
  - On-demand: full integration test with real model on developer machine with GPU
- [x] Test data contains no PII (synthetic prompts: "a red apple on a table")
- [x] No real API calls; model weights are local

### ✅ Principle VIII: Security (AI-Specific)
- [x] **No prompt injection risk**: no LLM system prompt; image generation is not susceptible to instruction injection
- [x] **No PII concern for inference**: prompts are text descriptions for image generation; no user data sent to external services (FR-006)
- [x] **No API keys required**: local inference — no credential management needed
- [x] **UUID filenames**: prevent predictable path collisions; no path traversal in output filenames
- [x] **Output directory validation**: validate `output_dir` is a relative or absolute path; creation is safe (standard `os.makedirs`)
- [x] **No DoW risk**: local computation; no cost-per-token; hardware resource limits are OS/driver-managed

### ✅ Principle IX: Use LTS Dependencies
- [x] Python 3.11+ (stable LTS)
- [x] `torch>=2.1.0`, `diffusers>=0.30.0`, `Pillow>=10.0.0`, `transformers>=4.40.0`, `accelerate>=0.26.0` — all stable, mature releases
- [x] Versions pinned in `pyproject.toml` as optional extras (`[stable-diffusion]`) to avoid imposing heavy GPU dependencies on all users

### ✅ Principle X: Backward Compatibility
- [x] Adding a new class `StableDiffusionNode` — no existing API changes
- [x] New optional dependency group `[stable-diffusion]` in `pyproject.toml` — existing installs unaffected
- [x] `ModelRegistry` is a new internal module — no public API removals or renames
- [x] `CHANGELOG.md` to be updated (minor version addition)

### ✅ Principle XI: Extensibility & Plugin Architecture
- [x] `StableDiffusionNode` can be registered via `PluginRegistry` (FR-012) — follows same pattern as `LLMProvider`
- [x] `ModelRegistry` is an internal extension point: alternative backends can be registered without modifying `StableDiffusionNode`
- [x] Node follows `WorkflowNode` contract — any middleware hooks applied to all nodes apply automatically

### ✅ Principle XII: Branch-Per-Task Development Workflow
- [x] Currently on `001-stable-diffusion-node` branch
- [x] All spec/design artifacts (spec.md, plan.md, data-model.md, contracts/, research.md) will be committed and merged to main before implementation begins
- [x] Each implementation task will get its own feature branch per tasks.md convention

## Project Structure

### Documentation (this feature)

```text
specs/001-stable-diffusion-node/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   ├── stable_diffusion_node.py
│   └── model_registry.py
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/generative_ai_workflow/
├── node.py                          # ADD: StableDiffusionNode class
├── sd_model_registry.py             # NEW: ModelRegistry singleton + thread-safe loader
├── providers/
│   └── (unchanged)
└── observability/
    └── (unchanged — reuse get_logger, NodeTimer)

tests/
├── unit/
│   └── test_stable_diffusion_node.py  # NEW: unit tests (mocked pipeline)
└── integration/
    └── test_sd_integration.py          # NEW: integration tests (hardware-gated)
```

**Structure Decision**: Single project layout. `StableDiffusionNode` added to existing `node.py` (same file as `LLMNode` and `TransformNode` — consistent with framework pattern). `ModelRegistry` gets its own module `sd_model_registry.py` (separate concern — model lifecycle management).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| `ModelRegistry` uses module-level singleton dict (violates pure DI from Principle III) | FR-013 requires shared model singleton per identifier; FR-001 forbids engine changes — only way to share state without engine modification | Pure DI would require passing registry through `NodeContext` or engine constructor, requiring engine changes that violate FR-001. Module-level singleton is the same pattern already used by `PluginRegistry` in this codebase. |
| No token tracking (deviates from Principle IV AI-Specific) | Diffusion models do not use tokens — concept does not apply | Token tracking cannot be adapted to image generation without misrepresenting the metric. Equivalent generation-specific metrics (`inference_steps`, `resolution`, `guidance_scale`, `device_type`, `duration_ms`) are emitted instead. |
