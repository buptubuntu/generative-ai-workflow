# Implementation Plan: Framework Foundation

**Branch**: `001-framework-foundation` | **Date**: 2026-02-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-framework-foundation/spec.md`

## Summary

Build the foundational Python library (`generative_ai_workflow`) for a generic AI workflow framework. The framework enables users to define and execute multi-step LLM workflows with built-in OpenAI integration, async/sync execution modes, structured observability, a plugin architecture for custom providers and middleware, and AI-specific testing utilities.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `openai` ≥1.0 — Built-in OpenAI provider (AsyncOpenAI client)
- `pydantic` ≥2.0 — Data validation and typed models
- `pydantic-settings` ≥2.0 — Environment-variable-based configuration
- `structlog` ≥24.0 — Structured JSON logging with context binding
- `tenacity` ≥8.0 — Async retry with exponential backoff

**Dev/Test Dependencies**:
- `pytest` ≥8.0
- `pytest-asyncio` ≥0.24 — Async test support
- `respx` ≥0.21 — httpx request mocking for OpenAI SDK tests
- `vcrpy` ≥6.0 — Record/replay cassettes for integration tests

**Storage**: N/A (library, no persistence layer)
**Testing**: pytest + pytest-asyncio + respx + vcrpy
**Target Platform**: Python 3.11+ on Linux/macOS (cross-platform library)
**Project Type**: Single Python library package (`src/` layout)
**Performance Goals**: ≤20% framework overhead vs single workflow at 100 concurrent async workflows (SC-008)
**Constraints**:
- v0.x pre-stability: no backward compatibility guarantees until v1.0.0
- v1 security scope: internal/trusted environments only (basic FR-027–030)
- No mandatory external services beyond OpenAI API
**Scale/Scope**: Foundation release; ~10 public modules, ~2000 LOC target

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` (current version: v1.4.1).

### ✅ Principle I: Interface-First Design
- [x] Public APIs designed with clear interfaces (LLMProvider, WorkflowStep, Middleware ABCs)
- [x] Implementation details hidden behind contracts (OpenAIProvider internals hidden)
- [x] Interface contracts documented in `contracts/interfaces.py` before implementation
- [x] Breaking interface changes require major version increment (enforced by v0.x policy)

### ✅ Principle II: Documented Public Interfaces
- [x] All public APIs have docstrings with: purpose, parameters, returns, exceptions
- [x] At least one usage example per non-trivial interface (see contracts/interfaces.py)
- [x] Type annotations included throughout (Python 3.11 type hints)
- [x] Performance characteristics documented for critical paths (async execution patterns)

### ✅ Principle III: SOLID Principles
- [x] Single Responsibility: each module has one concern (providers/, middleware/, observability/)
- [x] Open/Closed: new providers/steps extend via plugin system, no framework modification needed
- [x] Dependencies injected via interfaces (WorkflowEngine takes config; providers injected)
- [x] Violations justified in Complexity Tracking below

### ✅ Principle IV: Observability (AI-Specific)
**Traditional Observability:**
- [x] Structured logging (structlog JSON) implemented
- [x] Metrics for critical operations (step durations, token counts, error rates)
- [x] Correlation IDs for distributed tracing (UUID per execution)

**AI-Specific Observability (REQUIRED):**
- [x] **Token tracking implemented** for all LLM operations:
  - Capture prompt_tokens, completion_tokens, total_tokens per LLMResponse
  - ExecutionMetrics aggregates token usage by step and total
  - Token counts included in structured log messages for LLM calls
  - WorkflowResult.metrics exposes token usage via API
- [x] **LLM interaction logging**:
  - Model name, temperature, max_tokens logged per LLM call
  - Latency breakdown tracked in LLMResponse.latency_ms
  - Provider rate limit headers logged (from httpx response headers)
- [x] **Cost estimation support**: token usage in machine-readable LLMResponse.usage
- [x] **Workflow state tracking**: all WorkflowStatus and StepStatus transitions logged

### ✅ Principle V: Configurable But Convention First
- [x] Sensible defaults for all config (model=gpt-4o-mini, temp=0.7, max_tokens=1024)
- [x] All config options documented in data-model.md with default values
- [x] Configuration validated at startup via Pydantic validators with clear errors
- [x] Minimal configuration surface — 10 env vars, all optional except API key
- [x] Environment variables for deployment config (OPENAI_API_KEY, etc.)

