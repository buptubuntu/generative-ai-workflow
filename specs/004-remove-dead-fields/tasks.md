# Tasks: Remove Dead Fields from NodeContext

**Feature**: `004-remove-dead-fields` | **Branch**: `004-remove-dead-fields`
**Input**: Design documents from `/specs/004-remove-dead-fields/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Organization**: Tasks grouped by user story. Each phase is independently testable.

**Tests**: No new test files required — all 172 existing tests pass without modification (confirmed in research.md).

---

## Phase 1: Setup

**Purpose**: Confirm exact scope before making any changes.

- [X] T001 Audit all `variables` occurrences in `src/` — run `grep -rn "variables" src/generative_ai_workflow/` and confirm the 3 expected sites: `workflow.py:97` (field), `engine.py:176` (construction), `node.py:65,166-167` (docstring + fallback)

---

## Phase 2: User Story 1 — Remove `variables` Field (Priority: P1) 🎯 MVP

**Goal**: Delete the `variables` field from `NodeContext`, remove all references to it in `src/`, simplify the unreachable `LLMNode` fallback, and bump the version to `0.3.0`.

**Independent Test**: Run `pytest tests/` — all 172 tests pass with zero failures. Run `grep -rn "context\.variables\|variables: dict\[str, Any\] = Field" src/` — zero matches.

### Implementation for User Story 1

- [X] T002 [US1] Remove `variables: dict[str, Any] = Field(default_factory=dict)` field declaration and its docstring entry (`variables: Template substitution variables.`) from `NodeContext` in `src/generative_ai_workflow/workflow.py` (lines 88 and 97)
- [X] T003 [P] [US1] Remove `variables={},` from the `NodeContext(...)` constructor call in `src/generative_ai_workflow/engine.py` (line 176)
- [X] T004 [P] [US1] Simplify `LLMNode.execute()` model-resolution in `src/generative_ai_workflow/node.py` — replace the 4-line `context.variables` conditional (lines 165–168) with `or "gpt-4o-mini"`; remove ", variables," from the `context` parameter docstring (line 65)
- [X] T005 [P] [US1] Bump `__version__` from `"0.2.0"` to `"0.3.0"` in `src/generative_ai_workflow/__init__.py`
- [X] T006 [P] [US1] Bump `version` from `"0.2.0"` to `"0.3.0"` in `pyproject.toml`
- [X] T007 [P] [US1] Add `## [0.3.0] - 2026-02-22` section to `CHANGELOG.md` with a `### Removed` subsection listing: "`NodeContext.variables` field (`dict[str, Any]`) — was always `{}`, never populated; unreachable `_framework_config` lookup in `LLMNode` simplified to direct `"gpt-4o-mini"` default"

**Checkpoint**: `grep -rn "context\.variables\|variables: dict\[str" src/` returns zero matches; `pytest tests/` passes 172/172.

---

## Phase 3: User Story 2 — Dead-Field Audit (Priority: P2)

**Goal**: Confirm via systematic inspection that no other fields across `NodeResult`, `WorkflowMetrics`, `WorkflowResult`, and `WorkflowConfig` are dead, and record the finding.

**Independent Test**: All fields in the audited types have at least one write site and one read site in `src/`. Document findings in `research.md`.

### Implementation for User Story 2

- [X] T008 [US2] Verify the dead-field audit in `research.md` by cross-checking each field of `NodeResult`, `WorkflowMetrics`, `WorkflowResult`, and `WorkflowConfig` against their usages in `src/` — run `grep -rn "step_id\|status\|output\|error\|duration_ms\|token_usage\|total_duration\|step_durations\|steps_completed\|steps_failed\|steps_skipped\|workflow_id\|correlation_id\|created_at\|completed_at\|provider\|model\|temperature\|max_tokens\|max_iterations\|max_nesting" src/generative_ai_workflow/` to confirm all fields are referenced; update `research.md` Decision 4 findings table with confirmed "None" result

**Checkpoint**: `research.md` Decision 4 findings table confirmed accurate. No additional removals needed.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final verification that the removal is complete and clean.

- [X] T009 Run `grep -rn "context\.variables\|NodeContext.*variables\|variables={}\|\.variables\b" src/` — confirm zero matches
- [X] T010 Run `pytest tests/ -v` — confirm all tests pass with zero failures
- [X] T011 Run `python -c "from generative_ai_workflow.workflow import NodeContext; assert 'variables' not in NodeContext.model_fields, 'variables field still present'; print('OK')"` — confirm field is gone from the live model
- [X] T012 [P] Run `python -c "import generative_ai_workflow; assert generative_ai_workflow.__version__ == '0.3.0'; print('version OK')"` — confirm version bump

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 2)**: Depends on Setup; T002 is the anchor; T003–T007 are independent of each other (different files) and can run in parallel after T001
- **US2 (Phase 3)**: Depends on Phase 2 completion; T008 is a read-only verification task
- **Polish (Phase 4)**: Depends on Phases 2 and 3

### Within Phase 2 (US1)

T002 → (T003, T004, T005, T006, T007 all in parallel)

T002 is first because it removes the field definition; the other tasks remove references to that field. In practice all 6 edits touch different files so they can run in parallel — but logical ordering is T002 first.

---

## Parallel Opportunities

```bash
# After T001 (audit), these can all run in parallel (different files):
Task: "Remove variables={} from engine.py" (T003)
Task: "Simplify LLMNode fallback in node.py" (T004)
Task: "Bump __version__ in __init__.py" (T005)
Task: "Bump version in pyproject.toml" (T006)
Task: "Add CHANGELOG.md 0.3.0 section" (T007)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001) — 2 minutes
2. Complete Phase 2: US1 (T002–T007) — 6 targeted edits, ~10 lines total
3. **STOP and VALIDATE**: `pytest tests/` passes; `grep` confirms zero references
4. Merge if ready

### Full Delivery

1. US1 → field removed, version bumped, CHANGELOG updated
2. US2 → audit confirmed, `research.md` updated
3. Polish → final grep audit + test run + live model assertion

---

## Task Summary

| Phase | Tasks | Count | Notes |
|-------|-------|-------|-------|
| Phase 1: Setup | T001 | 1 | Scope audit |
| Phase 2: US1 (P1) | T002–T007 | 6 | Core removal + version bump |
| Phase 3: US2 (P2) | T008 | 1 | Audit verification |
| Phase 4: Polish | T009–T012 | 4 | Final checks |
| **Total** | | **12** | |

**Parallel opportunities**: T003–T007 all [P] within US1
**MVP scope**: T001–T007 (Phases 1–2 only, 7 tasks)
