# Data Model: Framework Foundation

**Date**: 2026-02-08
**Feature**: 001-framework-foundation

## Entities

### TokenUsage

Tracks token consumption for a single LLM operation.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| prompt_tokens | int | ≥ 0 | Tokens in the input prompt |
| completion_tokens | int | ≥ 0 | Tokens in the generated response |
| total_tokens | int | = prompt + completion | Derived; validated |
| model | str | non-empty | Model name (e.g., `gpt-4o-mini`) |
| provider | str | non-empty | Provider name (e.g., `openai`) |

---

### LLMRequest

Input to any LLM provider call.

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| prompt | str | required | non-empty |
| model | str | `gpt-4o-mini` | non-empty |
| temperature | float | 0.7 | 0.0–2.0 |
| max_tokens | int | 1024 | 1–128000 |
| system_prompt | str \| None | None | optional |
| extra_params | dict | {} | provider-specific passthrough |

---

### LLMResponse

Output from any LLM provider call.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| content | str | non-empty | Generated text |
| model | str | non-empty | Actual model used (may differ from request) |
| usage | TokenUsage | required | Token consumption |
| latency_ms | float | ≥ 0 | Total provider round-trip time |
| finish_reason | str | e.g., `stop`, `length`, `error` | Provider-reported completion reason |

---

### WorkflowStatus

Enum representing lifecycle states of a workflow execution.

```
PENDING → RUNNING → COMPLETED
                  → FAILED
                  → CANCELLED
                  → TIMEOUT
```

| Value | Terminal? | Description |
|-------|-----------|-------------|
| PENDING | No | Created, not yet started |
| RUNNING | No | Actively executing |
| COMPLETED | Yes | All steps finished successfully |
| FAILED | Yes | One or more steps failed unrecoverably |
| CANCELLED | Yes | Execution cancelled by user |
| TIMEOUT | Yes | Synchronous timeout exceeded |

---

### StepStatus

Enum representing lifecycle states of a single workflow step.

| Value | Terminal? | Description |
|-------|-----------|-------------|
| PENDING | No | Not yet executed |
| RUNNING | No | Currently executing |
| COMPLETED | Yes | Executed successfully |
| FAILED | Yes | Execution failed |
| SKIPPED | Yes | Skipped (non-critical step after prior failure) |

---

### StepContext

Data flowing through the workflow pipeline between steps.

| Field | Type | Notes |
|-------|------|-------|
| workflow_id | str (UUID) | Parent workflow identifier |
| step_id | str (UUID) | Current step identifier |
| correlation_id | str (UUID) | Tracing correlation ID |
| input_data | dict | Data passed to this step |
| variables | dict | Template substitution variables |
| previous_outputs | dict[str, Any] | Outputs from prior steps, keyed by step name |
| config | WorkflowConfig | Merged configuration for this execution |

---

### StepResult

Output from a single workflow step.

| Field | Type | Notes |
|-------|------|-------|
| step_id | str (UUID) | Step identifier |
| status | StepStatus | Execution outcome |
| output | dict \| None | Step output data |
| error | str \| None | Error message if failed |
| duration_ms | float | Step execution time |
| token_usage | TokenUsage \| None | If step involved LLM call |

---

### ExecutionMetrics

Aggregated performance and observability data for a complete workflow execution.

| Field | Type | Notes |
|-------|------|-------|
| total_duration_ms | float | Wall-clock time from start to end |
| step_durations | dict[str, float] | step_id → duration_ms |
| token_usage_total | TokenUsage \| None | Aggregated across all LLM steps |
| step_token_usage | dict[str, TokenUsage] | step_id → usage |
| steps_completed | int | Count of COMPLETED steps |
| steps_failed | int | Count of FAILED steps |
| steps_skipped | int | Count of SKIPPED steps |

---

### WorkflowResult

Final result returned to the caller after workflow execution.

| Field | Type | Notes |
|-------|------|-------|
| workflow_id | str (UUID) | Workflow identifier |
| correlation_id | str (UUID) | Tracing correlation ID |
| status | WorkflowStatus | Terminal status |
| output | dict \| None | Final step output |
| error | str \| None | Error message if failed/timeout |
| metrics | ExecutionMetrics | Full observability data |
| created_at | datetime | UTC timestamp |
| completed_at | datetime \| None | UTC timestamp (None if still running) |

---

### FrameworkConfig

Runtime configuration loaded from environment variables and defaults.

| Field | Type | Default | Env Var | Notes |
|-------|------|---------|---------|-------|
| openai_api_key | str | `""` | `OPENAI_API_KEY` | Validated non-empty at startup if OpenAI used |
| default_model | str | `gpt-4o-mini` | `GENAI_WORKFLOW_DEFAULT_MODEL` | |
| default_temperature | float | 0.7 | `GENAI_WORKFLOW_DEFAULT_TEMPERATURE` | |
| default_max_tokens | int | 1024 | `GENAI_WORKFLOW_DEFAULT_MAX_TOKENS` | |
| default_timeout_seconds | float \| None | None | `GENAI_WORKFLOW_DEFAULT_TIMEOUT` | None = no timeout |
| default_execution_mode | str | `async` | `GENAI_WORKFLOW_DEFAULT_MODE` | `async` or `sync` |
| max_retry_attempts | int | 3 | `GENAI_WORKFLOW_MAX_RETRIES` | |
| retry_backoff_factor | float | 2.0 | `GENAI_WORKFLOW_RETRY_BACKOFF` | |
| log_level | str | `INFO` | `GENAI_WORKFLOW_LOG_LEVEL` | |
| log_prompts | bool | False | `GENAI_WORKFLOW_LOG_PROMPTS` | opt-in |

Validation: All values validated at instantiation time with clear error messages (Pydantic validators).

---

## Relationships

```
Workflow ──[has many]──► WorkflowStep
Workflow ──[produces]──► WorkflowResult
WorkflowResult ──[contains]──► ExecutionMetrics
ExecutionMetrics ──[aggregates]──► TokenUsage (per-step + total)
WorkflowStep ──[produces]──► StepResult
StepResult ──[may contain]──► TokenUsage
LLMStep ──[uses]──► LLMProvider
LLMProvider ──[takes]──► LLMRequest
LLMProvider ──[returns]──► LLMResponse
LLMResponse ──[contains]──► TokenUsage
PluginRegistry ──[manages]──► LLMProvider registrations
WorkflowEngine ──[executes]──► Workflow
WorkflowEngine ──[applies]──► Middleware hooks
```

---

## Key Design Notes

- All IDs are UUIDs generated at creation time
- All timestamps are UTC (timezone-aware)
- Token counts are authoritative from provider response, not estimated
- `StepContext.previous_outputs` enables data passing between steps (FR-003)
- Variable substitution (FR-004) uses `StepContext.variables` with template strings