### ✅ Principle VI: Unit Tests (AI-Specific)
**Traditional Requirements:**
- [x] ≥80% code coverage target on business logic
- [x] Fast tests (<100ms typical — all use MockLLMProvider)
- [x] External dependencies mocked (respx for httpx, MockLLMProvider)

**AI-Specific Testing Strategy:**
- [x] **Pure logic** (prompt formatting, template rendering, config validation):
  - Traditional deterministic tests with exact assertions
- [x] **LLM integration code**:
  - respx mocks for unit tests (zero real API calls)
  - vcrpy cassettes for integration test record/replay
  - Fixtures stored in `tests/fixtures/` and version controlled
- [x] **Non-deterministic outputs**:
  - Semantic assertions for any real LLM output tests
- [x] **MockLLMProvider** ships as first-class testing utility (FR-031)

### ✅ Principle VII: Integration Tests (AI-Specific)
**Cost Management (CRITICAL):**
- [x] **Cost budget**: max $0.10 per test, $2.00 per full suite
- [x] **Tiered execution strategy**:
  - Commit hooks: No LLM calls (mocks/fixtures only)
  - PR checks: Smoke tests with gpt-4o-mini (<$0.50 total)
  - Nightly: Full suite with production models (<$2.00 total)
- [x] Cost optimization: cheapest model (gpt-4o-mini) for all integration tests

**AI-Specific Requirements:**
- [x] Semantic validation (length checks, format assertions, not exact string matching)
- [x] Model version pinned: `gpt-4o-mini` for reproducibility
- [x] Provider health checks in fixtures (skip if unavailable)
- [x] Synthetic test data (no PII in fixtures)

### ✅ Principle VIII: Security (AI-Specific)
**Traditional Security:**
- [x] API keys via environment variables, NEVER hardcoded (FR-028)
- [x] API keys automatically redacted from all logs (FR-027)
- [x] Input validation for workflow definitions (FR-029)

**AI-Specific — v1 Scope (Internal/Trusted Only):**
- [x] **Prompt Injection Defense**: Basic input validation (FR-029); advanced defense deferred to v2
- [x] **PII Protection**: PII detection utilities provided (FR-030); enforcement is user responsibility in v1
- [x] **DoW Prevention**: Deferred to v2 (v1 targets internal/trusted environments)
- [x] **Output Sanitization**: Deferred to v2
- [x] **Rate Limiting**: Deferred to v2

*Violations justified in Complexity Tracking below.*

### ✅ Principle IX: Use LTS Dependencies
- [x] Python 3.11+ (latest stable, LTS-equivalent lifecycle)
- [x] All dependencies pinned with minimum versions in pyproject.toml
- [x] No bleeding-edge or pre-release dependencies
- [x] Security scanning to be configured (Dependabot) post-initial setup

### ✅ Principle X: Backward Compatibility
- [x] **v0.x pre-stability**: no backward compatibility guarantees until v1.0.0 declared
- [x] Semantic versioning followed from first release
- [x] Internal APIs clearly marked with `_internal` module
- [x] CHANGELOG.md maintained from first release

*Violation noted: relaxed backward compat during v0.x pre-stability phase — justified by clarification (2026-02-08)*

### ✅ Principle XI: Extensibility & Plugin Architecture
- [x] Plugin registry for LLM providers (PluginRegistry)
- [x] Extension points documented in contracts/interfaces.py
- [x] Plugin registration is declarative (PluginRegistry.register_provider)
- [x] Plugin lifecycle defined (initialize, execute, cleanup on LLMProvider)
- [x] Plugin isolation: errors caught per-step with is_critical flag
- [x] OpenAI built-in provider implemented AS a plugin (dog-fooding)
- [x] Middleware hook system with full lifecycle coverage

## Project Structure

### Documentation (this feature)

