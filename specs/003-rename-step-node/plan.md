# Implementation Plan: Rename Step Concept to Node

**Branch**: `003-rename-step-node` | **Date**: 2026-02-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-rename-step-node/spec.md`

## Summary

Rename all public workflow building-block types from "Step" to "Node" throughout the generative-ai-workflow framework (v0.1.0 → v0.2.0). This is a hard breaking change in a pre-alpha library: `WorkflowStep`, `LLMStep`, `TransformStep`, and `ConditionalStep` become `WorkflowNode`, `LLMNode`, `TransformNode`, and `ConditionalNode`; the source module `step.py` is renamed to `node.py`; supporting execution-model types (`StepResult`, `StepContext`, `StepStatus`, `StepError`) become `NodeResult`, `NodeContext`, `NodeStatus`, `NodeError`; the `Workflow` constructor parameter `steps=` and attribute `.steps` become `nodes=` and `.nodes`; all log/error messages use "node"; and `CHANGELOG.md` receives a breaking-change migration note.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic>=2.0, openai>=1.0, structlog>=24.0, tenacity>=8.0, simpleeval>=1.0.0
**Storage**: N/A (in-memory workflow execution state)
**Testing**: pytest + pytest-asyncio; ruff for linting; mypy (strict) for type checking
**Target Platform**: Python library (PyPI installable package)
**Project Type**: Single Python package
**Performance Goals**: N/A — pure rename/refactor, zero runtime performance change
**Constraints**: Hard removal — no backward aliases, no re-export shims; old `generative_ai_workflow.step` import path permanently removed
**Scale/Scope**: 6 source files, 8 test files, 1 example file, README.md, CHANGELOG.md

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` (current version: v1.5.1).

### ✅ Principle I: Interface-First Design
- [x] Public APIs designed with clear interfaces — `WorkflowNode` ABC is the primary interface; contract unchanged, only renamed
- [x] Implementation details hidden behind contracts — no change to encapsulation model
- [x] Interface contracts documented before implementation begins — `contracts/node_api.py` generated in Phase 1
- [x] Breaking interface changes require major version increment — see Complexity Tracking for pre-alpha exception

### ✅ Principle II: Documented Public Interfaces
- [x] All public APIs have docstrings — all renamed classes have updated docstrings using "node" terminology
- [x] Usage examples per non-trivial interface — examples in docstrings updated to use node names
- [x] Type annotations included — all type annotations updated to node names
- [x] Performance characteristics documented — existing perf docs preserved (no change)

### ✅ Principle III: SOLID Principles
- [x] Single Responsibility — rename preserves each class's single responsibility
- [x] Open/Closed — extension via `WorkflowNode` subclassing fully preserved
- [x] Dependencies injected via interfaces — no change to DI patterns
- [x] No new violations introduced

### ✅ Principle IV: Observability
- [x] Structured logging — existing structlog preserved; error messages updated to say "node" (e.g., "ConditionalNode execution failed", "NodeError")
- [x] Metrics for critical operations — no change
- [x] Correlation IDs — no change
- [x] Token tracking — fully preserved; no changes to TokenUsage or tracking logic
- [x] LLM interaction logging — updated to use "node" in all log event messages
- [x] Workflow state tracking — log messages updated ("node" replaces "step" in human-readable output)

### ✅ Principle V: Configurable But Convention First
- [x] N/A — no configuration changes in this feature

### ✅ Principle VI: Unit Tests
- [x] ≥80% code coverage — existing tests renamed and continue to pass
- [x] Fast tests — rename does not affect test speed
- [x] External dependencies mocked — MockLLMProvider unchanged
- [x] Fixture-based LLM testing — VCR cassettes preserved
- [x] Mock providers in unit tests — MockLLMProvider unchanged (not a step/node name)
- [x] ImportError regression test added — verifies `from generative_ai_workflow import LLMStep` raises `ImportError` (SC-003, Clarification Q3)

### ✅ Principle VII: Integration Tests
- [x] Cost budget markers preserved — `@pytest.mark.cost_budget` unchanged
- [x] Tiered execution strategy — commit/PR/nightly tiers preserved
- [x] Semantic validation — no change
- [x] Provider health checks — no change

### ✅ Principle VIII: Security
- [x] No security surface changed — rename is invisible to attackers
- [x] PII detection — `detect_pii()` unaffected
- [x] Input injection validation — `_check_injection()` unaffected
- [x] Secrets in environment variables — no change
- [x] DoW prevention — unchanged

### ✅ Principle IX: Use LTS Dependencies
- [x] No new dependencies introduced — pure rename/refactor
- [x] All existing pinned LTS dependencies unchanged

