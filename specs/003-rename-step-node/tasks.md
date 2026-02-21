# Tasks: Rename Step Concept to Node

**Feature**: `003-rename-step-node` | **Branch**: `003-rename-step-node`
**Input**: Design documents from `/specs/003-rename-step-node/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Organization**: Tasks grouped by user story. Each phase is independently testable.

**Tests**: Tests are included per SC-003 (explicitly required: rename existing tests + add ImportError test).

---

## Phase 1: Setup

**Purpose**: Verify scope before making changes.

- [X] T001 Audit all "step" occurrences across src/, tests/, examples/, README.md to confirm full rename scope matches data-model.md rename map

---

## Phase 2: Foundational (Core Module Rename)

**Purpose**: Rename the primary node module and execution-model types. All user story phases depend on this.

**⚠️ CRITICAL**: Complete Phase 2 fully before beginning any user story phase.

- [X] T002 Create src/generative_ai_workflow/node.py — copy step.py and rename `WorkflowStep` → `WorkflowNode`, `LLMStep` → `LLMNode`, `TransformStep` → `TransformNode` in class definitions, docstrings, and all internal references
- [X] T003 Delete src/generative_ai_workflow/step.py (old module permanently removed per FR-007)
- [X] T004 Update src/generative_ai_workflow/workflow.py — rename `StepResult` → `NodeResult`, `StepContext` → `NodeContext`, `StepStatus` → `NodeStatus`; rename `Workflow.steps` attribute and `steps=` constructor parameter to `nodes`; update `TYPE_CHECKING` import from `step` to `node`
- [X] T005 Update src/generative_ai_workflow/exceptions.py — rename `StepError` → `NodeError` in class definition, docstring, and all internal references
- [X] T006 Update src/generative_ai_workflow/__init__.py — remove all `*Step`, `StepResult`, `StepContext`, `StepStatus` exports; add `WorkflowNode`, `LLMNode`, `TransformNode`, `NodeResult`, `NodeContext`, `NodeStatus`, `NodeError` exports; update `__version__` from `"0.1.0"` to `"0.2.0"`
- [X] T007 [P] Update pyproject.toml — bump `version` from `"0.1.0"` to `"0.2.0"`

**Checkpoint**: `python -c "from generative_ai_workflow import LLMNode, TransformNode, WorkflowNode"` succeeds; `python -c "from generative_ai_workflow import LLMStep"` raises `ImportError`.

---

## Phase 3: User Story 1 — Build Workflows Using Node Terminology (Priority: P1) 🎯 MVP

**Goal**: All public workflow-building-block types use "node" names; old step names raise `ImportError`; all framework messages use "node"; version bumped and changelog updated.

**Independent Test**: Construct a `Workflow(nodes=[LLMNode(...), TransformNode(...)])` and execute it; verify all types resolve, workflow runs without error, and `from generative_ai_workflow import LLMStep` raises `ImportError`.

### Implementation for User Story 1

- [X] T008 [US1] Update src/generative_ai_workflow/control_flow.py — rename `ConditionalStep` → `ConditionalNode`; rename `true_steps` / `false_steps` parameters and attributes to `true_nodes` / `false_nodes`; update `TYPE_CHECKING` import from `step` to `node`; update all docstrings and log messages to use "node"
- [X] T009 [P] [US1] Update src/generative_ai_workflow/engine.py — replace `WorkflowStep` with `WorkflowNode` in all type hints and log/error messages
- [X] T010 [US1] Add `## [0.2.0] - 2026-02-21` section to CHANGELOG.md with a `### Removed` subsection containing the full migration table (all 12 renamed symbols: old name → new name) and the module path change (`generative_ai_workflow.step` → `generative_ai_workflow.node`)

### Tests for User Story 1

- [X] T011 [P] [US1] Update tests/conftest.py — replace all Step/StepResult/StepContext/StepStatus imports with their Node counterparts
- [X] T012 [US1] Rename tests/unit/test_step.py → tests/unit/test_node.py; update all imports, class name references, fixture names, and assertions to use node terminology throughout
- [X] T013 [P] [US1] Update tests/unit/test_workflow.py — replace `StepResult`, `StepContext`, `StepStatus`, `steps=` with `NodeResult`, `NodeContext`, `NodeStatus`, `nodes=` in all imports and test bodies
- [X] T014 [P] [US1] Update tests/unit/test_engine.py — replace all `WorkflowStep` / `LLMStep` / `TransformStep` references with `WorkflowNode` / `LLMNode` / `TransformNode`
- [X] T015 [P] [US1] Update tests/unit/test_control_flow.py — replace `ConditionalStep` → `ConditionalNode`; replace `true_steps` → `true_nodes` and `false_steps` → `false_nodes` in all constructor calls and assertions
- [X] T016 [US1] Create tests/unit/test_import_removal.py — assert that `from generative_ai_workflow import LLMStep` raises `ImportError`; assert the same for `TransformStep`, `WorkflowStep`, `ConditionalStep`, `StepResult`, `StepContext`, `StepStatus`; assert that `import generative_ai_workflow.step` raises `ImportError` (SC-003)

