# Research: Workflow Control Flow

**Feature**: 002-workflow-control-flow
**Date**: 2026-02-08
**Purpose**: Resolve technical unknowns and establish best practices for implementing control flow primitives in the generative AI workflow engine

---

## Research Questions

This document consolidates findings from research tasks addressing:

1. **Safe Expression Evaluation**: How to safely evaluate user-supplied boolean/categorical expressions without arbitrary code execution risks?
2. **Async Workflow Patterns**: How do modern Python async workflow engines handle nested step execution and control flow?
3. **Performance Overhead**: What is acceptable performance overhead for control flow constructs in workflow engines?
4. **Engine Integration**: How do the existing `WorkflowEngine._execute_steps()` loop and `StepContext` threading work?

---

## 1. Safe Expression Evaluator Selection

### Decision: Use `simpleeval`

**Rationale**:
- **Security**: AST-based safe evaluation with no `eval()` or `__builtins__` access
- **Performance**: ~1.8 seconds per 1M evaluations (14x faster than `asteval`: 26.1s per 1M)
- **Simplicity**: Single-file library, zero external dependencies
- **Maintenance**: Actively maintained (v1.0.3 as of 2024), no recent CVEs
- **Feature fit**: Supports required operators (`==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `not in`, `and`, `or`, `not`)
- **Safety limits**: Built-in protection against DoS (MAX_POWER=4000000, MAX_STRING_LENGTH=100000)

**Alternatives Considered**:

| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| **RestrictedPython** | Enterprise-grade, Zope foundation | Heavier (multiple modules), recent CVEs (CVE-2024-47532, CVE-2025-22153), overkill for simple expressions | ❌ Too complex |
| **asteval** | More features (loops, functions, comprehensions) | Significantly slower (14x), multi-file module, more complex | ❌ Overkill |
| **simpleeval** | Fast, single-file, secure, minimal | Limited features (no loops/functions) | ✅ **SELECTED** |
| **Custom parser** | Full control | High development cost, security risks | ❌ Not justified |

**Implementation Notes**:
- Wrap `simpleeval.simple_eval()` in `ExpressionEvaluator` class
- Pass workflow context variables via `names` parameter: `simple_eval(expr, names={**context.input_data, **context.previous_outputs})`
- Restrict to safe operators only (default simpleeval configuration)
- Apply workflow-level timeout to expression evaluation (no separate timeout needed)

**Sources**:
- [simpleeval GitHub](https://github.com/danthedeckie/simpleeval)
- [simpleeval PyPI](https://pypi.org/project/simpleeval/)
- [RestrictedPython PyPI](https://pypi.org/project/RestrictedPython/)
- [Snyk RestrictedPython vulnerabilities](https://security.snyk.io/package/pip/restrictedpython)
- [evalidate comparison benchmarks](https://github.com/yaroslaff/evalidate)

---

## 2. Async Workflow Patterns

### Decision: Sequential Async Execution with Recursive `execute_async()` Calls

**Rationale**:
- **Consistency**: Aligns with existing `WorkflowEngine._execute_steps()` sequential loop
- **Simplicity**: No parallelism means no race conditions, no lock contention
- **Predictability**: Execution order is deterministic (iteration N+1 sees results of iteration N)
- **Backward compatibility**: Existing workflows continue to work identically

**Pattern**:
```python
async def execute_async(self, context: StepContext) -> StepResult:
    # Control flow step orchestrates nested steps
    for step in self.nested_steps:
        child_ctx = StepContext(
            workflow_id=context.workflow_id,
            step_id=str(uuid.uuid4()),
            correlation_id=context.correlation_id,
            input_data=context.input_data,  # Immutable
            variables=context.variables,
            previous_outputs={**context.previous_outputs, **accumulated_output},  # Thread data
            config=context.config,
        )
        child_result = await step.execute_async(child_ctx)
        # Handle failure, accumulate output
        accumulated_output.update(child_result.output or {})
    return StepResult(...)
```

**Alternatives Considered**:
- **Parallel iteration**: Loop body steps run concurrently (e.g., `asyncio.gather()`)
  - ❌ Rejected: Adds complexity, breaks determinism, not required by spec (assumption: "sequential only")
- **Task queue**: Dispatch loop iterations to worker pool
  - ❌ Rejected: Overkill for library code, complicates error handling

**Sources**:
- Existing codebase analysis (`engine.py:153-271`, `_execute_steps()` loop)
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)

---

## 3. Performance Overhead Budget

### Decision: ≤5% Overhead Per Control Flow Construct

**Rationale**:
- **SC-007 requirement**: Each control flow construct (conditional/switch/loop-dispatch) adds ≤5% overhead vs. equivalent plain TransformStep
- **Industry baseline**: Web frameworks target <10% middleware overhead; 5% is achievable for control flow
- **Measurement**: Compare 100-iteration loop with 100 sequential plain steps (both with no-op transforms)

**Performance Targets**:

| Operation | Target | Measurement Method |
|-----------|--------|---------------------|
| Expression evaluation | <0.1ms per eval | Benchmark: 10K evaluations of `sentiment == 'positive'` |
| Conditional branch dispatch | <0.2ms | Benchmark: 1K conditional evaluations + branch selection |
| Loop iteration dispatch | <0.1ms per iteration | Benchmark: 100-iteration loop with no-op body vs. 100 sequential steps |
| Nested step context creation | <0.05ms | Benchmark: 1K StepContext instantiations |

**Optimization Strategies**:
- Cache compiled expression ASTs (simpleeval returns AST, reusable)
- Minimize dict copying (use dict views where possible)
- Profile hot paths with `cProfile` before merging

**Sources**:
- [simpleeval performance characteristics](https://github.com/danthedeckie/simpleeval#performance)
- SC-003, SC-007 from spec.md

---

## 4. Existing WorkflowEngine Integration

### Finding: Comprehensive Understanding of Engine Architecture

**Key Integration Points**:

1. **`WorkflowEngine._execute_steps()` Loop** (`engine.py:153-271`):
   - **Sequential execution**: `for step in workflow.steps`
   - **StepContext creation**: Lines 170-179, passes `previous_outputs.copy()` to each step
   - **Error handling**: Lines 188-200, catches all exceptions and wraps in `StepResult`
   - **Output accumulation**: Lines 254-255, `previous_outputs.update(step_result.output)`
   - **Metrics aggregation**: Lines 202-217, collects token usage and step durations

2. **StepContext Data Threading** (`workflow.py:80-99`):
   - `input_data`: Immutable original workflow input
   - `previous_outputs`: Accumulates output from step 1 → step 2 → ... → step N
   - All steps see same `input_data`, but `previous_outputs` grows incrementally

3. **WorkflowStep Interface** (`step.py:21-89`):
   - **Required method**: `async def execute_async(self, context: StepContext) -> StepResult`
   - **Return value**: `StepResult` with `step_id`, `status`, `output`, `error`, `duration_ms`, `token_usage`
   - **Error handling**: Return `StepResult(status=FAILED, error=str(e))`, do NOT raise exceptions

4. **Error Handling Pattern**:
   - Control flow steps must check `step.is_critical`:
     - If `True` and child step fails → return `StepResult(status=FAILED)`
     - If `False` and child step fails → log warning, continue

5. **Token Usage Aggregation**:
   - Control flow steps do NOT directly call LLMs (orchestrate nested LLMStep instances)
   - Engine automatically aggregates token usage from nested steps via `metrics.token_usage_total`
   - No new token tracking code needed

**Sources**:
- Existing codebase exploration (completed by research agent a063529)
- Files analyzed: `engine.py`, `step.py`, `workflow.py`, `tests/unit/test_workflow.py`

---

## 5. Additional Best Practices

### Logging Best Practices (from research agent a1e9375)

**Decision**: Use `structlog` with `orjson` for JSON logging (already in codebase)

**Control Flow Logging Requirements**:
- Log control flow decisions: "ConditionalStep 'sentiment_router' took true branch (condition: sentiment == 'positive')"
- Log iteration counts: "ForEachStep 'batch_processor' completed 42 iterations"
- Log case matches: "SwitchStep 'type_router' matched case 'email' (value: 'email')"
- Log forward reference validation errors: "ConditionalStep 'X' references undefined variable 'missing_var' (available: ['input', 'step1_output'])"

**Sources**:
- [structlog performance documentation](https://www.structlog.org/en/stable/performance.html)
- [Better Stack Python logging guide](https://betterstack.com/community/guides/logging/best-python-logging-libraries/)

---

## 6. Dependency Decisions

### Python Packaging: Use `hatchling` (existing)

**Decision**: Add `simpleeval` to existing `pyproject.toml` using hatchling backend

**Rationale**:
- Existing project uses hatchling (modern PEP 621 standard)
- No reason to change build system for single dependency addition

**Implementation**:
```toml
[project]
dependencies = [
    # Existing dependencies...
    "simpleeval>=1.0.0,<2.0.0",
]
```

**Sources**:
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Hatchling documentation](https://pypi.org/project/hatchling/)

---

## Summary of Decisions

| Question | Decision | Key Rationale |
|----------|----------|---------------|
| Expression Evaluator | `simpleeval` | 14x faster than asteval, secure, single-file, zero dependencies |
| Execution Model | Sequential async with recursive `execute_async()` | Consistent with existing engine, deterministic, simple |
| Performance Budget | ≤5% overhead per construct | SC-007 requirement, achievable via expression caching |
| Logging | `structlog` + `orjson` (existing) | Already in codebase, best-in-class performance |
| Packaging | `hatchling` (existing) | No change needed, modern standard |
| Testing Strategy | Unit tests with MockLLMProvider | No real LLM calls, deterministic, fast |
| Integration Test Cost | $0.30 total (6 tests @ $0.05 each) | gpt-4o-mini, VCR caching, PR checks only |

---

## Open Questions Resolved

All "NEEDS CLARIFICATION" items from Technical Context have been resolved:

1. ✅ Expression evaluator library → `simpleeval`
2. ✅ Async execution pattern → Sequential with recursive `execute_async()`
3. ✅ Performance overhead budget → ≤5% per construct
4. ✅ Engine integration points → Comprehensive mapping complete
5. ✅ Logging infrastructure → Existing `structlog` + `orjson`
6. ✅ Testing strategy → MockLLMProvider for unit tests, gpt-4o-mini for integration

---

**Research Complete** | Ready for Phase 1 (Design & Contracts)
