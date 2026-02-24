# Tasks: Stable Diffusion Node

**Input**: Design documents from `/specs/001-stable-diffusion-node/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Feature Branch**: `001-stable-diffusion-node`
**Generated**: 2026-02-23

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Included — spec.md SC-006 explicitly requires unit tests covering successful generation, failed generation (non-critical), missing template variable, invalid construction parameters, and empty-prompt edge case.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add optional dependency extras so the core framework install remains lightweight (research.md Decision 6).

- [x] T001 Add `[stable-diffusion]` optional extras group to `pyproject.toml` with pinned ranges: `diffusers>=0.31.0,<1.0`, `transformers>=4.41.2,<5.0`, `accelerate>=0.31.0`, `safetensors>=0.3.1`, `Pillow>=9.0`, `torch>=2.0.0`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure shared by ALL user stories — ModelRegistry singleton, data models, and device detection. Every user story phase blocks on this completing first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Implement `_detect_device_and_dtype()` helper in `src/generative_ai_workflow/sd_model_registry.py` — returns `(device: str, dtype: torch.dtype)` with priority CUDA→float16, MPS→float32, CPU→float32 (research.md Decision 2)
- [x] T003 [P] Implement `_PipelineHolder` class in `src/generative_ai_workflow/sd_model_registry.py` — wraps a loaded `StableDiffusionPipeline`, stores `device: str` property and `_gpu_lock: threading.Lock`; `.run(prompt, width, height, num_inference_steps, guidance_scale) -> bytes` clones scheduler via `from_pipe()` then acquires `_gpu_lock` before inference, returns raw PNG bytes (research.md Decision 3, contracts/model_registry.py PipelineHolder)
- [x] T004 Implement `ModelRegistry` class in `src/generative_ai_workflow/sd_model_registry.py` — module-level `_instances: dict[str, _PipelineHolder]` and `_class_lock: threading.Lock`; classmethod `get(model_id: str) -> _PipelineHolder` uses double-checked locking to load once via `StableDiffusionPipeline.from_pretrained()`; classmethods `clear() -> None` and `loaded_model_ids() -> list[str]` (data-model.md Entity 3, contracts/model_registry.py ModelRegistryInterface) — depends on T002, T003
- [x] T005 [P] Implement `GenerationConfig` Pydantic model in `src/generative_ai_workflow/sd_model_registry.py` — fields: `model_id: str = Field(min_length=1)`, `width: int = Field(default=512, ge=8, multiple_of=8)`, `height: int = Field(default=512, ge=8, multiple_of=8)`, `num_inference_steps: int = Field(default=20, ge=1)`, `guidance_scale: float = Field(default=7.5, ge=0.0)`, `output_dir: str = Field(default="./generated_images", min_length=1)` (data-model.md Entity 1)
- [x] T006 [P] Implement `GeneratedImage` Pydantic model in `src/generative_ai_workflow/node.py` alongside `LLMNode` — fields: `file_path: str`, `image_bytes: bytes`, `width: int = Field(ge=1)`, `height: int = Field(ge=1)`, `generation_duration_ms: float = Field(ge=0.0)`, `model_id: str`, `inference_steps: int = Field(ge=1)`, `guidance_scale: float = Field(ge=0.0)`, `device_type: str`; `model_config = {"arbitrary_types_allowed": True}` (contracts/stable_diffusion_node.py GeneratedImage)

**Checkpoint**: Foundation ready — `ModelRegistry`, `GenerationConfig`, and `GeneratedImage` are defined. User story implementation can now begin.

---

## Phase 3: User Story 1 — Generate Image from Text Prompt (Priority: P1) 🎯 MVP

**Goal**: A workflow author adds a `StableDiffusionNode` to an existing workflow. When executed, the node substitutes prompt variables from workflow context, runs local inference via the shared `ModelRegistry` singleton, saves a UUID-named PNG to `output_dir`, and returns a `NodeResult` with `status=COMPLETED` containing `generated_image`, `image_file_path`, and `image_bytes`.

**Independent Test**: Instantiate `StableDiffusionNode(name="test", prompt="a red apple", model_id="<local-path>")`, call `execute_async(context)`, verify `result.status == NodeResultStatus.COMPLETED`, `result.output["image_file_path"]` ends with `.png`, and `result.output["generated_image"].device_type` is one of `{"cuda", "mps", "cpu"}`.

### Tests for User Story 1

> **Write these tests FIRST — confirm they FAIL before implementing T011–T014**

- [x] T007 [P] [US1] Write unit test for successful generation in `tests/unit/test_stable_diffusion_node.py` — mock `ModelRegistry.get` to return a fake `_PipelineHolder` whose `.run()` returns minimal valid PNG bytes; assert `result.status == COMPLETED`, `result.output["image_file_path"]` is an absolute path ending in `.png`, `result.output["generated_image"]` is a `GeneratedImage` with `generation_duration_ms >= 0`
- [x] T008 [P] [US1] Write unit test for missing template variable in `tests/unit/test_stable_diffusion_node.py` — supply `prompt="{color} apple"` with no `color` in `NodeContext.input_data` or `previous_outputs`; assert `result.status == FAILED` and `result.error` mentions the missing variable name
- [x] T009 [P] [US1] Write unit test for empty rendered prompt in `tests/unit/test_stable_diffusion_node.py` — supply `prompt="{var}"` with `var=""` in context; assert `result.status == FAILED`
- [x] T010 [P] [US1] Write unit test for structured log emission in `tests/unit/test_stable_diffusion_node.py` — capture logs via `structlog.testing.capture_logs()` during a successful `execute_async` call; assert at least two log entries are emitted (start event and completion event) per execution (FR-014, SC-007)

### Implementation for User Story 1

- [x] T011 [US1] Implement `StableDiffusionNode.__init__` in `src/generative_ai_workflow/node.py` — signature: `(self, name: str, prompt: str, model_id: str, width: int = 512, height: int = 512, num_inference_steps: int = 20, guidance_scale: float = 7.5, output_dir: str = "./generated_images", is_critical: bool = True)`; call `super().__init__(name=name, is_critical=is_critical)`; construct and store a `GenerationConfig`; raise `ValueError` for empty `name` or empty `prompt` (contracts/stable_diffusion_node.py constructor contract)
- [x] T012 [US1] Implement prompt template substitution helper in `src/generative_ai_workflow/node.py` — merges `context.input_data` and `context.previous_outputs` (flattened) into a substitution dict, applies `str.format_map()`, returns `(rendered: str, error: str | None)`; mirrors `LLMNode` substitution behavior (FR-002, FR-009)
- [x] T013 [US1] Implement `StableDiffusionNode.execute_async` in `src/generative_ai_workflow/node.py` — follows the 10-point contract in `contracts/stable_diffusion_node.py`: (1) render prompt, return FAILED on error or empty result; (2) retrieve `_PipelineHolder` via `ModelRegistry.get(model_id)`; (3) call `holder.run(prompt, width, height, steps, guidance_scale)` inside `asyncio.get_event_loop().run_in_executor(None, ...)` to keep event loop unblocked; (4) convert PNG bytes from holder; (5) save to `output_dir/<uuid4>.png` (create dir if absent); (6) build and return `NodeResult(status=COMPLETED, output={"generated_image": GeneratedImage(...), "image_file_path": str(path), "image_bytes": bytes})`; (7) wrap entire method body in broad `except Exception` returning FAILED; NEVER raise (research.md Decisions 4 & 5)
- [x] T014 [US1] Add structlog observability to `StableDiffusionNode.execute_async` in `src/generative_ai_workflow/node.py` — use `get_logger(__name__)` bound with `node_name` and `model_id`; emit start-event log before inference; emit completion-event log with `status`, `file_path`, `generation_duration_ms`, `device_type` on success; emit failure-event log with `error` on any exception; use `NodeTimer` from `generative_ai_workflow.observability.metrics` to capture wall-clock duration and populate `GeneratedImage.generation_duration_ms` (FR-014, SC-007)

**Checkpoint**: User Story 1 complete — `StableDiffusionNode` generates images and returns structured results with observability. Test independently with a local model before proceeding.

---

## Phase 4: User Story 2 — Configure Generation Parameters (Priority: P2)

**Goal**: A workflow author specifies image dimensions, inference step count, and guidance scale at construction time. The node validates all parameters eagerly and raises descriptive `ValueError`s before any model loading or I/O. Valid parameters are propagated unchanged to the inference call.

**Independent Test**: (1) Construct `StableDiffusionNode(name="x", prompt="y", model_id="m", width=768, height=256, num_inference_steps=30, guidance_scale=8.0)`, mock `holder.run` to capture kwargs, execute, assert `width=768`, `height=256`, `num_inference_steps=30`, `guidance_scale=8.0`. (2) Attempt `StableDiffusionNode(name="x", prompt="y", model_id="m", width=7)` — assert `ValueError` raised.

### Tests for User Story 2

> **Write these tests FIRST — confirm they FAIL before implementing T017–T018**

- [x] T015 [P] [US2] Write unit tests for invalid construction parameters in `tests/unit/test_stable_diffusion_node.py` — one `pytest.raises(ValueError)` test per case: `width=0`, `height=-1`, `height=7` (not multiple of 8), `num_inference_steps=0`, `guidance_scale=-0.1`, `model_id=""`, `prompt=""`; confirm no file system side-effects occur (FR-011, SC-005)
- [x] T016 [P] [US2] Write unit test for parameter propagation in `tests/unit/test_stable_diffusion_node.py` — construct node with `width=768, height=256, num_inference_steps=30, guidance_scale=8.0`; mock `holder.run` to capture call arguments; execute `execute_async`; assert all four values are passed correctly to `holder.run` (FR-003, FR-004)

### Implementation for User Story 2

- [x] T017 [US2] Wire `GenerationConfig` Pydantic validation to the public constructor in `src/generative_ai_workflow/node.py` — catch `pydantic.ValidationError` raised when constructing `GenerationConfig` inside `__init__` and re-raise as `ValueError` with the field name and constraint in the message; ensures `ValueError` (not `ValidationError`) is the public contract (FR-011, data-model.md GenerationConfig validation rules)
- [x] T018 [US2] Confirm `self._config` fields drive the `holder.run()` call in `execute_async` in `src/generative_ai_workflow/node.py` — verify `self._config.width`, `self._config.height`, `self._config.num_inference_steps`, `self._config.guidance_scale` are the values forwarded (no hardcoded defaults in the call site) (FR-003, FR-004)

**Checkpoint**: User Story 2 complete — parameter validation and propagation verified. US1 and US2 independently testable.

---

## Phase 5: User Story 3 — Non-Critical Node Failure Mode (Priority: P3)

**Goal**: When `is_critical=False`, a `StableDiffusionNode` that encounters any generation error (OOM, missing weights, corrupt model) returns `status=FAILED` with a descriptive error and does not raise to the workflow engine, allowing subsequent nodes to continue executing.

**Independent Test**: Construct `StableDiffusionNode(name="opt", prompt="test", model_id="bad", is_critical=False)`, mock `ModelRegistry.get` to raise `RuntimeError("OOM")`, call `execute_async`, assert `result.status == FAILED`, `result.error` is non-empty, and no exception propagates. Then run a two-node workflow with this as the first node and a `TransformNode` second — assert the `TransformNode` output is present in `workflow_result.node_outputs`.

### Tests for User Story 3

> **Write these tests FIRST — confirm they FAIL before implementing T021**

- [x] T019 [P] [US3] Write unit test for non-critical failure in `tests/unit/test_stable_diffusion_node.py` — mock `ModelRegistry.get` to raise `RuntimeError("OOM")`; construct `StableDiffusionNode(is_critical=False)`; call `execute_async`; assert `result.status == FAILED`, `result.error` contains the exception message, no exception propagates (FR-008, FR-010, SC-003)
- [x] T020 [P] [US3] Write integration test that verifies workflow continues past non-critical failure in `tests/unit/test_stable_diffusion_node.py` — compose a `Workflow` with a failing `StableDiffusionNode(is_critical=False)` as the first node and a simple `TransformNode` as the second; execute the workflow; assert the `TransformNode` output is present in the final result (SC-001, FR-010)

### Implementation for User Story 3

- [x] T021 [US3] Verify `is_critical` is correctly passed to `WorkflowNode` base class in `StableDiffusionNode.__init__` in `src/generative_ai_workflow/node.py` — confirm `super().__init__(name=name, is_critical=is_critical)` is called; the broad `except Exception → FAILED` pattern in `execute_async` (T013) already satisfies FR-008; no additional error handling is needed if `WorkflowNode` handles `is_critical` routing (FR-010)

**Checkpoint**: All three user stories complete and independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Public exports, documentation, backward compatibility verification, and end-to-end quickstart validation.

- [x] T022 Add `StableDiffusionNode` and `GeneratedImage` to public exports in `src/generative_ai_workflow/node.py` and (if applicable) `src/generative_ai_workflow/__init__.py` so downstream users can import via `from generative_ai_workflow.node import StableDiffusionNode, GeneratedImage` (quickstart.md Example 1 import path)
- [x] T023 [P] Update `CHANGELOG.md` — add entry for next version documenting additions: `StableDiffusionNode`, `ModelRegistry`, `GeneratedImage`, `GenerationConfig`, optional `[stable-diffusion]` extras group; note no breaking changes to existing `LLMNode`, `TransformNode`, or `WorkflowNode` public APIs (Principle X)
- [x] T024 [P] Verify backward compatibility — run `pytest tests/ -x` excluding the new test file to confirm zero regressions in pre-existing tests (SC-001, Principle X)
- [ ] T025 [P] Run quickstart.md validation — execute Example 1 (static prompt) and Example 2 (LLMNode + StableDiffusionNode) from `specs/001-stable-diffusion-node/quickstart.md` against a locally available model to confirm end-to-end usability (requires model weights pre-downloaded per quickstart.md prerequisites section)
- [x] T026 [P] Verify observability completeness — run unit tests with log capture and confirm every `execute_async` invocation (success and failure paths) emits at least one start-event log, one terminal-event log, and records `generation_duration_ms >= 0` in the `GeneratedImage` output (SC-007, FR-014)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1. BLOCKS all user story phases.
- **User Stories (Phases 3–5)**: All depend on Phase 2 completion; can proceed sequentially (P1→P2→P3) or in parallel if staffed.
- **Polish (Phase 6)**: Depends on all desired user stories complete.

### User Story Dependencies

| Story | Depends On | Independent? |
|-------|-----------|--------------|
| US1 (Phase 3) | Phase 2 only | Yes — fully independent |
| US2 (Phase 4) | Phase 2 + T011 (`__init__` skeleton) | Extends US1 constructor validation |
| US3 (Phase 5) | Phase 2 + T013 (`execute_async`) | Extends US1 error-handling path |

> US2 and US3 extend code introduced in US1 but are independently testable: US2 covers the construction/validation path and US3 covers the error/failure path without requiring successful inference.

### Within Each User Story

1. Tests MUST be written first and confirmed failing
2. Data models / helpers before core logic
3. Core logic before observability integration
4. Story complete and checkpoint validated before next priority

### Parallel Opportunities

- **Phase 2**: T003, T005, T006 can run in parallel (different classes/files); T004 follows T002+T003
- **Phase 3 tests**: T007, T008, T009, T010 are independent test functions — write in parallel
- **Phase 4 tests**: T015, T016 are independent test functions — write in parallel
- **Phase 5 tests**: T019, T020 are independent test functions — write in parallel
- **Phase 6**: T022, T023, T024, T025, T026 all touch different files — run in parallel

---

## Parallel Example: User Story 1 Tests

```bash
# All four US1 test tasks can be written simultaneously (independent test functions):
Task: "Write unit test for successful generation (T007)"   # tests/unit/test_stable_diffusion_node.py
Task: "Write unit test for missing template variable (T008)"
Task: "Write unit test for empty rendered prompt (T009)"
Task: "Write unit test for structured log emission (T010)"
```

## Parallel Example: Phase 2 Foundational

```bash
# After T002, run T003/T005/T006 in parallel:
Task: "Implement _PipelineHolder (T003)"   # sd_model_registry.py
Task: "Implement GenerationConfig (T005)"  # sd_model_registry.py
Task: "Implement GeneratedImage (T006)"    # node.py
# Then sequentially: T004 ModelRegistry (depends on T002 + T003)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: `pyproject.toml` extras
2. Complete Phase 2: `ModelRegistry`, `GenerationConfig`, `GeneratedImage`
3. Complete Phase 3: Core generation + observability (US1)
4. **STOP and VALIDATE**: Run unit tests; optionally test with a local model
5. Demo or deliver — fully working image generation in a workflow

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. User Story 1 → test independently → **MVP delivery point**
3. User Story 2 → parameter validation → test independently
4. User Story 3 → non-critical failure mode → test independently
5. Polish → exports, CHANGELOG, backward compat, quickstart

