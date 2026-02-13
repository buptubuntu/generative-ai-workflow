# Generative AI Workflow Framework - Examples

This directory contains comprehensive examples demonstrating all features of the framework.

## Quick Start

```bash
# Run all examples
python examples/complete_workflow_example.py

# Or run with real OpenAI (requires API key)
export OPENAI_API_KEY=your_key_here
python examples/complete_workflow_example.py
```

## Implemented Features

### ✅ Phase 1: Framework Foundation (001-framework-foundation)

#### Core Components
- **Workflow**: Orchestrates multi-step AI workflows
- **WorkflowEngine**: Async/sync execution with timeout handling
- **WorkflowConfig**: Centralized configuration with validation

#### Step Types
- **LLMStep**: Executes LLM calls with prompt templates
- **TransformStep**: Pure data transformation functions
- **WorkflowStep**: Abstract base class for custom steps

#### Providers
- **OpenAIProvider**: Production OpenAI integration with retry logic
- **MockLLMProvider**: Zero-cost testing with deterministic responses
- **PluginRegistry**: Dynamic provider registration

#### Features
- Async and sync execution modes
- Prompt template interpolation with `{variable}` syntax
- Token usage tracking and aggregation
- Structured JSON logging with correlation IDs
- Middleware pipeline support
- PII detection for safe logging

### ✅ Phase 3: Control Flow (002-workflow-control-flow)

#### Control Flow Primitives
- **ConditionalStep**: If/else branching with boolean expressions
- **ExpressionEvaluator**: Safe AST-based expression evaluation
- **Complex expressions**: `and`, `or`, `not`, `in`, comparison operators

#### Advanced Features
- **Nested conditionals**: Multi-level decision trees
- **Context threading**: Seamless data flow through branches
- **Token aggregation**: Combines token usage across all LLM calls
- **Critical/non-critical**: Configurable failure handling
- **No else branch**: Optional false_steps for conditional-only logic

#### Security
- No eval/exec (AST-based evaluation only)
- Restricted operator set (comparison, logical, membership)
- DoS protection (string length, exponentiation limits)
- Clear error messages with variable suggestions

## Example Overview

### Example 1: Basic Workflow
**Demonstrates:** LLMStep, TransformStep, sequential execution

```python
workflow = Workflow(
    steps=[
        TransformStep(name="extract", transform=lambda d: {"text": d["input"]}),
        LLMStep(name="analyze", prompt="Analyze: {text}", provider="mock"),
        LLMStep(name="respond", prompt="Generate response", provider="mock"),
    ],
)
result = workflow.execute({"input": "Customer message"})
```

**Output:**
- Status: COMPLETED
- Token usage: 36 tokens
- Duration: ~2ms

### Example 2: Conditional Branching
**Demonstrates:** ConditionalStep, sentiment-based routing

```python
ConditionalStep(
    name="sentiment_router",
    condition="sentiment == 'positive'",
    true_steps=[positive_response_step],
    false_steps=[negative_response_step],
)
```

**Features:**
- Routes to different response strategies
- Logs decision with `control_flow_decision` event
- Only executes selected branch (not both)

### Example 3: Nested Conditionals
**Demonstrates:** Multi-level decision trees, priority escalation

```python
# Outer: Priority check
priority_router = ConditionalStep(
    condition="priority > 7",
    true_steps=[mark_urgent, severity_router],  # Nested conditional
    false_steps=[mark_normal, severity_router],
)

# Inner: Severity action
severity_router = ConditionalStep(
    condition="severity == 'critical'",
    true_steps=[escalate_to_manager],
    false_steps=[assign_to_agent],
)
```

**Output:**
```
Priority: 9 → Urgent → Critical → Escalate to manager (SLA: 1 hour)
Priority: 5 → Normal → Normal → Assign to agent (SLA: 24 hours)
```

### Example 4: Complex Expressions
**Demonstrates:** Boolean logic, compound conditions

```python
ConditionalStep(
    name="access_check",
    condition="(user_type == 'premium' and usage < limit) or user_type == 'admin'",
    true_steps=[grant_access],
    false_steps=[deny_access],
)
```

**Supported Operators:**
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `and`, `or`, `not`
- Membership: `in`, `not in`
- Functions: `len()`

### Example 5: Token Usage Tracking
**Demonstrates:** Token aggregation across conditional branches

```python
conditional = ConditionalStep(
    condition="route == 'multi'",
    true_steps=[llm_step1, llm_step2, llm_step3],  # 3 LLM calls
    false_steps=[llm_step1],  # 1 LLM call
)
```

**Output:**
```
True branch: 48 total tokens (3 steps)
False branch: 16 total tokens (1 step)
```

**Note:** Token usage from all steps in the executed branch is automatically aggregated in `result.metrics.token_usage_total`

### Example 6: Error Handling
**Demonstrates:** Critical vs non-critical step failures

