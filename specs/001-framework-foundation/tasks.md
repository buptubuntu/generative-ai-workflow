# Tasks: Framework Foundation

**Input**: Design documents from `/specs/001-framework-foundation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included — AI-specific testing strategy (fixture-based, semantic assertions, cost budgets per Principles VI & VII).

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Constitution Compliance**: All tasks aligned with `.specify/memory/constitution.md` (v1.4.1).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: User story this task belongs to (US1/US2/US3)
- Exact file paths included in all task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — greenfield Python library scaffold

- [x] T001 Create full directory structure: `src/generative_ai_workflow/` with all subdirectories (`providers/`, `plugins/`, `middleware/`, `observability/`, `_internal/`) and `tests/` tree per plan.md
- [x] T002 Create `pyproject.toml` with hatchling build backend, all runtime deps (`openai>=1.0`, `pydantic>=2.0`, `pydantic-settings>=2.0`, `structlog>=24.0`, `tenacity>=8.0`) and dev deps (`pytest>=8.0`, `pytest-asyncio>=0.24`, `respx>=0.21`, `vcrpy>=6.0`)
- [x] T003 [P] Create `.env.example` with all `OPENAI_API_KEY` and `GENAI_WORKFLOW_*` env var documentation
- [x] T004 [P] Create `README.md` with project overview and quickstart reference to `specs/001-framework-foundation/quickstart.md`
- [x] T005 [P] Create `CHANGELOG.md` with `[Unreleased]` section skeleton (Principle X)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, config, logging, and test infrastructure — MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create exception hierarchy in `src/generative_ai_workflow/exceptions.py`: `FrameworkError`, `ProviderError`, `ProviderAuthError`, `StepError`, `WorkflowError`, `PluginError`, `PluginNotFoundError`, `PluginRegistrationError`, `AbortError`, `ConfigurationError`
- [x] T007 [P] Create `FrameworkConfig` in `src/generative_ai_workflow/config.py` using `pydantic-settings` `BaseSettings` with all env vars (`OPENAI_API_KEY`, all `GENAI_WORKFLOW_*` vars), startup validation with clear error messages, and sensible defaults per data-model.md (FR-019, FR-020, FR-021, FR-022, FR-028)
- [x] T008 [P] Create core pydantic models in `src/generative_ai_workflow/providers/base.py`: `TokenUsage`, `LLMRequest` (with defaults: model=`gpt-4o-mini`, temperature=0.7, max_tokens=1024), `LLMResponse` (FR-013)
- [x] T009 [P] Create `WorkflowStatus` and `StepStatus` enums, `StepContext`, `StepResult`, `WorkflowResult`, `ExecutionMetrics` pydantic models in `src/generative_ai_workflow/workflow.py` with all state transition values per data-model.md
- [x] T010 Configure structlog with JSON renderer (orjson) in `src/generative_ai_workflow/observability/logging.py`: JSON output, automatic API key redaction processor, log level from config (FR-015, FR-027, Principle IV)
- [x] T011 Configure pytest in `pyproject.toml` `[tool.pytest.ini_options]`: asyncio_mode=`auto`, testpaths, markers for `integration` and `cost_budget`
- [x] T012 [P] Create `tests/conftest.py` with shared fixtures: `framework_config` (test env), `mock_provider` fixture returning `MockLLMProvider` instance

---

## Phase 3: User Story 1 — Execute Simple LLM Workflow (P1)

**Story Goal**: User can define and execute a multi-step LLM workflow in ≤15 lines of code (sync or async)

**Independent Test**: Execute a 2-step workflow (prompt → LLM → response) end-to-end using MockLLMProvider, verify WorkflowResult.status == "completed" and output matches expected response

- [x] T013 Create `LLMProvider` ABC in `src/generative_ai_workflow/providers/base.py` with `complete_async()` abstract method, default `complete()` sync wrapper, and `initialize()`/`cleanup()` lifecycle hooks (FR-010, FR-024, Principle I, XI)
- [x] T014 [P] [US1] Create `WorkflowStep` ABC in `src/generative_ai_workflow/step.py` with `execute_async()` abstract method, `execute()` sync wrapper, `name` and `is_critical` attributes (FR-001, FR-002, Principle I)
- [x] T015 [US1] Create tenacity retry configuration in `src/generative_ai_workflow/_internal/retry.py`: exponential backoff, max 3 attempts (configurable), retryable errors (429/5xx/timeout), non-retryable (401/403/400) (FR-012)
- [x] T016 [US1] Create `OpenAIProvider` in `src/generative_ai_workflow/providers/openai.py` using `AsyncOpenAI` context manager with tenacity retry, capturing `TokenUsage` from API response, logging model/params/latency/rate-limit headers (FR-009, FR-013, Principle IV AI-specific)
- [x] T017 [P] [US1] Create `MockLLMProvider` in `src/generative_ai_workflow/providers/mock.py`: configurable canned responses dict, token usage simulation, supports both sync and async (FR-031)
- [x] T018 [US1] Create `PluginRegistry` in `src/generative_ai_workflow/plugins/registry.py` with `register_provider()`, `get_provider()`, `list_providers()`, validate at registration time, pre-register `openai` provider (FR-023, Principle XI)
- [x] T019 [US1] Implement `LLMStep` in `src/generative_ai_workflow/step.py`: prompt template with `{variable}` substitution using `str.format_map()`, calls LLMProvider, stores token usage in StepResult (FR-001, FR-003, FR-004)
- [x] T020 [P] [US1] Implement `TransformStep` in `src/generative_ai_workflow/step.py`: callable-based data transformation between steps, passes output to next step context (FR-003)
- [x] T021 [US1] Create `Workflow` class in `src/generative_ai_workflow/workflow.py`: accepts `steps: list[WorkflowStep]`, `name`, `config`; generates workflow_id (UUID); exposes `execute_async()` and `execute()` signatures per contracts/interfaces.py (FR-001, FR-006)
- [x] T022 [US1] Create `_internal/async_utils.py` with safe sync-from-async bridge (handles existing event loop detection) for `execute()` sync wrapper
- [x] T023 [US1] Implement `WorkflowEngine` async execution in `src/generative_ai_workflow/engine.py`: sequential step execution, StepContext data passing, step-level error handling with attribution, WorkflowStatus transitions (FR-002, FR-003, FR-005, FR-006, FR-014)
- [x] T024 [US1] Implement `WorkflowEngine` sync execution with optional timeout in `src/generative_ai_workflow/engine.py`: blocking wrapper, timeout terminates and returns TIMEOUT status with execution state, thread-safe (FR-006, FR-007)
- [x] T025 [US1] Implement graceful async cancellation in `src/generative_ai_workflow/engine.py`: cancel() on asyncio Task, CANCELLED terminal state with final metrics (FR-008)
- [x] T026 [US1] Export complete public API in `src/generative_ai_workflow/__init__.py`: `Workflow`, `WorkflowEngine`, `WorkflowStep`, `LLMStep`, `TransformStep`, `LLMProvider`, `PluginRegistry`, `FrameworkConfig`, all exception types
- [x] T027 [P] [US1] Write unit tests in `tests/unit/test_workflow.py`: variable substitution, step sequencing, data passing between steps, error attribution (deterministic, uses MockLLMProvider)
- [x] T028 [P] [US1] Write unit tests in `tests/unit/test_engine.py`: async/sync execution, timeout behavior, cancellation, step failure handling (MockLLMProvider, no real API)
- [x] T029 [P] [US1] Write unit tests in `tests/unit/providers/test_openai_provider.py`: respx mocks for OpenAI httpx calls, retry behavior, token usage extraction
- [x] T030 [P] [US1] Write unit tests in `tests/unit/test_config.py`: env var loading, startup validation errors, default values

---

## Phase 4: User Story 2 — Observe Workflow Execution (P2)

**Story Goal**: User can query token usage and execution metrics after workflow completes

**Independent Test**: Execute workflow, verify WorkflowResult.metrics contains per-step token counts, durations, and total aggregates accessible via API

- [x] T031 [US2] Create `TokenUsageTracker` in `src/generative_ai_workflow/observability/tracker.py`: accumulates per-step and total TokenUsage, provides query API (FR-011, FR-016, Principle IV)
- [x] T032 [US2] Implement `ExecutionMetrics` collection in `src/generative_ai_workflow/observability/metrics.py`: tracks step start/end times, calculates durations, aggregates token counts (FR-017)
- [x] T033 [P] [US2] Add correlation ID (UUID) generation and propagation through `StepContext` in WorkflowEngine execution pipeline (FR-018)
- [x] T034 [US2] Implement workflow state transition logging with structlog in WorkflowEngine: log all state transitions (PENDING→RUNNING→COMPLETED/FAILED/CANCELLED/TIMEOUT) with correlation_id, workflow_id, duration_ms (FR-014, FR-015)
- [x] T035 [P] [US2] Add LLM interaction metadata logging in `OpenAIProvider`: model name, temperature, max_tokens, latency_ms, finish_reason, rate-limit headers from httpx response (Principle IV AI-specific)
- [x] T036 [US2] Integrate `TokenUsageTracker` into WorkflowEngine: capture usage after each LLM step, aggregate in ExecutionMetrics, expose in WorkflowResult.metrics (FR-011, FR-016)
- [x] T037 [P] [US2] Write unit tests in `tests/unit/observability/test_token_tracker.py`: accumulation, per-step queries, total aggregation
- [x] T038 [P] [US2] Write unit tests in `tests/unit/observability/test_metrics.py`: duration tracking, step timing, metrics aggregation
- [x] T039 [P] [US2] Write unit tests in `tests/unit/observability/test_logging.py`: JSON output format, correlation ID presence, API key redaction

---

## Phase 5: User Story 3 — Extend Framework with Custom Components (P3)

**Story Goal**: User can register custom LLM provider and use it in workflows without modifying framework source

**Independent Test**: Implement a custom provider extending `LLMProvider`, register it via `PluginRegistry`, execute a workflow using it, verify plugin lifecycle (init/execute/cleanup) and isolation (failure doesn't crash framework)

- [x] T040 [US3] Create `Middleware` ABC in `src/generative_ai_workflow/middleware/base.py`: all lifecycle hook methods with default no-op implementations (`before_llm_call`, `after_llm_call`, `on_workflow_start`, `on_workflow_end`, `on_step_error`) per contracts/interfaces.py (FR-026, Principle XI)
- [x] T041 [US3] Implement middleware pipeline in `WorkflowEngine`: deterministic FIFO execution order, hooks can modify data (return modified object) or short-circuit (raise AbortError), hook errors logged with context and continue for non-critical hooks (FR-026, Principle XI)
- [x] T042 [US3] Add `WorkflowEngine.use()` for middleware registration with method chaining support
- [x] T043 [P] [US3] Implement plugin isolation in WorkflowEngine: catch step exceptions per `is_critical` flag, log with plugin attribution (class name + module), continue or abort per criticality (FR-025, Principle XI)
- [x] T044 [P] [US3] Implement plugin lifecycle management in WorkflowEngine: call `provider.initialize()` before first use, `provider.cleanup()` on shutdown/context exit (Principle XI)
- [x] T045 [P] [US3] Create respx cassette fixtures in `tests/fixtures/llm_responses/` with sample OpenAI API response YAML for deterministic replay (FR-032, Principle VI AI-specific)
- [x] T046 [US3] Create `cost_tracker` fixture in `tests/conftest.py`: tracks token usage and enforces max cost budget per test ($0.10) and suite ($2.00) (FR-033, Principle VII)
- [x] T047 [P] [US3] Write unit tests in `tests/unit/middleware/test_base.py`: hook execution order, data modification, error handling, short-circuit behavior
- [x] T048 [US3] Write integration test in `tests/integration/test_full_workflow.py`: full 3-step workflow with real OpenAI fixture, cost-budgeted, semantic assertions on output (Principle VII)
- [x] T049 [P] [US3] Write integration test in `tests/integration/test_provider_retry.py`: retry behavior with respx-simulated 429 responses, backoff verification

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: YAML config, security utilities, input validation, and final validation

- [x] T050 [P] Add YAML config file loading to `FrameworkConfig` in `src/generative_ai_workflow/config.py`: optional `config.yaml` for domain settings, merged with env vars (env vars take precedence) (FR-019a)
- [x] T051 [P] Implement PII detection utilities in `src/generative_ai_workflow/providers/base.py`: regex patterns for common PII (email, SSN, credit card, phone), `detect_pii()` helper function (FR-030)
- [x] T052 Implement input validation in `src/generative_ai_workflow/workflow.py` and `src/generative_ai_workflow/providers/base.py`: validate non-empty steps, valid step names, no duplicate step names; detect and reject basic injection patterns in prompt inputs (keywords: "ignore previous", "reveal", "system prompt") per FR-029
- [x] T053 [P] Add `pyyaml` dependency to `pyproject.toml` and import guard for YAML config loading (needed for FR-019a)
- [x] T054 [P] Final review: verify all 34 FRs have implementation coverage; update `__init__.py` with any missing exports
- [x] T055 Validate ≤20% framework overhead at 100 concurrent async workflows: create `tests/integration/test_performance.py` using `asyncio.gather` with 100 tasks; assert p99 framework overhead ≤20% vs single-workflow baseline (exclude LLM call time, use MockLLMProvider) (SC-008)
- [x] T056 Create `.github/workflows/ci.yml` with tiered execution: on-commit (unit tests only, no LLM), on-PR (smoke integration with `gpt-4o-mini`, budget $0.50), nightly (full suite, budget $2.00) (Principle VII)
- [x] T057 [P] Create `.pre-commit-config.yaml` with hooks: `ruff` linting, `black` formatting, `mypy` type checking (constitution §Enforcement)

---

## Dependencies

```
Phase 1 (Setup)
    └─► Phase 2 (Foundational)
            └─► Phase 3 (US1 - Execute Workflow)  [MUST complete first]
                    └─► Phase 4 (US2 - Observability)
                    └─► Phase 5 (US3 - Extensibility)
                            └─► Phase 6 (Polish)