### Parallel Team Strategy (2 developers)

After Phase 2 completes:

- **Developer A**: Phase 3 (US1) — T007–T014 (core generation path)
- **Developer B**: Phase 4 tests (T015–T016) + Phase 5 tests (T019–T020), then implementation once US1 lands

---

## Notes

- `[P]` tasks can run in parallel — different files or independent code sections with no mutual dependencies
- `[USn]` label maps each task to its user story for traceability
- Tests MUST be written first and confirmed failing before implementation (SC-006)
- `sd_model_registry.py` is a **new file**; `node.py` is **extended in-place** (add `StableDiffusionNode` + `GeneratedImage` alongside existing `LLMNode`, `TransformNode`)
- `ModelRegistry` uses a module-level dict — see `plan.md` Complexity Tracking for the justified deviation from Principle III (dependency injection); this follows the existing `PluginRegistry` pattern
- No token tracking (Principle IV AI-Specific deviation) — substituted with `inference_steps`, resolution, `guidance_scale`, `device_type`, `generation_duration_ms` per `plan.md`
- Model weights must be pre-downloaded before running quickstart validation (see `specs/001-stable-diffusion-node/quickstart.md` Prerequisites section)
- **Principle XII — Branch-Per-Task**: Work each task on its own branch (`<task-id>-<short-description>`), merge to main only after unit AND integration tests pass
- Total tasks: 26 (T001–T026)
