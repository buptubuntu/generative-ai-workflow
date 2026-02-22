# Research: Remove Dead Fields from NodeContext

**Branch**: `004-remove-dead-fields` | **Date**: 2026-02-21

## Summary

This is a pure code cleanup feature. No external research is required — the analysis is based entirely on static inspection of the existing codebase.

---

## Decision 1: Is `variables` genuinely dead?

**Decision**: Yes — `variables` is a dead field and should be removed.

**Evidence**:

| Site | File | Line | Nature |
|------|------|------|--------|
| Field declaration | `workflow.py` | 97 | Always `{}` — default factory, never overridden |
| Construction site | `engine.py` | 176 | Hardcoded `variables={}` — never populated from workflow input or config |
| Only read site | `node.py` | 166–167 | Guarded by `isinstance(context.variables.get("_framework_config"), dict)` — always `False` since `variables` is always `{}` |

**Conclusion**: The `_framework_config` lookup via `context.variables` is structurally unreachable. Removing the field simplifies `NodeContext` to contain only fields the engine actively populates and nodes actively consume.

**Alternatives considered**:
- *Populate `variables` from workflow input*: Rejected — `previous_outputs` and `input_data` already serve this purpose.
- *Keep field and document as extension point*: Rejected — no design document specifies this intent; leaving it creates misleading API surface for a pre-alpha library.

---

## Decision 2: What replaces the `context.variables` model fallback in `LLMNode`?

**Decision**: Remove the two-line conditional entirely. Replace with the direct `"gpt-4o-mini"` literal already used as the else branch.

**Rationale**: The current code is:

```python
model = (cfg.model if cfg and cfg.model else None) or (
    context.variables.get("_framework_config", {}).get("default_model", "gpt-4o-mini")
    if isinstance(context.variables.get("_framework_config"), dict)
    else "gpt-4o-mini"
)
```

Since `context.variables` is always `{}`, the `isinstance(...)` check is always `False`, so `model` always resolves to `cfg.model` (if set) or `"gpt-4o-mini"`. The simplified form is:

```python
model = (cfg.model if cfg and cfg.model else None) or "gpt-4o-mini"
```

This is strictly equivalent to the current runtime behavior.

**Alternatives considered**:
- *Introduce a `default_model` field on `WorkflowConfig`*: Out of scope for this cleanup; `WorkflowConfig.model` already serves this role.

---

## Decision 3: Version bump

**Decision**: Bump `__version__` from `"0.2.0"` → `"0.3.0"` (patch-level semantic change within pre-alpha).

**Rationale**: Removing a public field from a public class is a breaking change under semantic versioning. Although the package is pre-alpha (v0.x) with no backward-compatibility guarantees, the project follows semver conventions for CHANGELOG and version tracking. A MINOR bump to 0.3.0 is appropriate — the change is small and localized.

---

## Decision 4: Scope of the dead-field audit (US2)

**Decision**: Audit `NodeContext`, `NodeResult`, `WorkflowMetrics`, `WorkflowResult`, and `WorkflowConfig`. Conclude that `variables` is the only dead field in these types.

**Findings**:

| Type | Fields | Dead fields found |
|------|--------|------------------|
| `NodeContext` | `workflow_id`, `step_id`, `correlation_id`, `input_data`, `variables`, `previous_outputs`, `config` | `variables` only |
| `NodeResult` | `step_id`, `status`, `output`, `error`, `duration_ms`, `token_usage` | None |
| `WorkflowMetrics` | `total_duration_ms`, `step_durations`, `token_usage_total`, `step_token_usage`, `steps_completed`, `steps_failed`, `steps_skipped` | None |
| `WorkflowResult` | `workflow_id`, `correlation_id`, `status`, `output`, `error`, `metrics`, `created_at`, `completed_at` | None |
| `WorkflowConfig` | `provider`, `model`, `temperature`, `max_tokens`, `max_iterations`, `max_nesting_depth` | None |

**Note on `step_id` naming**: `NodeContext.step_id` and `NodeResult.step_id` use the legacy name "step" internally but are actively populated and read. Renaming these internal UUIDs is out of scope for this cleanup (they are internal identifiers, not user-facing API surface).
