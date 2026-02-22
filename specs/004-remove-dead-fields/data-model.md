# Data Model: Remove Dead Fields

**Branch**: `004-remove-dead-fields` | **Date**: 2026-02-21

## Changed Type: NodeContext

### Before (v0.2.0)

```
NodeContext
├── workflow_id: str          — Parent workflow UUID
├── step_id: str              — Execution-slot UUID
├── correlation_id: str       — Distributed tracing UUID
├── input_data: dict          — Data passed to this node (default: {})
├── variables: dict           — [DEAD] Template substitution variables (always {})
├── previous_outputs: dict    — Outputs from prior nodes, keyed by node name (default: {})
└── config: Any               — Merged workflow configuration for this execution (default: None)
```

### After (v0.3.0)

```
NodeContext
├── workflow_id: str          — Parent workflow UUID
├── step_id: str              — Execution-slot UUID
├── correlation_id: str       — Distributed tracing UUID
├── input_data: dict          — Data passed to this node (default: {})
├── previous_outputs: dict    — Outputs from prior nodes, keyed by node name (default: {})
└── config: Any               — Merged workflow configuration for this execution (default: None)
```

**Removed**: `variables: dict[str, Any]`

**Reason**: Always constructed as `{}` by the engine; the only read site in `LLMNode` was guarded by an always-false conditional.

---

## Unchanged Types

All other core data-model types are confirmed clean (see `research.md` — audit findings):

- `NodeResult` — all fields actively used
- `WorkflowMetrics` — all fields actively used
- `WorkflowResult` — all fields actively used
- `WorkflowConfig` — all fields actively used

---

## LLMNode Internal Change

The internal model-resolution logic in `LLMNode.execute()` is simplified:

### Before
```python
model = (cfg.model if cfg and cfg.model else None) or (
    context.variables.get("_framework_config", {}).get("default_model", "gpt-4o-mini")
    if isinstance(context.variables.get("_framework_config"), dict)
    else "gpt-4o-mini"
)
```

### After
```python
model = (cfg.model if cfg and cfg.model else None) or "gpt-4o-mini"
```

Runtime behaviour is identical (the removed branch was always unreachable).

---

## Version

| File | Before | After |
|------|--------|-------|
| `src/generative_ai_workflow/__init__.py` | `"0.2.0"` | `"0.3.0"` |
| `pyproject.toml` | `"0.2.0"` | `"0.3.0"` |
