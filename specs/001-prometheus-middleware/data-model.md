# Data Model: Prometheus Observability Middleware

**Feature**: 001-prometheus-middleware | **Date**: 2026-02-26

## Entities

### PrometheusMiddleware

The top-level class. Owns all metric descriptor objects and the registry reference.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `_prefix` | `str` | `"workflow"` | Namespace prepended to all metric names |
| `_registry` | `CollectorRegistry` | global `REGISTRY` | Prometheus registry owning all descriptors |
| `_label_sanitiser` | `Callable[[str], str]` | built-in char sanitiser | Transforms raw label values to valid Prometheus strings |
| `_workflow_duration` | `Histogram` | — | Records total workflow wall-clock time in seconds |
| `_workflow_total` | `Counter` | — | Counts completed workflow executions by status |
| `_node_duration` | `Histogram` | — | Records per-node wall-clock time in seconds |
| `_node_errors` | `Counter` | — | Counts node-level errors by node name |
| `_tokens_prompt` | `Counter` | — | Counts prompt tokens consumed by node and model |
| `_tokens_completion` | `Counter` | — | Counts completion tokens consumed by node and model |

**Lifecycle**: Metrics are registered to the registry at `__init__` time. All six metric objects are initialised once and reused for the lifetime of the middleware instance.

---

### Metric Families

#### workflow_duration_seconds (Histogram)

- **Full name**: `{prefix}_duration_seconds`
- **Labels**: `workflow_name`, `status`
- **Buckets**: configurable; default Prometheus buckets (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10 seconds)
- **Source**: `result.metrics.total_duration_ms / 1000` in `on_workflow_end`
- **Status values**: `completed`, `failed`, `cancelled`, `timeout`

#### workflow_total (Counter)

- **Full name**: `{prefix}_total`
- **Labels**: `workflow_name`, `status`
- **Source**: `result.status.value` in `on_workflow_end`
- **Status values**: same as above

#### workflow_node_duration_seconds (Histogram)

- **Full name**: `{prefix}_node_duration_seconds`
- **Labels**: `workflow_name`, `node`
- **Buckets**: same configurable buckets as workflow duration
- **Source**: `result.metrics.step_durations` dict (node_name → ms) in `on_workflow_end`
- **Note**: Only nodes that executed and have a recorded duration emit a data point

#### workflow_node_errors_total (Counter)

- **Full name**: `{prefix}_node_errors_total`
- **Labels**: `workflow_name`, `node`
- **Source**: `node_name` parameter in `on_node_error` hook

#### workflow_tokens_prompt_total (Counter)

- **Full name**: `{prefix}_tokens_prompt_total`
- **Labels**: `workflow_name`, `node`, `model`
- **Source**: `result.metrics.step_token_usage[node].prompt_tokens` in `on_workflow_end`
- **Note**: Only emitted when a node has token usage recorded (LLM nodes only)

#### workflow_tokens_completion_total (Counter)

- **Full name**: `{prefix}_tokens_completion_total`
- **Labels**: `workflow_name`, `node`, `model`
- **Source**: `result.metrics.step_token_usage[node].completion_tokens` in `on_workflow_end`
- **Note**: Same condition as prompt counter

---

### Label Definitions

| Label | Scope | Raw Source | Sanitised |
|-------|-------|------------|-----------|
| `workflow_name` | workflow-level metrics | `ctx["workflow_name"]` from engine | Yes |
| `status` | workflow-level metrics | `result.status.value` (enum string) | No (already safe) |
| `node` | node-level metrics | `node_name` string | Yes |
| `model` | token metrics | `TokenUsage.model` string | Yes |

**Default sanitiser rule**: `re.sub(r"[^a-zA-Z0-9_]", "_", value)` — replaces all non-alphanumeric/underscore chars with `_`. Empty result defaults to `"unknown"`.

---

## State Transitions

The middleware is stateless between workflow executions — all Prometheus metric state lives inside the `prometheus_client` library's internal counters and histograms. The middleware only holds references to those objects.

```
PrometheusMiddleware.__init__()
    → registers 6 metric descriptors to registry
    → ready to receive hook calls

on_workflow_start() [no-op — no metrics at start]

on_node_error(error, node_name, ctx)
    → sanitise node_name label
    → _node_errors.labels(...).inc()

on_workflow_end(result, ctx)
    → sanitise workflow_name from ctx
    → record _workflow_duration
    → inc _workflow_total
    → for each node in step_durations: record _node_duration
    → for each node in step_token_usage: inc _tokens_prompt + _tokens_completion
```

---

## External Data Dependencies

| Data | Source Object | Field Path |
|------|--------------|------------|
| Workflow total duration (ms) | `WorkflowResult.metrics` | `.total_duration_ms` |
| Per-node durations (ms) | `WorkflowResult.metrics` | `.step_durations: dict[str, float]` |
| Per-node token usage | `WorkflowResult.metrics` | `.step_token_usage: dict[str, TokenUsage]` |
| Workflow status | `WorkflowResult` | `.status: WorkflowStatus` (enum) |
| Workflow name | Middleware context dict | `ctx["workflow_name"]: str` |
| Node name (errors) | `on_node_error` parameter | `node_name: str` |
| Model name (tokens) | `TokenUsage` | `.model: str` |
