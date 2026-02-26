# Implementation Plan: Prometheus Observability Middleware

**Branch**: `001-prometheus-middleware` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-prometheus-middleware/spec.md`

## Summary

Add a `PrometheusMiddleware` class to `src/generative_ai_workflow/middleware/prometheus.py` that hooks into the existing `Middleware` base class to export 6 Prometheus metric families (2 histograms, 4 counters) covering workflow duration, completion status, per-node duration, per-node errors, and per-node token usage. The class is an optional dependency (`prometheus-client>=0.16.0`) distributed via a new `[observability]` extras group. No existing code is modified except `pyproject.toml` and `middleware/__init__.py`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `prometheus-client>=0.16.0` (new, optional); `structlog>=24.0` (existing); `pydantic>=2.0` (existing)
**Storage**: N/A — all metric state is in-memory inside prometheus-client's registry
**Testing**: pytest + pytest-asyncio (existing)
**Target Platform**: Library — any Linux/macOS/Windows Python 3.11+ environment
**Project Type**: Single Python package
**Performance Goals**: ≤1ms overhead per workflow execution on average (SC-004)
**Constraints**: No HTTP server spawned by the middleware; optional dep must not break import for users who don't install it
**Scale/Scope**: Library with multiple concurrent async WorkflowEngine instances sharing one PrometheusMiddleware

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Interface-First Design
- [x] `PrometheusMiddleware` implements the existing `Middleware` ABC — contracts defined before implementation
- [x] Implementation details (metric objects) hidden behind the `Middleware` hook interface
- [x] API contract documented in `contracts/prometheus-middleware-api.md` before implementation begins
- [x] No breaking interface changes — additive only

### ✅ Principle II: Documented Public Interfaces
- [x] `PrometheusMiddleware.__init__` will have full docstring: purpose, all parameters, raises, example
- [x] Each hook override will document what metrics it records
- [x] Type annotations on all parameters and return types
- [x] Performance note: ≤1ms overhead documented in class docstring

### ✅ Principle III: SOLID Principles
- [x] Single Responsibility: `PrometheusMiddleware` only records Prometheus metrics — no routing, no cost calc
- [x] Open/Closed: existing engine and middleware base untouched; extended via composition
- [x] Dependencies injected: `registry` and `label_sanitiser` injected at construction

### ✅ Principle IV: Observability (AI-Specific)
- [x] Structured logging: metric recording errors logged via structlog with warning level
- [x] This feature IS the metrics layer — it satisfies the observability requirement for users
- [x] Token tracking: FR-005 exposes prompt and completion tokens per node and model
- [x] Workflow state tracking: workflow status and node-level durations captured

### ✅ Principle V: Configurable But Convention First
- [x] All constructor params have sensible defaults (`prefix="workflow"`, global registry, default buckets)
- [x] All config options documented with examples in `contracts/` and `quickstart.md`
- [x] No startup validation needed beyond ValueError on bad prefix (simple, fast)
- [x] Optional dependency pattern with clear ImportError message (FR-009)

### ✅ Principle VI: Unit Tests (AI-Specific)
- [x] No LLM calls in this feature — all tests are pure/deterministic
- [x] Unit tests use mock `WorkflowResult` and `TokenUsage` objects; no real engine calls needed
- [x] Test coverage target: ≥80% on `middleware/prometheus.py`
- [x] External dep (`prometheus-client`) used directly in tests (no mocking needed — it's a pure in-memory library)

### ✅ Principle VII: Integration Tests (AI-Specific)
- [x] Integration test: attach PrometheusMiddleware to real WorkflowEngine with MockProvider; verify metric output
- [x] No LLM API calls → $0 cost per test run
- [x] No model version pinning needed (no LLM involved)

### ✅ Principle VIII: Security (AI-Specific)
- [x] No secrets or PII handled by this middleware
- [x] Label sanitiser (FR-010, FR-014) prevents injection of unexpected characters into metric names
- [x] `label_sanitiser` hook allows callers to mask sensitive node/model names (FR-014)
- [x] No network calls; no authentication surface

### ✅ Principle IX: Use LTS Dependencies
- [x] `prometheus-client>=0.16.0` — stable, widely-deployed, LTS-equivalent
- [x] All existing LTS deps unchanged

### ✅ Principle X: Backward Compatibility
- [x] No existing public API modified
- [x] `Middleware` base class unchanged
- [x] New optional extras group `observability` is additive
- [x] Minor version bump required (e.g., 0.4.0 → 0.5.0)
- [x] CHANGELOG.md to be updated

### ✅ Principle XI: Extensibility & Plugin Architecture
- [x] `label_sanitiser` callable allows extensibility without subclassing
- [x] `registry` injection allows multi-tenant metric isolation
- [x] `PrometheusMiddleware` itself is a plugin to the existing middleware system

### ✅ Principle XII: Branch-Per-Task Development Workflow
- [x] Working on branch `001-prometheus-middleware`
- [x] Spec and design artifacts committed before implementation begins
- [x] Tasks will have sub-branches per task

## Project Structure

### Documentation (this feature)

```text
specs/001-prometheus-middleware/
├── spec.md              ✅ complete
├── plan.md              ✅ this file
├── research.md          ✅ complete
├── data-model.md        ✅ complete
├── quickstart.md        ✅ complete
├── contracts/
│   └── prometheus-middleware-api.md  ✅ complete
├── checklists/
│   └── requirements.md  ✅ complete
└── tasks.md             ⏳ generated by /speckit.tasks
```

### Source Code Changes

```text
src/generative_ai_workflow/
├── middleware/
│   ├── __init__.py          MODIFY — export PrometheusMiddleware (lazy/guarded)
│   └── prometheus.py        CREATE — PrometheusMiddleware implementation
└── (all other files)        NO CHANGES

tests/
├── unit/
│   └── middleware/
│       └── test_prometheus.py   CREATE — unit tests (mock WorkflowResult)
└── integration/
    └── test_prometheus_integration.py   CREATE — integration test with MockProvider

pyproject.toml               MODIFY — add [observability] extras group
```

## Complexity Tracking

No constitution violations requiring justification. All principles satisfied cleanly by the additive nature of this feature.