```text
specs/001-framework-foundation/
├── plan.md              # This file
├── research.md          # Technology decisions (Phase 0)
├── data-model.md        # Entity definitions (Phase 1)
├── quickstart.md        # Getting started guide (Phase 1)
├── contracts/
│   └── interfaces.py    # Public interface contracts (Phase 1)
└── tasks.md             # Implementation tasks (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
  generative_ai_workflow/
    __init__.py               # Public API exports (Workflow, WorkflowEngine, etc.)
    workflow.py               # Workflow class, WorkflowConfig
    step.py                   # WorkflowStep ABC, LLMStep, TransformStep
    engine.py                 # WorkflowEngine (sync/async execution, retry)
    config.py                 # FrameworkConfig (pydantic-settings, env vars)
    exceptions.py             # Exception hierarchy (ProviderError, StepError, etc.)
    providers/
      __init__.py
      base.py                 # LLMProvider ABC, LLMRequest, LLMResponse, TokenUsage
      openai.py               # OpenAIProvider (built-in plugin, uses AsyncOpenAI)
      mock.py                 # MockLLMProvider (testing utility, FR-031)
    plugins/
      __init__.py
      registry.py             # PluginRegistry
    middleware/
      __init__.py
      base.py                 # Middleware ABC
    observability/
      __init__.py
      logging.py              # structlog configuration, JSON renderer
      metrics.py              # ExecutionMetrics, StepResult aggregation
      tracker.py              # TokenUsageTracker
    _internal/
      __init__.py
      retry.py                # tenacity retry configuration for LLM calls
      async_utils.py          # Event loop utilities (sync wrapper helpers)

tests/
  conftest.py                 # Shared fixtures (MockLLMProvider, cost_tracker)
  unit/
    __init__.py
    test_workflow.py
    test_engine.py
    test_config.py
    test_exceptions.py
    providers/
      __init__.py
      test_openai_provider.py  # respx mocks
      test_mock_provider.py
    middleware/
      __init__.py
      test_base.py
    observability/
      __init__.py
      test_metrics.py
      test_token_tracker.py
      test_logging.py
  integration/
    __init__.py
    test_full_workflow.py     # Cost-budgeted, semantic assertions
    test_provider_retry.py    # Retry/backoff integration
  fixtures/
    llm_responses/            # vcrpy cassettes for integration tests

pyproject.toml
README.md
CHANGELOG.md
.env.example
```

**Structure Decision**: Single Python library package using `src/` layout (PEP 517/518 best practice). No web layer, no CLI — pure importable library. All public exports exposed via `generative_ai_workflow/__init__.py`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle VIII: Security hardening deferred | v1 targets internal/trusted use only (clarified 2026-02-08) | Implementing full DoW/rate limiting adds 3+ weeks scope for zero user value in v0.x |
| Principle X: No backward compat guarantee during v0.x | Framework API must evolve quickly during initial design phase | Locking API too early would require major versions every few weeks, creating maintenance overhead |

## Implementation Phases

### Phase 1: Package Scaffold & Data Models
- pyproject.toml with hatchling, all dependencies declared
- Directory structure creation
- Core pydantic models (TokenUsage, LLMRequest, LLMResponse, etc.)
- Exception hierarchy
- FrameworkConfig with pydantic-settings
- structlog configuration module
- Basic __init__.py with public exports skeleton

### Phase 2: LLM Provider Interface + OpenAI
- LLMProvider ABC
- OpenAIProvider using AsyncOpenAI with tenacity retry
- MockLLMProvider for testing
- PluginRegistry with OpenAI pre-registered

### Phase 3: Workflow Engine
- WorkflowStep ABC + LLMStep + TransformStep
- Workflow class (step container + variable substitution)
- WorkflowEngine with sync/async execution
- Timeout handling for sync mode
- Graceful cancellation for async mode

### Phase 4: Observability Layer
- TokenUsageTracker
- ExecutionMetrics collection
- structlog JSON logging integration
- Correlation ID propagation

### Phase 5: Middleware System
- Middleware ABC + pipeline execution
- Built-in observability middleware (logging, token tracking)
- WorkflowEngine.use() integration

### Phase 6: Testing Infrastructure
- pytest configuration (pytest.ini / pyproject.toml)
- conftest.py with shared fixtures
- respx-based OpenAI mocks
- vcrpy cassette setup for integration tests
- cost_tracker fixture for budget enforcement
