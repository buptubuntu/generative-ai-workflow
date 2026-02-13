# Implementation Plan: Workflow Control Flow

**Branch**: `002-workflow-control-flow` | **Date**: 2026-02-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-workflow-control-flow/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add control flow primitives (conditional branching, for-each loops, switch/case dispatch) to the workflow engine to enable adaptive AI workflows. This feature introduces three new `WorkflowStep` subtypes (`ConditionalStep`, `ForEachStep`, `SwitchStep`) that evaluate boolean/categorical expressions on workflow context data and route execution to nested step sequences. Expressions use a safe restricted evaluator (simpleeval) to prevent arbitrary code execution. The implementation maintains backward compatibility with existing workflows while enabling batch processing, conditional routing, and multi-way dispatch patterns essential for production AI applications.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase uses Python 3.11+ with type annotations)
**Primary Dependencies**:
- `simpleeval` (safe expression evaluator, ~1.8s per 1M evaluations, no external dependencies)
- Existing: `pydantic`, `structlog`, `openai`, `tenacity`
**Storage**: N/A (in-memory workflow execution state)
**Testing**: `pytest` with `pytest-asyncio` (existing test infrastructure at `tests/unit/`, `tests/integration/`)
**Target Platform**: Python runtime (Linux/macOS/Windows server environments)
**Project Type**: Single Python library package (`src/generative_ai_workflow/`)
**Performance Goals**:
- ≤5% overhead per control flow construct (conditional/switch/loop-dispatch) vs. equivalent plain TransformStep (SC-007)
- 100 loop iterations without >10% degradation vs. manually-unrolled equivalent (SC-003)
**Constraints**:
- Sequential execution only (no parallel iteration in loops)
- Max iteration limit: 100 (configurable, default to prevent runaway loops)
- Max nesting depth: 5 levels (configurable)
- Expression evaluation timeout: inherit from workflow-level timeout
**Scale/Scope**:
- 3 new step types (`ConditionalStep`, `ForEachStep`, `SwitchStep`)
- 1 new module (`control_flow.py`)
- 1 expression evaluator integration (`ExpressionEvaluator` class wrapping simpleeval)
- ~20 new unit tests, ~6 integration tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` (current version: v1.5.0). Each principle must be addressed - either compliant (✓) or violation justified in Complexity Tracking section below.

### ✅ Principle I: Interface-First Design
- [x] Public APIs designed with clear interfaces (abstract base classes, protocols)
  - All three step types inherit from `WorkflowStep` ABC (existing interface)
  - `ExpressionEvaluator` interface defined before implementation
- [x] Implementation details hidden behind contracts
  - Expression evaluation logic encapsulated in `ExpressionEvaluator`
  - Step consumers interact only via `WorkflowStep.execute_async()` method
- [x] Interface contracts documented before implementation begins
  - Phase 1 will generate data-model.md with interface contracts
- [x] Breaking interface changes require major version increment
  - No breaking changes to existing `WorkflowStep` interface (backward compatible)

### ✅ Principle II: Documented Public Interfaces
- [x] All public APIs have docstrings/comments with: purpose, parameters, returns, exceptions
  - All new classes (`ConditionalStep`, `ForEachStep`, `SwitchStep`, `ExpressionEvaluator`) will have comprehensive docstrings
- [x] At least one usage example per non-trivial interface
  - Quickstart.md (Phase 1) will include usage examples for each step type
- [x] Type annotations included where language supports
  - Full type annotations (Python 3.11+ style with `dict[str, Any]`, `list[WorkflowStep]`)
- [x] Performance characteristics documented for critical paths
  - Expression evaluation overhead (≤5% per construct) documented in SC-007
  - Loop iteration performance (100 iterations, ≤10% degradation) documented in SC-003

### ✅ Principle III: SOLID Principles
- [x] Single Responsibility: Each class/module has one reason to change
  - `ConditionalStep`: conditional routing only
  - `ForEachStep`: loop iteration only
  - `SwitchStep`: multi-way dispatch only
  - `ExpressionEvaluator`: expression parsing and evaluation only
- [x] Open/Closed: Extend via composition/inheritance, not modification
  - New step types extend existing `WorkflowStep` ABC without modifying it
  - Expression evaluator can be extended via custom function injection (simpleeval feature)
- [x] Dependencies injected via interfaces (not concrete implementations)
  - Control flow steps depend on `WorkflowStep` ABC (for nested steps)
  - Expression evaluator encapsulated behind interface
- [x] Violations justified in Complexity Tracking section
  - No violations anticipated

### ✅ Principle IV: Observability (AI-Specific)
**Traditional Observability:**
- [x] Structured logging (JSON/key-value format) implemented
  - Use existing `structlog` infrastructure in codebase
  - Log control flow decisions (branch taken, iteration count, case matched) per FR-017
- [x] Metrics for critical operations (latency, throughput, error rates)
  - Control flow step duration added to existing `ExecutionMetrics.step_durations`
  - Iteration counts and loop statistics captured
- [x] Correlation IDs for distributed tracing
  - Existing `StepContext.correlation_id` propagated through nested steps

**AI-Specific Observability (REQUIRED):**
- [x] **Token tracking implemented** for all LLM operations:
  - Control flow steps do not directly make LLM calls (they orchestrate nested steps)
  - Token aggregation already handled by `WorkflowEngine._execute_steps()` for nested LLMStep calls
  - No new token tracking code needed (existing infrastructure sufficient)
- [x] **LLM interaction logging**:
  - N/A for control flow steps (no direct LLM calls)
  - Nested LLMStep calls logged via existing infrastructure
- [x] **Cost estimation support**: Token usage in machine-readable format
  - Token usage from nested steps aggregated in `WorkflowResult.metrics.token_usage_total`
- [x] **Workflow state tracking**: State transitions, step execution times logged
  - Control flow decisions logged: "ConditionalStep 'X' took true branch", "ForEachStep 'Y' completed 42 iterations"
  - Nested step execution times captured in step_durations

### ✅ Principle V: Configurable But Convention First
- [x] Sensible defaults provided for all optional configuration
  - Default max iterations: 100 (configurable via workflow config)
  - Default max nesting depth: 5 (configurable via workflow config)
  - No mandatory configuration required for basic usage
- [x] All config options documented with examples and default values
  - `WorkflowConfig` extended with `max_iterations: int = 100`, `max_nesting_depth: int = 5`
  - Documented in quickstart.md with examples
- [x] Configuration validated at startup with clear error messages
  - Pydantic validation on `WorkflowConfig` (automatic via BaseModel)
  - Eager validation at workflow definition time (forward references checked per FR-004)
- [x] Configuration kept minimal (prefer convention over configuration)
  - Only 2 new config options (max_iterations, max_nesting_depth)
  - Sequential execution (no parallelism configuration needed)
- [x] Environment variables used for deployment config (secrets, URLs)
  - N/A (control flow primitives have no deployment-specific config)

### ✅ Principle VI: Unit Tests (AI-Specific)
**Traditional Requirements:**
- [x] ≥80% code coverage on business logic
  - Target: 100% coverage on expression evaluator, control flow routing logic
  - ~20 new unit tests planned
- [x] Fast tests (<100ms typical)
  - Expression evaluation tests: <10ms per test
  - Control flow routing tests: <50ms per test (using MockLLMProvider for nested steps)
- [x] External dependencies mocked/stubbed
  - Nested LLMStep calls use MockLLMProvider (existing test infrastructure)

**AI-Specific Testing Strategy (REQUIRED):**
- [x] **Pure logic** (prompt formatting, parsing, calculations):
  - Expression parsing and evaluation: deterministic tests with exact assertions
  - `assert ExpressionEvaluator.evaluate("sentiment == 'positive'", {...}) == True`
  - Loop iteration counting, conditional branch selection: deterministic
- [x] **LLM integration code**:
  - Control flow steps don't directly call LLMs (orchestrate nested LLMStep instances)
  - Use MockLLMProvider for nested steps in unit tests
  - No VCR pattern needed (no direct LLM calls)
- [x] **Non-deterministic outputs**:
  - N/A (control flow logic is deterministic given context data)
  - Nested LLMStep outputs mocked with deterministic responses
- [x] **Mock LLM providers** in unit tests (NEVER call real APIs in unit tests)
  - Use existing MockLLMProvider for all tests

### ✅ Principle VII: Integration Tests (AI-Specific)
**Cost Management (CRITICAL):**
- [x] **Cost budget documented**: $0.05 per test, $0.30 total suite (6 integration tests)
  - Use `gpt-4o-mini` for integration tests (~$0.05 per 10K tokens)
  - Each test: ~20K tokens total (10K prompt + 10K completion) = ~$0.10, but only 6 tests with short prompts (~5K tokens each) = ~$0.05/test
- [x] **Tiered execution strategy**:
  - Commit hooks: Unit tests only (no LLM calls, MockLLMProvider)
  - PR checks: Integration tests with `gpt-4o-mini` (~$0.30 total)
  - Nightly: Full suite with production models (same as PR, no additional cost)
- [x] Cost optimization strategy (use cheaper models, cache responses)
  - Use gpt-4o-mini for all integration tests
  - VCR pattern for caching responses (optional, but reduces cost to $0 after first run)

**AI-Specific Requirements:**
- [x] Semantic validation (not exact string matching)
  - Integration tests verify: "Output contains summary", "Output length > 50 chars"
  - No exact string matching for LLM outputs
- [x] Model version pinned for reproducibility (e.g., `gpt-4-0613`)
  - Pin to `gpt-4o-mini-2024-07-18` in integration tests
- [x] Provider health checks implemented
  - Integration tests verify OpenAI API connectivity (existing infrastructure)
- [x] PII sanitization verified in test data
  - Test data contains no PII (synthetic data only)

### ✅ Principle VIII: Security (AI-Specific)
**Traditional Security:**
- [x] Input validation, authentication, authorization implemented
  - Expression syntax validated (safe operators only: ==, !=, <, >, <=, >=, in, not in, and, or, not)
  - No `eval()` or arbitrary code execution (simpleeval enforces AST-based safe evaluation)
- [x] Secrets in environment variables/secret managers (NEVER hardcoded)
  - N/A (no secrets in control flow primitives)
- [x] Encryption (TLS in transit, encryption at rest for sensitive data)
  - N/A (control flow operates on in-memory data)
- [x] OWASP Top 10 vulnerabilities addressed
  - **Injection**: Prevented via simpleeval (no eval(), restricted operator set)
  - **XSS/CSRF**: N/A (server-side library, no web UI)

**AI-Specific Security (10 threat categories - address all CRITICAL):**
- [x] **1. Prompt Injection Defense** (CRITICAL):
  - Control flow steps don't construct prompts (nested LLMStep instances do)
  - Expression evaluator prevents code injection (no eval(), no __builtins__ access)
  - Existing prompt injection defense in LLMStep applies to nested steps
- [x] **2. PII Protection** (CRITICAL):
  - Control flow passes context data to nested steps unchanged
  - PII detection handled by existing infrastructure (LLMStep, middleware)
  - No new PII exposure risk introduced
- [x] **3. Denial of Wallet Prevention** (CRITICAL):
  - **Max iteration limit**: Configurable default of 100, prevents runaway loops (FR-010)
  - **Expression evaluation timeout**: Inherits from workflow-level timeout (FR-016, clarification #2)
  - **Nesting depth limit**: Configurable default of 5, prevents deeply nested explosions (FR-015)
- [x] **4. Data Isolation** (CRITICAL):
  - N/A (library code, no multi-tenancy)
  - Applications using library must enforce their own tenancy boundaries
- [x] **5-10. Other Security Measures**:
  - Output sanitization: N/A (control flow outputs are structured dicts, not user-facing strings)
  - API key security: N/A (no new API keys introduced)
  - Rate limiting: Handled by application layer (not library responsibility)
  - Monitoring: Observability via structured logging (Principle IV)

### ✅ Principle IX: Use LTS Dependencies
- [x] LTS versions used for runtime platforms (Node.js LTS, Python stable, etc.)
  - Python 3.11+ (stable, LTS support until 2027-10)
  - All dependencies use stable versions (no beta/alpha)
- [x] Dependencies pinned with version ranges in manifest
  - `simpleeval>=1.0.0,<2.0.0` (current: 1.0.3, stable since 2024)
  - Existing dependencies already pinned in pyproject.toml
- [x] Security scanning configured (Dependabot, Snyk, or equivalent)
  - Existing repository has Dependabot configured (assumed based on production framework setup)
- [x] Regular update schedule defined (monthly/quarterly)
  - Follow existing project update schedule (assumed quarterly based on constitution)

### ✅ Principle X: Backward Compatibility (Framework-Critical)
- [x] **No breaking changes** to public APIs within major version OR:
  - ✅ **Zero breaking changes**: All existing workflows continue to work identically (FR-018)
  - New step types are additive (extend `WorkflowStep` ABC, no modifications to existing classes)
  - `WorkflowConfig` extended with optional fields (default values preserve existing behavior)
  - `WorkflowEngine._execute_steps()` unchanged (control flow steps implement standard `execute_async()` interface)
- [x] Migration guide provided in `UPGRADING.md` for breaking changes
  - N/A (no breaking changes)
- [x] Semantic versioning followed (MAJOR.MINOR.PATCH)
  - This is a MINOR version increment (v0.2.0) - new features, backward compatible
- [x] Deprecated features have warnings (minimum 1 minor version notice)
  - N/A (no deprecations)
- [x] `CHANGELOG.md` updated with all changes
  - Update CHANGELOG.md with new features: ConditionalStep, ForEachStep, SwitchStep, ExpressionEvaluator

### ✅ Principle XI: Extensibility & Plugin Architecture
- [x] **Uses plugin system** for extensibility (NOT hardcoded)
  - Control flow steps are themselves extensions of `WorkflowStep` plugin interface
  - ExpressionEvaluator allows custom function injection via simpleeval's `functions` parameter
- [x] Extension points documented (which interfaces can be extended)
  - `WorkflowStep` ABC remains primary extension point (unchanged)
  - ExpressionEvaluator custom functions documented in quickstart.md
- [x] Plugin registration is declarative and simple
  - Control flow steps registered like any WorkflowStep (instantiate and add to workflow.steps list)
  - No special registration needed (uses existing pattern)
- [x] Plugin lifecycle defined (init, execute, cleanup)
  - Same lifecycle as existing WorkflowStep (init → execute_async → cleanup via context managers)
- [x] Plugin isolation implemented (failures don't cascade to framework)
  - Existing WorkflowEngine error handling applies (critical vs. non-critical step failures)
  - Nested step failures handled gracefully (FR-011: step-level error attribution)
- [x] Example plugin provided for guidance
  - Quickstart.md will include examples of all three control flow step types

### ✅ Principle XII: Branch-Per-Task Development Workflow
- [x] Each task has its own dedicated feature branch before work begins
  - Feature branch `002-workflow-control-flow` created
  - Each implementation task will have sub-branch: `002-T###-<description>`