**Checkpoint**: `pytest tests/unit/` passes with zero failures; `pytest tests/unit/test_import_removal.py` confirms all old names raise `ImportError`.

---

## Phase 4: User Story 2 — Extend Framework with Custom Nodes (Priority: P2)

**Goal**: The extension API (`WorkflowNode` base class, middleware, plugin registry) uses "node" terminology throughout so custom node implementations feel consistent with built-in nodes.

**Independent Test**: Subclass `WorkflowNode`, register it in a `Workflow(nodes=[...])`, execute the workflow, and verify the custom node executes correctly; inspect middleware and registry type hints to confirm no "Step" names remain.

### Implementation for User Story 2

- [X] T017 [P] [US2] Update src/generative_ai_workflow/middleware/base.py — replace `WorkflowStep` with `WorkflowNode` in all type annotations, docstrings, and method signatures
- [X] T018 [P] [US2] Update src/generative_ai_workflow/plugins/registry.py — replace `WorkflowStep` with `WorkflowNode` in all type annotations, docstrings, and method signatures

### Tests for User Story 2

- [X] T019 [P] [US2] Update tests/unit/middleware/test_base.py — replace `WorkflowStep` with `WorkflowNode` in all imports and test assertions

**Checkpoint**: `pytest tests/unit/middleware/` passes; mypy finds no remaining `WorkflowStep` references in middleware/ or plugins/.

---

## Phase 5: User Story 3 — Updated Documentation and Examples (Priority: P3)

**Goal**: All bundled documentation, quickstart guide, README, integration tests, and example code use "node" terminology exclusively — zero occurrences of the old "step" building-block term in user-facing content.

**Independent Test**: `grep -r "LLMStep\|TransformStep\|WorkflowStep\|ConditionalStep\|StepResult\|StepContext\|StepStatus\|StepError" examples/ README.md` returns no matches.

### Implementation for User Story 3

- [X] T020 [P] [US3] Update src/generative_ai_workflow/observability/logging.py — replace "step" with "node" in all log field names and human-readable log event strings (e.g., `"step_name"` → `"node_name"`, `"step execution failed"` → `"node execution failed"`)
- [X] T021 [P] [US3] Update src/generative_ai_workflow/observability/metrics.py — replace "step" with "node" in all metric key names
- [X] T022 [P] [US3] Update src/generative_ai_workflow/observability/tracker.py — replace "step" with "node" in all tracker field names and log messages
- [X] T023 [P] [US3] Update examples/complete_workflow_example.py — replace all `LLMStep`, `TransformStep`, `WorkflowStep`, `ConditionalStep` references with node equivalents; replace `steps=[...]` with `nodes=[...]` in all `Workflow(...)` constructor calls
- [X] T024 [US3] Update README.md Quick Start section — replace step class names with node names; replace `Workflow(steps=[...])` with `Workflow(nodes=[...])`; ensure code example matches quickstart.md exactly

### Tests for User Story 3

- [X] T025 [P] [US3] Update tests/integration/test_full_workflow.py — replace all `LLMStep`, `TransformStep`, `StepResult`, `steps=` with their node equivalents throughout
- [X] T026 [P] [US3] Update tests/integration/test_control_flow_integration.py — replace `ConditionalStep` → `ConditionalNode`; replace `true_steps` → `true_nodes`; replace `false_steps` → `false_nodes`
- [X] T027 [P] [US3] Update tests/integration/test_provider_retry.py — replace all step class and parameter references with node equivalents
- [X] T028 [P] [US3] Update tests/integration/test_performance.py — replace all step class and parameter references with node equivalents

**Checkpoint**: `pytest tests/integration/` passes; `grep -r "LLMStep\|TransformStep\|WorkflowStep\|ConditionalStep" examples/ README.md tests/integration/` returns no matches.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification that all 12 renamed symbols are consistent across the entire codebase.

