# Research: Rename Step Concept to Node

**Feature**: 003-rename-step-node
**Date**: 2026-02-21
**Status**: Complete — no NEEDS CLARIFICATION items; all decisions resolved in spec clarifications.

---

## Decision 1: Python Module Rename Strategy

**Decision**: Hard rename `step.py` → `node.py` with no `step.py` re-export shim. The old import path `generative_ai_workflow.step` is permanently removed.

**Rationale**: The project is pre-alpha (v0.x) with explicitly no backward compatibility guarantees per README. A re-export shim would keep the old module path alive, contradicting the hard-removal decision. Python 3.11+ has no special behavior requiring compatibility shims for intra-package module renames.

**Alternatives considered**:
- Keep `step.py` with class renames only → Rejected. Module path `generative_ai_workflow.step` would still reference "step", creating a partial and confusing rename (Clarification Q2, chose Option A: full rename).
- Add `step.py` re-export shim → Rejected. Creates technical debt and explicitly violates the hard-removal decision (Clarification Q1, chose Option A: hard removal).

---

## Decision 2: Scope of Supporting Type Renames

**Decision**: Rename all public types whose names contain "Step" to use "Node", including supporting execution-model types:

| Old | New | File |
|-----|-----|------|
| `WorkflowStep` | `WorkflowNode` | `step.py` → `node.py` |
| `LLMStep` | `LLMNode` | `step.py` → `node.py` |
| `TransformStep` | `TransformNode` | `step.py` → `node.py` |
| `ConditionalStep` | `ConditionalNode` | `control_flow.py` |
| `StepResult` | `NodeResult` | `workflow.py` |
| `StepContext` | `NodeContext` | `workflow.py` |
| `StepStatus` | `NodeStatus` | `workflow.py` |
| `StepError` | `NodeError` | `exceptions.py` |

Additionally, the `Workflow` constructor parameter `steps=` is renamed to `nodes=`, and the `workflow.steps` attribute becomes `workflow.nodes`. The `true_steps`/`false_steps` parameters of `ConditionalNode` become `true_nodes`/`false_nodes`.

**Rationale**: These types represent the execution model of a node (context passed in, result returned, status, error). Leaving `StepResult`, `StepContext`, `StepStatus`, `StepError` as "Step*" while building blocks become "Node*" would create a conceptually inconsistent public API. FR-003 (all framework messages use "node") and FR-004 (documentation uses "node" exclusively) imply a complete terminology shift.

**Alternatives considered**:
- Rename only the 4 explicitly named building-block classes → Rejected. Would leave `StepResult`, `StepContext`, `StepStatus`, `StepError` as "step"-named types in an otherwise node-centric API.

---

## Decision 3: Version Bump Strategy

**Decision**: Bump `pyproject.toml` version from `0.1.0` → `0.2.0` and update `__version__` in `__init__.py`.

**Rationale**: Per semver.org, before v1.0.0 "anything MAY change at any time." Minor version increment (0.1.x → 0.2.0) conventionally signals a notable breaking change in pre-alpha Python libraries without implying production readiness.

**Alternatives considered**:
- 0.1.1 (patch) → Rejected. This is a comprehensive breaking API rename, not a bug fix.
- 1.0.0 (major) → Rejected. Library is explicitly pre-alpha and not production-ready.

---

## Decision 4: Test Strategy

**Decision**: Rename all existing tests to use node names AND add one test that explicitly verifies importing old step names raises `ImportError`.

**Rationale**: Renaming existing tests validates that node-named types behave identically to the former step-named types. The `ImportError` test is the only explicit validation of FR-002 (hard removal) — without it the test suite could pass even if old names accidentally remained importable. (Clarification Q3, Option B.)

**Alternatives considered**:
- Only rename existing tests → Rejected. Does not validate hard removal.
- Leave existing tests unchanged → Rejected. Tests would immediately fail on import of old names, providing no value.

---

## Decision 5: CHANGELOG Entry

**Decision**: Add a `## [0.2.0] - 2026-02-21` section to `CHANGELOG.md` with a `### Removed` subsection listing every old name with its replacement, satisfying SC-004 (developer identifies all changes within 5 minutes).

**Format**: Migration table: Old name → New name, plus note on module path change.