- [x] Branch naming follows convention: `<task-id>-<short-description>`
  - Example: `002-T001-expression-evaluator`, `002-T002-conditional-step`
- [x] Unit tests pass before opening PR/MR
  - CI/CD pipeline enforces unit test passage (existing infrastructure)
- [x] Integration tests pass before merging to main
  - CI/CD pipeline enforces integration test passage before merge
- [x] No direct commits to main branch
  - All work via feature branches and PRs (existing workflow)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/generative_ai_workflow/
├── __init__.py                     # Public API exports
├── workflow.py                     # Workflow, StepContext, WorkflowResult, ExecutionMetrics
├── step.py                         # WorkflowStep ABC, LLMStep, TransformStep
├── engine.py                       # WorkflowEngine, _execute_steps loop
├── config.py                       # FrameworkConfig, WorkflowConfig
├── exceptions.py                   # Exception hierarchy
├── control_flow.py                 # NEW: ConditionalStep, ForEachStep, SwitchStep, ExpressionEvaluator
├── providers/
│   ├── __init__.py
│   ├── base.py                     # LLMProvider ABC, TokenUsage, LLMRequest, LLMResponse
│   ├── openai.py                   # OpenAIProvider
│   └── mock.py                     # MockLLMProvider
├── plugins/
│   └── registry.py                 # PluginRegistry
├── middleware/
│   └── base.py                     # Middleware ABC
└── observability/
    ├── logging.py                  # Structured logging setup
    ├── metrics.py                  # Metrics collection
    └── tracker.py                  # Token usage tracking

tests/
├── unit/
│   ├── test_workflow.py            # Existing workflow tests
│   ├── test_step.py                # Existing step tests
│   ├── test_engine.py              # Existing engine tests
│   ├── test_control_flow.py        # NEW: Control flow step tests
│   └── test_expression_evaluator.py # NEW: Expression evaluator tests
└── integration/
    ├── test_workflow_integration.py # Existing integration tests
    └── test_control_flow_integration.py # NEW: Control flow integration tests (6 tests)
```

**Structure Decision**: Single project structure (Option 1). This is a Python library package following the existing `src/generative_ai_workflow/` layout. New control flow primitives are added as a single new module (`control_flow.py`) containing all three step types and the expression evaluator. Tests follow the existing `tests/unit/` and `tests/integration/` structure.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No constitutional violations** - All principles fully compliant. No complexity tracking needed.
