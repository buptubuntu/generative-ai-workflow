# Research: Prometheus Observability Middleware

**Feature**: 001-prometheus-middleware | **Date**: 2026-02-26

## Decision 1: Metric Families to Expose

**Decision**: Expose 6 metric families — 2 Histograms and 4 Counters.

| Metric Name (default prefix `workflow`) | Type | Labels | Source |
|---|---|---|---|
| `workflow_duration_seconds` | Histogram | `workflow_name`, `status` | `on_workflow_end` hook → `result.metrics.total_duration_ms` |
| `workflow_total` | Counter | `workflow_name`, `status` | `on_workflow_end` hook → `result.status` |
| `workflow_node_duration_seconds` | Histogram | `workflow_name`, `node` | `on_workflow_end` hook → `result.metrics.step_durations` |
| `workflow_node_errors_total` | Counter | `workflow_name`, `node` | `on_node_error` hook → `node_name` |
| `workflow_tokens_prompt_total` | Counter | `workflow_name`, `node`, `model` | `on_workflow_end` → `result.metrics.step_token_usage` |
| `workflow_tokens_completion_total` | Counter | `workflow_name`, `node`, `model` | `on_workflow_end` → `result.metrics.step_token_usage` |

**Rationale**: These 6 families cover all FR-002–006, FR-011. Histograms for durations (enables p50/p95/p99 PromQL). Counters for events and tokens (rate() queries). All align with the Prometheus data model best practices.

**Alternatives considered**:
- Gauge for durations — rejected; Gauges don't support rate() and are poor for latency distributions.
- Single token counter with `type` label — rejected; split counters (prompt vs completion) are more useful for cost modelling.

---

## Decision 2: Hook Integration Points

**Decision**: Use only `on_workflow_end` and `on_node_error` hooks. Do NOT use `before_llm_call`/`after_llm_call`.

**Rationale**: `WorkflowResult.metrics` (available in `on_workflow_end`) already contains all per-node durations and token usage aggregated by the engine. Using `after_llm_call` would be redundant and risk double-counting. `on_node_error` is the only additional hook needed for the node-error counter, as the engine fires it before `on_workflow_end` when a node fails.

**Source verified**: `engine.py` passes `ctx = {"workflow_id": ..., "correlation_id": ..., "workflow_name": ...}` to all hooks. The `workflow_name` from this context dict satisfies FR-011.

---

## Decision 3: Constructor Signature

**Decision**:

```python
class PrometheusMiddleware(Middleware):
    def __init__(
        self,
        *,
        prefix: str = "workflow",
        registry: CollectorRegistry | None = None,
        buckets: Sequence[float] = DEFAULT_BUCKETS,
        label_sanitiser: Callable[[str], str] | None = None,
    ) -> None:
```

- `prefix`: namespaces all metric names (FR-008)
- `registry`: optional isolated registry (FR-007); `None` → global `REGISTRY`
- `buckets`: configurable histogram boundaries (FR-002); default is `prometheus_client.CONTENT_TYPE_LATEST` — actually `prometheus_client.DEFAULT_BUCKETS` (0.005…10.0 seconds)
- `label_sanitiser`: optional callable replacing default sanitiser (FR-014); default replaces non-`[a-zA-Z0-9_]` chars with `_`

**Keyword-only args** (the `*`) enforce clarity at call sites and prevent positional misuse.

---

## Decision 4: Multi-Engine Double-Registration Safety

**Decision**: Use `prometheus_client`'s `CollectorRegistry` registration deduplication. When sharing a registry across multiple `PrometheusMiddleware` instances (same prefix), the second instantiation would raise `ValueError: Duplicated timeseries`. To prevent this, use `registry.unregister()` guard or, better, pass a shared `PrometheusMiddleware` instance to multiple engines.

**Rationale**: The spec (Edge Cases) states metrics must aggregate without double-registration errors. The simplest safe pattern is to document that callers should share one middleware instance across engines. Internally, we wrap collector registration in a try/except for `ValueError` and log a warning if the same metric is registered twice to the same registry.

---

## Decision 5: Label Sanitiser Implementation

**Decision**: Default sanitiser uses `re.sub(r"[^a-zA-Z0-9_]", "_", value)`. Leading digits are prepended with `_` to comply with Prometheus label name rules.

**Rationale**: Prometheus label values can contain any UTF-8 characters, but label **names** must match `[a-zA-Z_][a-zA-Z0-9_]*`. Our labels are pre-defined by the middleware (not dynamic), so value sanitisation only needs to strip characters that Prometheus exporters may mishandle in time-series selectors. The conservative approach (replace everything non-alphanumeric) ensures compatibility with all Prometheus versions ≥0.16.0.

---

## Decision 6: Optional Dependency Pattern

**Decision**: Guard import with a top-of-file try/except:

```python
try:
    import prometheus_client
except ImportError as exc:
    raise ImportError(
        "prometheus-client is required for PrometheusMiddleware. "
        "Install it with: pip install 'generative-ai-workflow[observability]'"
    ) from exc
```

**Rationale**: Importing the module raises immediately (not lazily) so the error is surfaced at class-definition time, not at first method call. This satisfies FR-009 and gives a clear actionable message.

---

## Decision 7: File Placement

**Decision**: New file `src/generative_ai_workflow/middleware/prometheus.py`. Export `PrometheusMiddleware` from `src/generative_ai_workflow/middleware/__init__.py` under `TYPE_CHECKING` guard to avoid mandatory import of `prometheus_client` at package-level.

**Rationale**: Keeping it in the `middleware/` package is consistent with `base.py`. The `__init__.py` guard means users who don't install the optional dep can still import the rest of the framework without errors.