### ⚠️ Principle X: Backward Compatibility — VIOLATION JUSTIFIED
- [ ] No breaking changes within major version
- [x] Migration note in CHANGELOG.md for breaking changes
- [x] Semantic versioning followed — bumped to 0.2.0 (see Complexity Tracking)
- [x] CHANGELOG.md updated with full migration table

**Justification**: See Complexity Tracking. Pre-alpha library with explicit "no backward compatibility guarantees until v1.0.0" per README. Hard removal is intentional per Clarification Q1.

### ✅ Principle XI: Extensibility & Plugin Architecture
- [x] `WorkflowNode` base class preserves all extension points unchanged
- [x] Plugin registration unaffected (`PluginRegistry` unchanged)
- [x] Middleware base class references updated (`WorkflowStep` → `WorkflowNode`)
- [x] Framework uses its own extension API internally (dog-fooding preserved)

### ✅ Principle XII: Branch-Per-Task Development Workflow
- [x] Currently on dedicated branch `003-rename-step-node`
- [x] Branch naming follows convention
- [x] All spec/design artifacts committed to main before implementation begins
- [x] Each implementation task will have its own sub-branch (e.g., `T001-rename-module`)

---

## Project Structure

### Documentation (this feature)

```text
specs/003-rename-step-node/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── node_api.py      # Phase 1 output — public API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command — NOT created here)
```

### Source Code Changes

```text
src/generative_ai_workflow/
├── __init__.py          ← Update exports: remove Step names, add Node names; bump __version__
├── node.py              ← Renamed from step.py; classes WorkflowNode, LLMNode, TransformNode
├── step.py              ← DELETED
├── control_flow.py      ← ConditionalStep → ConditionalNode; TYPE_CHECKING import updated;
│                           true_steps/false_steps → true_nodes/false_nodes; docstrings/messages updated
├── workflow.py          ← StepResult→NodeResult, StepContext→NodeContext, StepStatus→NodeStatus;
│                           Workflow.steps→Workflow.nodes; TYPE_CHECKING import updated
├── exceptions.py        ← StepError → NodeError; update all references
├── engine.py            ← WorkflowStep→WorkflowNode in all type hints and log messages
├── observability/
│   ├── logging.py       ← Update "step" in log field names and human-readable messages
│   ├── metrics.py       ← Update "step" in metric key names
│   └── tracker.py       ← Update "step" in tracker field names
├── middleware/
│   └── base.py          ← WorkflowStep→WorkflowNode in type hints
└── plugins/
    └── registry.py      ← WorkflowStep→WorkflowNode in type hints

tests/
├── conftest.py          ← Update imports
├── unit/
│   ├── test_step.py     ← Renamed to test_node.py; update all imports and class names
│   ├── test_workflow.py ← Update imports: NodeResult, NodeContext, NodeStatus, etc.
│   ├── test_engine.py   ← Update imports and node names
│   ├── test_control_flow.py ← Update ConditionalStep→ConditionalNode, true_steps→true_nodes
│   └── middleware/
│       └── test_base.py ← Update WorkflowStep→WorkflowNode
├── integration/
│   ├── test_full_workflow.py       ← Update all step names to node names
│   ├── test_control_flow_integration.py ← Update ConditionalStep→ConditionalNode
│   ├── test_provider_retry.py      ← Update step references
│   └── test_performance.py         ← Update step references
└── unit/
    └── test_import_removal.py      ← NEW: ImportError test (SC-003, Clarification Q3)

examples/
└── complete_workflow_example.py    ← Update all step names to node names

README.md                           ← Update Quick Start code example
CHANGELOG.md                        ← Add [0.2.0] breaking change section with migration table
pyproject.toml                      ← version: "0.1.0" → "0.2.0"
```

**Structure Decision**: Single package (Option 1). Module `step.py` is deleted and replaced by `node.py`. `workflow.py` retains its name as it contains the `Workflow` class (not a step/node type). All other module names are unchanged.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Principle X: Hard removal without deprecation period | Pre-alpha library (v0.x) with explicit "no backward compatibility guarantees until v1.0.0" per README. User explicitly chose hard removal (Clarification Q1). | Soft deprecation keeps "step" names alive for ≥1 release cycle, defeating the conceptual rename goal. Pre-alpha allows this. |
| Principle X: Version bump to 0.2.0 (minor, not major) | semver.org explicitly states: "Major version zero (0.y.z) is for initial development. Anything MAY change at any time." Minor bump signals notable breaking change without implying production readiness. | 0.1.1 (patch) understates impact of a full API rename. 1.0.0 (major) would falsely imply production stability. |
