# Tasks: Prometheus Observability Middleware

**Input**: Design documents from `/specs/001-prometheus-middleware/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no pending dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add optional dependency and create module skeleton.

- [x] T001 Add `[observability]` extras group with `prometheus-client>=0.16.0` to `pyproject.toml`
- [x] T002 [P] Create `src/generative_ai_workflow/middleware/prometheus.py` with top-of-file ImportError guard (FR-009) and empty `PrometheusMiddleware(Middleware)` class stub

**Checkpoint**: `import generative_ai_workflow` succeeds without `prometheus-client` installed; importing `prometheus.py` directly raises `ImportError` with install hint.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core class construction — metric descriptor registration, sanitiser, label helpers. Must be complete before any user story hook implementation.

**⚠️ CRITICAL**: No user story hook work can begin until this phase is complete.

- [x] T003 Implement `PrometheusMiddleware.__init__` in `src/generative_ai_workflow/middleware/prometheus.py` — register all 6 metric descriptors (`_workflow_duration` Histogram, `_workflow_total` Counter, `_node_duration` Histogram, `_node_errors` Counter, `_tokens_prompt` Counter, `_tokens_completion` Counter) with configurable `prefix`, `registry`, and `buckets` parameters; use `try/except ValueError` around each `register()` call to handle shared-registry reuse
- [x] T004 [P] Implement `_sanitise(value: str) -> str` private method in `src/generative_ai_workflow/middleware/prometheus.py` — default: `re.sub(r"[^a-zA-Z0-9_]", "_", value)`, empty result → `"unknown"`, delegates to caller-supplied `label_sanitiser` when provided (FR-010, FR-014)
- [x] T005 [P] Update `src/generative_ai_workflow/middleware/__init__.py` — add lazy `PrometheusMiddleware` export guarded by `TYPE_CHECKING` so the package import does not require `prometheus-client`

**Checkpoint**: `PrometheusMiddleware(prefix="test")` instantiates cleanly with a fresh `CollectorRegistry`; 6 metric families visible in registry output.

---

## Phase 3: User Story 1 — Monitor Workflow Execution Metrics (Priority: P1) 🎯 MVP

**Goal**: An operator attaches PrometheusMiddleware and sees workflow duration histograms, completion counters, per-node durations, and node error counts in their Prometheus scrape output.

**Independent Test**: Run a workflow with `PrometheusMiddleware(registry=custom_registry)` attached, call `generate_latest(custom_registry)`, verify at least 4 metric families appear with correct label values and status.

### Implementation for User Story 1

- [x] T006 [US1] Implement `on_workflow_end` hook in `src/generative_ai_workflow/middleware/prometheus.py` — extract `workflow_name` from `ctx`, sanitise; observe `_workflow_duration` (`result.metrics.total_duration_ms / 1000`), increment `_workflow_total` (`result.status.value`), iterate `result.metrics.step_durations` and observe `_node_duration` per node; wrap all recording in try/except and log warnings via structlog (FR-002, FR-003, FR-004, FR-011, FR-012)
- [x] T007 [US1] Implement `on_node_error` hook in `src/generative_ai_workflow/middleware/prometheus.py` — extract `workflow_name` from `ctx`, sanitise `node_name`, increment `_node_errors`; wrap in try/except (FR-006, FR-012)
- [x] T008 [P] [US1] Write unit tests in `tests/unit/middleware/test_prometheus_middleware.py` — test `on_workflow_end` records `{prefix}_duration_seconds`, `{prefix}_total`, `{prefix}_node_duration_seconds` with correct labels using mock `WorkflowResult`; test `on_node_error` increments `{prefix}_node_errors_total`; test errors in recording are swallowed (FR-012); test with custom prefix
- [x] T009 [US1] Write integration test in `tests/integration/test_prometheus_integration.py` — attach `PrometheusMiddleware` to real `WorkflowEngine` with `MockProvider`, run a workflow, call `generate_latest(registry)`, assert ≥4 metric families present (SC-001), assert `workflow_name` label matches workflow `.name` (SC-002)

**Checkpoint**: User Story 1 independently functional. `pytest tests/unit/middleware/test_prometheus_middleware.py tests/integration/test_prometheus_integration.py` passes.

---

## Phase 4: User Story 2 — Track Token Usage Per Node (Priority: P2)

**Goal**: A developer queries per-node prompt and completion token counters in Prometheus and identifies which nodes consume the most tokens.

**Independent Test**: Run a two-node workflow (both with token usage) via `MockProvider`; verify `{prefix}_tokens_prompt_total` and `{prefix}_tokens_completion_total` appear with distinct `node` labels matching each node name (SC-002). Verify a node with no token usage emits no token metrics.

### Implementation for User Story 2

- [x] T010 [US2] Add token metric recording to `on_workflow_end` in `src/generative_ai_workflow/middleware/prometheus.py` — iterate `result.metrics.step_token_usage`, sanitise `node_name` and `usage.model`, increment `_tokens_prompt` by `usage.prompt_tokens` and `_tokens_completion` by `usage.completion_tokens`; skip nodes with `None` usage (FR-005, FR-011)
- [x] T011 [P] [US2] Add token-specific unit tests to `tests/unit/middleware/test_prometheus_middleware.py` — test prompt/completion counters increment correctly; test nodes with no token usage emit no token metrics (FR-005 zero-pollution rule); test `model` label is sanitised

**Checkpoint**: User Stories 1 and 2 both work independently. Token counters visible in Prometheus output with correct per-node, per-model labels.

---

## Phase 5: User Story 3 — Zero-Config Registry Isolation (Priority: P3)

**Goal**: A library user passes a custom `CollectorRegistry` and verifies global registry is unaffected; a user who passes no registry gets global default registry.

**Independent Test**: Instantiate `PrometheusMiddleware(registry=CollectorRegistry())`, run a workflow, assert `REGISTRY` (global) has zero new metric families (SC-003). Also instantiate `PrometheusMiddleware()` (no registry arg) and assert it uses global `REGISTRY`.

### Implementation for User Story 3

- [x] T012 [US3] Add unit tests in `tests/unit/middleware/test_prometheus_middleware.py` — test custom `CollectorRegistry` isolation: metrics appear only in custom registry, not in `prometheus_client.REGISTRY` (SC-003); test default instantiation registers to `prometheus_client.REGISTRY`; test two `PrometheusMiddleware` instances sharing a registry do not raise `ValueError` (double-registration safety) (FR-007, Edge Case)
- [x] T013 [P] [US3] Add integration test for registry isolation to `tests/integration/test_prometheus_integration.py` — run workflow with isolated registry, scrape with `generate_latest(custom_registry)`, verify global `generate_latest()` output unchanged (SC-003)

**Checkpoint**: All three user stories independently functional. Registry isolation verified by tests.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression verification, and final validation.

- [x] T014 Update `CHANGELOG.md` in project root — add entry for `PrometheusMiddleware` under new minor version (e.g., `0.5.0`): new `[observability]` extras, new class, 6 metric families (Principle X)
- [x] T015 [P] Run full existing test suite (`pytest`) from `src/` to verify SC-005 (zero regressions) — confirm all prior unit and integration tests pass
- [x] T016 [P] Validate `quickstart.md` end-to-end — install package with `[observability]` extras, run the 30-second setup example, confirm metrics appear in `generate_latest()` output
- [x] T017 [P] Verify `ruff check .` passes in `src/` with no new lint errors introduced by `middleware/prometheus.py`

**Checkpoint**: All tests pass, CHANGELOG updated, quickstart validated, linter clean.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story hook work
- **US1 (Phase 3)**: Depends on Phase 2 — no dependency on US2/US3
- **US2 (Phase 4)**: Depends on Phase 2 — T010 extends `on_workflow_end` already created in T006; implement after T006
- **US3 (Phase 5)**: Depends on Phase 2 — tests only (isolation already implemented in T003); can run after Phase 2
- **Polish (Phase 6)**: Depends on all user story phases

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2
- **US2 (P2)**: Independent after Phase 2; T010 adds to `on_workflow_end` created in T006 — sequence after T006
- **US3 (P3)**: Independent after Phase 2 — pure test coverage of constructor behaviour

### Within Each User Story

- Implementation tasks before test tasks (this is a library — tests validate the implementation)
- T003 (metric init) before T006 (hook implementation) before T010 (token extension)
- T004 (sanitiser) before T006/T007/T010 (all use `_sanitise`)

### Parallel Opportunities

- T002, T005 can run in parallel (different files)
- T003, T004 can run in parallel within Phase 2
- T008, T009 can run in parallel within Phase 3 (different test files)
- T011, T012, T013 can run in parallel across Phase 4/5 (different concerns)
- T015, T016, T017 can run in parallel in Phase 6

---

## Parallel Example: User Story 1

```bash
# After T006 + T007 complete:
Task: "T008 unit tests in tests/unit/middleware/test_prometheus_middleware.py"
Task: "T009 integration test in tests/integration/test_prometheus_integration.py"
# Both can run simultaneously
```

---

## Implementation Strategy

### MVP (User Story 1 Only — ~4 tasks)

1. Complete Phase 1: T001, T002
2. Complete Phase 2: T003, T004, T005
3. Complete Phase 3: T006, T007, T008, T009
4. **STOP and VALIDATE**: `pytest` passes, scrape output shows ≥4 metric families
5. Operators can immediately start using the middleware

### Incremental Delivery

1. Phase 1 + 2 → middleware class ready
2. Phase 3 → workflow + node metrics (P1 MVP)
3. Phase 4 → token cost visibility (P2)
4. Phase 5 → library embedding safety (P3)
5. Phase 6 → polish and ship

---

## Notes

- No LLM API calls in any test — all tests use `MockProvider` or mock `WorkflowResult` objects. Cost per test run: $0.
- `[P]` tasks operate on different files and have no blocking inter-task dependencies.
- **Principle XII — Branch-Per-Task**: Each task MUST be worked on in its own branch (`<task-id>-<short-description>`). Merge to main only after unit AND integration tests pass.
- Total tasks: 17 (T001–T017)
- Test tasks: T008, T009, T011, T012, T013 (5 test tasks across 3 user stories)
- Parallel opportunities: 9 tasks marked [P]
