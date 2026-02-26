# Quickstart: Prometheus Observability Middleware

**Feature**: 001-prometheus-middleware | **Date**: 2026-02-26

## Install

```bash
pip install 'generative-ai-workflow[observability]'
```

## 30-Second Setup

```python
from generative_ai_workflow import WorkflowEngine
from generative_ai_workflow.middleware.prometheus import PrometheusMiddleware
from prometheus_client import start_http_server

# 1. Create middleware
metrics = PrometheusMiddleware()

# 2. Attach to engine
engine = WorkflowEngine()
engine.use(metrics)

# 3. Expose /metrics endpoint (your application's responsibility)
start_http_server(8000)  # browse http://localhost:8000/metrics

# 4. Run workflows normally — metrics are recorded automatically
result = await engine.run(my_workflow, input_data={...})
```

## What You'll See in Prometheus

After running a workflow, scraping `localhost:8000/metrics` returns:

```
# HELP workflow_duration_seconds Total workflow wall-clock duration
# TYPE workflow_duration_seconds histogram
workflow_duration_seconds_bucket{status="completed",workflow_name="",le="0.005"} 0.0
workflow_duration_seconds_bucket{status="completed",workflow_name="",le="0.5"} 1.0
...
workflow_duration_seconds_count{status="completed",workflow_name=""} 1.0
workflow_duration_seconds_sum{status="completed",workflow_name=""} 0.342

# HELP workflow_total Workflow execution count by terminal status
# TYPE workflow_total counter
workflow_total_total{status="completed",workflow_name=""} 1.0

# HELP workflow_node_duration_seconds Per-node wall-clock duration
# TYPE workflow_node_duration_seconds histogram
workflow_node_duration_seconds_bucket{node="summarise",workflow_name="",le="0.5"} 1.0
...

# HELP workflow_tokens_prompt_total Prompt tokens consumed
# TYPE workflow_tokens_prompt_total counter
workflow_tokens_prompt_total_total{model="gpt-4o",node="summarise",workflow_name=""} 423.0

# HELP workflow_tokens_completion_total Completion tokens consumed
# TYPE workflow_tokens_completion_total counter
workflow_tokens_completion_total_total{model="gpt-4o",node="summarise",workflow_name=""} 87.0
```

## Useful PromQL Queries

```promql
# P95 workflow latency over the last 5 minutes
histogram_quantile(0.95, rate(workflow_duration_seconds_bucket[5m]))

# Workflow error rate
rate(workflow_total_total{status="failed"}[5m])
  / rate(workflow_total_total[5m])

# Total token spend by model (last hour)
increase(workflow_tokens_prompt_total_total[1h])
  + increase(workflow_tokens_completion_total_total[1h])

# Slowest nodes (average duration)
rate(workflow_node_duration_seconds_sum[5m])
  / rate(workflow_node_duration_seconds_count[5m])
```

## Common Patterns

### Named Workflows (recommended)

Set `workflow_name` on your `Workflow` object so metrics are filterable per workflow type:

```python
from generative_ai_workflow import Workflow

workflow = Workflow(name="summarise-article", nodes=[...])
result = await engine.run(workflow, input_data={...})
# → workflow_name="summarise_article" label on all metrics
```

### Isolated Registry (for libraries)

```python
from prometheus_client import CollectorRegistry

registry = CollectorRegistry()
engine.use(PrometheusMiddleware(registry=registry))
# Global registry untouched — safe to embed in larger apps
```

### Multiple Engines (shared metrics)

```python
mw = PrometheusMiddleware()
engine_a.use(mw)
engine_b.use(mw)  # metrics aggregate naturally
```
