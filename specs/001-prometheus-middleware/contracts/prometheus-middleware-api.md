# API Contract: PrometheusMiddleware

**Package**: `generative_ai_workflow.middleware.prometheus`
**Requires**: `prometheus-client >= 0.16.0` (optional extras: `observability`)
**Date**: 2026-02-26

---

## Class: PrometheusMiddleware

```
PrometheusMiddleware(
    *,
    prefix: str = "workflow",
    registry: CollectorRegistry | None = None,
    buckets: Sequence[float] = DEFAULT_BUCKETS,
    label_sanitiser: Callable[[str], str] | None = None,
) -> None
```

Implements `generative_ai_workflow.middleware.base.Middleware`.

### Constructor Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `prefix` | `str` | `"workflow"` | No | Namespace prepended to all metric names. Must be a valid Prometheus metric name prefix. |
| `registry` | `CollectorRegistry \| None` | `None` (→ global) | No | Prometheus registry to register metrics against. Pass a custom `CollectorRegistry` for isolation. |
| `buckets` | `Sequence[float]` | `prometheus_client.DEFAULT_BUCKETS` | No | Histogram bucket boundaries in seconds for duration metrics. |
| `label_sanitiser` | `Callable[[str], str] \| None` | `None` (→ built-in) | No | Callable that transforms raw label values (node names, model names, workflow names) into valid Prometheus label strings. Replaces the default sanitiser entirely. |

### Raises at Import Time

- `ImportError` — if `prometheus-client` is not installed. Message includes install instruction.

### Raises at Construction Time

- `ValueError` — if `prefix` is empty or contains invalid characters.

---

## Inherited Hook Methods

All hooks are `async`. Return values from hooks that return `None` are ignored by the engine.

### on_workflow_start(workflow_id, ctx) → None

No-op. No metrics are recorded at workflow start.

### on_workflow_end(result, ctx) → None

Records:
- `{prefix}_duration_seconds` histogram observation (labels: `workflow_name`, `status`)
- `{prefix}_total` counter increment (labels: `workflow_name`, `status`)
- `{prefix}_node_duration_seconds` histogram observation per node (labels: `workflow_name`, `node`)
- `{prefix}_tokens_prompt_total` counter increment per LLM node (labels: `workflow_name`, `node`, `model`)
- `{prefix}_tokens_completion_total` counter increment per LLM node (labels: `workflow_name`, `node`, `model`)

**Never raises** — all metric errors are caught, logged as warnings via structlog, and swallowed.

| Parameter | Type | Description |
|-----------|------|-------------|
| `result` | `WorkflowResult` | Completed workflow result including metrics |
| `ctx` | `dict[str, Any]` | Engine context containing `workflow_name`, `workflow_id`, `correlation_id` |

### on_node_error(error, node_name, ctx) → None

Records:
- `{prefix}_node_errors_total` counter increment (labels: `workflow_name`, `node`)

**Never raises** — errors caught and logged.

| Parameter | Type | Description |
|-----------|------|-------------|
| `error` | `Exception` | The exception that caused the node failure |
| `node_name` | `str` | Name of the failed node |
| `ctx` | `dict[str, Any]` | Engine context |

---

## Metric Reference

All metric names follow the pattern: `{prefix}_{suffix}`.

| Suffix | Type | Labels | Description |
|--------|------|--------|-------------|
| `duration_seconds` | Histogram | `workflow_name`, `status` | Total workflow wall-clock duration |
| `total` | Counter | `workflow_name`, `status` | Workflow execution count by terminal status |
| `node_duration_seconds` | Histogram | `workflow_name`, `node` | Per-node wall-clock duration |
| `node_errors_total` | Counter | `workflow_name`, `node` | Per-node error count |
| `tokens_prompt_total` | Counter | `workflow_name`, `node`, `model` | Prompt tokens consumed |
| `tokens_completion_total` | Counter | `workflow_name`, `node`, `model` | Completion tokens consumed |

### Label Value Constraints

| Label | Valid Values | Sanitised |
|-------|-------------|-----------|
| `workflow_name` | Any string; empty → `""` | Yes |
| `status` | `completed`, `failed`, `cancelled`, `timeout` | No |
| `node` | Any string from node definition | Yes |
| `model` | Any string from `TokenUsage.model` | Yes |

**Default sanitiser**: replaces `[^a-zA-Z0-9_]` with `_`. Empty result → `"unknown"`.

---

## Usage Examples

### Minimal (global registry)

```python
from generative_ai_workflow import WorkflowEngine
from generative_ai_workflow.middleware.prometheus import PrometheusMiddleware

engine = WorkflowEngine()
engine.use(PrometheusMiddleware())
```

### Custom registry (isolated metrics)

```python
from prometheus_client import CollectorRegistry, generate_latest
from generative_ai_workflow.middleware.prometheus import PrometheusMiddleware

registry = CollectorRegistry()
engine.use(PrometheusMiddleware(registry=registry))

# Expose only this feature's metrics
print(generate_latest(registry))
```

### Custom prefix + buckets

```python
engine.use(PrometheusMiddleware(
    prefix="myapp_llm",
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
))
```

### Shared middleware across multiple engines

```python
mw = PrometheusMiddleware()   # single instance, single set of metric descriptors
engine_a.use(mw)
engine_b.use(mw)              # metrics aggregate across both engines
```

### Custom label sanitiser (hash sensitive names)

```python
import hashlib

def hash_sanitiser(value: str) -> str:
    return "h_" + hashlib.md5(value.encode()).hexdigest()[:8]

engine.use(PrometheusMiddleware(label_sanitiser=hash_sanitiser))
```

---

## Backward Compatibility

- `PrometheusMiddleware` is a new class; no existing public API is modified.
- The `Middleware` base class in `middleware/base.py` is not changed.
- Adding `prometheus-client` to `[observability]` extras is additive; no existing extras groups are modified.
- This feature targets a minor version bump (e.g., `0.3.0` → `0.4.0` or `0.5.0`).