```python
# Critical step (workflow fails if this fails)
TransformStep(
    name="critical_step",
    transform=failing_function,
    is_critical=True,
)

# Non-critical step (workflow continues if this fails)
TransformStep(
    name="optional_step",
    transform=failing_function,
    is_critical=False,
)
```

**Behavior:**
- **Critical failure**: Workflow status = FAILED, execution stops
- **Non-critical failure**: Workflow status = COMPLETED, execution continues

## Real-World Use Cases

### Customer Support Triage System
```python
workflow = Workflow(steps=[
    # 1. Analyze sentiment
    LLMStep(name="sentiment", prompt="Analyze: {text}"),

    # 2. Route by sentiment
    ConditionalStep(
        condition="sentiment_output == 'positive'",
        true_steps=[thank_you_response],
        false_steps=[
            # Nested: Check priority for negative sentiment
            ConditionalStep(
                condition="priority > 7",
                true_steps=[urgent_escalation],
                false_steps=[standard_response],
            )
        ],
    ),

    # 3. Finalize ticket
    TransformStep(name="finalize", transform=create_ticket),
])
```

### Access Control System
```python
ConditionalStep(
    name="rbac_check",
    condition="(role == 'admin' or (role == 'user' and owns_resource)) and not blocked",
    true_steps=[grant_access],
    false_steps=[deny_access],
)
```

### Content Moderation Pipeline
```python
workflow = Workflow(steps=[
    LLMStep(name="classify", prompt="Classify content: {text}"),
    ConditionalStep(
        condition="classification in ['spam', 'harmful', 'illegal']",
        true_steps=[flag_content, notify_moderators],
        false_steps=[approve_content],
    ),
])
```

## Testing Best Practices

### Use MockLLMProvider for Development
```python
from generative_ai_workflow import MockLLMProvider, PluginRegistry

# Setup mock responses
mock = MockLLMProvider(responses={
    "positive": "positive",
    "negative": "negative",
    "response": "Thank you for your feedback!",
})
PluginRegistry.register_provider("mock", mock)

# Use in workflow
workflow = Workflow(
    steps=[LLMStep(name="test", prompt="...", provider="mock")],
    config=WorkflowConfig(provider="mock"),
)
```

**Benefits:**
- ✅ Zero API costs
- ✅ Deterministic outputs
- ✅ Fast execution (~0.2ms per call)
- ✅ Token usage simulation

### Test Both Branches
```python
# Test true branch
result_true = workflow.execute({"condition_var": True})
assert "true_step_output" in result_true.output

# Test false branch
result_false = workflow.execute({"condition_var": False})
assert "false_step_output" in result_false.output
```

## Performance Characteristics

### Execution Speed (MockLLMProvider)
- Basic workflow (3 steps): ~2ms
- Conditional branching: ~0.6ms
- Nested conditionals (2 levels): ~1ms
- Complex expressions: ~0.5ms

### Token Usage (Real OpenAI)
- Expression evaluation: 0 tokens
- ConditionalStep overhead: 0 tokens (no LLM calls)
- Only selected branch steps consume tokens

### Memory Efficiency
- Minimal overhead: ~100KB per workflow instance
- Context threading: Dict updates (O(n) where n = # of keys)
- No deep copies: References to step outputs

## Migration to Real OpenAI

1. **Set API key:**
```bash
export OPENAI_API_KEY=sk-...
```

2. **Update provider:**
```python
workflow = Workflow(
    steps=[...],
    config=WorkflowConfig(
        provider="openai",  # Changed from "mock"
        model="gpt-4o-mini",
        temperature=0.7,
    ),
)
```

3. **Handle rate limits:**
```python
# OpenAIProvider includes automatic retry with exponential backoff
# Default: 3 retries, exponential backoff starting at 1s
```

4. **Monitor token usage:**
```python
result = workflow.execute(input_data)
print(f"Tokens used: {result.metrics.token_usage_total.total_tokens}")
print(f"Cost: ${result.metrics.token_usage_total.total_tokens * 0.000001}")
```

## Next Steps

### Upcoming Features (Phase 4-7)
- **ForEachStep**: Parallel iteration over collections
- **SwitchStep**: Multi-way routing (like match/case)
- **WhileStep**: Loop-based execution
- **Enhanced observability**: Distributed tracing, metrics export
- **Performance optimizations**: Caching, batching

### Try It Yourself
1. Clone the repository
2. Install: `pip install -e ".[dev]"`
3. Run examples: `python examples/complete_workflow_example.py`
4. Explore the test suite: `pytest tests/ -v`

## Support

- GitHub: https://github.com/buptubuntu/generative-ai-workflow
- Issues: Report bugs or request features
- Tests: 128 passing tests demonstrate all features

---

**Framework Version:** 0.2.0
**Last Updated:** 2024-02-13
**Test Coverage:** 128/128 tests passing ✅