```

**Within Phase 3 dependencies:**
```
T013 (LLMProvider ABC) → T016 (OpenAIProvider), T017 (MockLLMProvider)
T014 (WorkflowStep ABC) → T019 (LLMStep), T020 (TransformStep)
T015 (retry config) → T016 (OpenAIProvider)
T018 (PluginRegistry) → T016 (OpenAIProvider)
T021 (Workflow class) → T019, T020
T022 (async_utils) → T021 (Workflow)
T023 (Engine async) → T021, T022
T024 (Engine sync) → T023
T025 (cancellation) → T023
T026 (__init__.py) → all above
```

---

## Parallel Execution Examples

### Phase 2 parallelization:
```
T006 (exceptions) ─┐
T007 (config)      ├─ all independent, different files
T008 (models)      │
T009 (enums/result)│
T010 (logging)     │
T011 (pytest cfg)  │
T012 (conftest)    ┘
```

### Phase 3 parallelization (after T013, T014):
```
T016 (OpenAIProvider) ─┐
T017 (MockProvider)    ├─ parallel (both implement T013's ABC)
                       │
T019 (LLMStep)    ─────┤
T020 (TransformStep) ──┘ parallel (both implement T014's ABC)

T027-T030 (unit tests) ─ all parallel after implementation complete
```

### Phase 4 parallelization:
```
T031 (TokenUsageTracker) ─┐
T032 (ExecutionMetrics)   ├─ parallel
T033 (correlation IDs)    │
T035 (LLM metadata log)   ┘
```

---

## Implementation Strategy

**MVP Scope (deliver first)**: Phase 1 + Phase 2 + Phase 3 (US1)
- After Phase 3: Users can execute async/sync LLM workflows with OpenAI, variable substitution, error handling, timeout, and cancellation
- Tests verify all User Story 1 acceptance scenarios

**Increment 2**: Phase 4 (US2 — Observability)
- After Phase 4: Full token tracking, metrics API, structured logging with correlation IDs

**Increment 3**: Phase 5 (US3 — Extensibility) + Phase 6 (Polish)
- After Phase 5: Complete plugin system, middleware hooks, testing utilities
- Phase 6 completes YAML config, security utilities, performance validation

---

## Summary

| Phase | Tasks | Parallel Opportunities | Story |
|-------|-------|----------------------|-------|
| 1 Setup | T001-T005 | T003, T004, T005 | — |
| 2 Foundational | T006-T012 | T007-T012 | — |
| 3 US1 Execute Workflow | T013-T030 | T014,T017,T020,T027-T030 | US1 |
| 4 US2 Observability | T031-T039 | T033,T035,T037-T039 | US2 |
| 5 US3 Extensibility | T040-T049 | T043-T045,T047,T049 | US3 |
| 6 Polish | T050-T057 | T050,T051,T053,T054,T057 | — |
| **Total** | **57 tasks** | **28 parallelizable** | |