- [X] T029 Run `ruff check src/` — fix any linting errors introduced by the rename
- [X] T030 [P] Run `mypy src/` — verify all type annotations are consistent with the renamed types; fix any remaining `WorkflowStep` / `StepResult` / `StepContext` / `StepStatus` / `StepError` type annotation residuals
- [X] T031 Run `pytest tests/unit/ -v` — confirm all unit tests pass with zero failures
- [X] T032 Run `pytest tests/integration/ -v` — confirm all integration tests pass with zero failures
- [X] T033 [P] Final audit: run `grep -rn "WorkflowStep\|LLMStep\|TransformStep\|ConditionalStep\|StepResult\|StepContext\|StepStatus\|StepError" src/ tests/ examples/ README.md CHANGELOG.md` — confirm zero matches in user-facing code (only legitimate internal uses, if any, should remain)
- [X] T034 [P] Verify quickstart.md examples against the contracts in specs/003-rename-step-node/contracts/node_api.py — confirm all parameter names and return types in examples match the implemented API

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup; **BLOCKS all user story phases**
- **User Story Phases (3–5)**: All depend on Phase 2 completion; can proceed in priority order or in parallel if staffed
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (Phase 3)**: Requires Phase 2 — no dependencies on US2 or US3
- **US2 (Phase 4)**: Requires Phase 2 — independent of US1 and US3
- **US3 (Phase 5)**: Requires Phase 2 — independent of US1 and US2 (though US3 integration tests will pass only once US1 core types are correct)

### Within Phase 2 (Sequential — same files)

T002 (create node.py) → T003 (delete step.py) → T004 (update workflow.py) → T005 (update exceptions.py) → T006 (update __init__.py); T007 is independent and can run in parallel with any of the above.

### Within Phase 3 (US1)

T008–T010 (implementation) must complete before T011–T016 (tests); tests T011–T015 can run in parallel with each other once implementation is done; T016 (ImportError test) requires T006 (__init__.py updated) to be complete.

---

## Parallel Opportunities

### Phase 2 Parallel

```bash
# These can run in parallel (different files):
Task: "Update pyproject.toml version bump" (T007)

# These must be sequential (ordering matters for import correctness):
T002 → T003 → T004 → T005 → T006
```

### Phase 3 Parallel (after T008–T010 complete)

```bash
Task: "Update tests/conftest.py" (T011)
Task: "Update tests/unit/test_workflow.py" (T013)
Task: "Update tests/unit/test_engine.py" (T014)
Task: "Update tests/unit/test_control_flow.py" (T015)
```

### Phase 5 Parallel (all independent files)

```bash
Task: "Update observability/logging.py" (T020)
Task: "Update observability/metrics.py" (T021)
Task: "Update observability/tracker.py" (T022)
Task: "Update examples/complete_workflow_example.py" (T023)
Task: "Update integration/test_full_workflow.py" (T025)
Task: "Update integration/test_control_flow_integration.py" (T026)
Task: "Update integration/test_provider_retry.py" (T027)
Task: "Update integration/test_performance.py" (T028)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T007) — **CRITICAL blocker**
3. Complete Phase 3: User Story 1 (T008–T016)
4. **STOP and VALIDATE**: `pytest tests/unit/` passes; ImportError test passes
5. Merge if ready

### Incremental Delivery

1. Setup + Foundational → core types renamed; all imports updated
2. User Story 1 → workflow construction with node API works; tests validate hard removal → **Ship 0.2.0 MVP**
3. User Story 2 → extension API consistent; middleware/plugin names updated
4. User Story 3 → docs, examples, integration tests clean; zero "step" terminology in user-facing content

---

## Task Summary

| Phase | Tasks | Count | Notes |
|-------|-------|-------|-------|
| Phase 1: Setup | T001 | 1 | No dependencies |
| Phase 2: Foundational | T002–T007 | 6 | Blocks all stories |
| Phase 3: US1 (P1) | T008–T016 | 9 | Core API rename + tests |
| Phase 4: US2 (P2) | T017–T019 | 3 | Extension API |
| Phase 5: US3 (P3) | T020–T028 | 9 | Docs, examples, integration |
| Phase 6: Polish | T029–T034 | 6 | Final audit + CI |
| **Total** | | **34** | |

**Parallel opportunities**: 18 of 34 tasks marked `[P]`
**MVP scope**: T001–T016 (Phases 1–3 only, 16 tasks)
