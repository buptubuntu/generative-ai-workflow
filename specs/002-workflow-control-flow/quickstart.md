# Quickstart: Workflow Control Flow

**Feature**: 002-workflow-control-flow
**Version**: 0.2.0
**Date**: 2026-02-08

This guide demonstrates how to use control flow primitives (conditional branching, loops, switch/case) in the generative AI workflow engine.

---

## Table of Contents

1. [Installation](#installation)
2. [Conditional Branching](#conditional-branching)
3. [Loop Iteration](#loop-iteration)
4. [Multi-Way Dispatch (Switch/Case)](#multi-way-dispatch-switchcase)
5. [Nested Control Flow](#nested-control-flow)
6. [Expression Reference](#expression-reference)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Performance Considerations](#performance-considerations)

---

## Installation

Control flow primitives are included in generative-ai-workflow v0.2.0+:

```bash
pip install generative-ai-workflow>=0.2.0
```

Import the new step types:

```python
from generative_ai_workflow import (
    Workflow,
    WorkflowConfig,
    ConditionalStep,  # NEW: Conditional branching
    ForEachStep,      # NEW: Loop iteration
    SwitchStep,       # NEW: Multi-way dispatch
    LLMStep,
    TransformStep,
)
```

---

## Conditional Branching

### Example 1: Route by Sentiment

```python
from generative_ai_workflow import Workflow, ConditionalStep, LLMStep

# Workflow: Analyze sentiment, then generate appropriate response
workflow = Workflow(
    steps=[
        # Step 1: Sentiment analysis
        LLMStep(
            name="analyze_sentiment",
            prompt="Analyze sentiment of this text: '{text}'. Return only 'positive' or 'negative'.",
        ),

        # Step 2: Conditional routing based on sentiment
        ConditionalStep(
            name="sentiment_router",
            condition="analyze_sentiment_output == 'positive'",  # Boolean expression
            true_steps=[
                LLMStep(
                    name="positive_response",
                    prompt="Generate an enthusiastic response to: {text}",
                ),
            ],
            false_steps=[
                LLMStep(
                    name="empathetic_response",
                    prompt="Generate an empathetic, supportive response to: {text}",
                ),
            ],
        ),
    ],
)

# Execute
result = workflow.execute({"text": "I love this product!"})
print(result.output["positive_response_output"])  # Enthusiastic response
```

### Example 2: Conditional with No Else Branch

```python
# Only process high-priority items
workflow = Workflow(
    steps=[
        TransformStep(
            name="classify",
            transform=lambda data: {"priority": 9, "issue": data["issue"]},
        ),
        ConditionalStep(
            name="high_priority_only",
            condition="priority > 8",
            true_steps=[
                LLMStep(name="escalate", prompt="Escalate issue: {issue}"),
            ],
            # No false_steps → step completes with empty output if priority <= 8
        ),
    ],
)

result = workflow.execute({"issue": "Production outage"})
# If priority > 8: result.output contains "escalate_output"
# If priority <= 8: result.output is empty for this step
```

### Example 3: Complex Boolean Conditions

```python
ConditionalStep(
    name="approval_router",
    condition="confidence > 0.8 and error_count == 0 and status != 'failed'",
    true_steps=[
        LLMStep(name="auto_approve", prompt="Generate approval message"),
    ],
    false_steps=[
        LLMStep(name="manual_review", prompt="Flag for manual review"),
    ],
)
```

---

## Loop Iteration

### Example 1: Batch Process Documents

```python
from generative_ai_workflow import Workflow, ForEachStep, LLMStep, TransformStep

# Workflow: Summarize multiple documents
workflow = Workflow(
    steps=[
        # Step 1: Load documents
        TransformStep(
            name="load_documents",
            transform=lambda _: {
                "documents": [
                    "Document 1: AI advances in 2024...",
                    "Document 2: Climate change report...",
                    "Document 3: Economic forecast...",
                ]
            },
        ),

        # Step 2: Loop over documents and summarize each
        ForEachStep(
            name="batch_summarizer",
            items_var="documents",       # List from previous step
            loop_var="doc",              # Current item variable name
            loop_steps=[
                LLMStep(
                    name="summarize",
                    prompt="Summarize in 2 sentences: {doc}",
                ),
            ],
            output_var="summaries",      # Collected results
        ),
    ],
)

# Execute
result = workflow.execute({})
print(result.output["summaries"])  # List of 3 summaries
# [
#     {"summarize_output": "Summary of document 1..."},
#     {"summarize_output": "Summary of document 2..."},
#     {"summarize_output": "Summary of document 3..."},
# ]
```

### Example 2: Multi-Step Loop Body

```python
# Complex loop body: analyze + classify + route
ForEachStep(
    name="process_emails",
    items_var="emails",
    loop_var="email",
    loop_steps=[
        # Step 1: Extract key information
        LLMStep(
            name="extract_info",
            prompt="Extract sender, subject, and urgency from: {email}",
        ),
        # Step 2: Classify urgency
        LLMStep(
            name="classify_urgency",
            prompt="Rate urgency 1-10 for: {extract_info_output}",
        ),
        # Step 3: Generate response
        LLMStep(
            name="generate_response",
            prompt="Generate response for: {email} (urgency: {classify_urgency_output})",
        ),
    ],
    output_var="processed_emails",
)

# Each iteration produces accumulated output from all 3 steps
# output["processed_emails"] = [
#     {"extract_info_output": ..., "classify_urgency_output": ..., "generate_response_output": ...},
#     {"extract_info_output": ..., "classify_urgency_output": ..., "generate_response_output": ...},
#     ...
# ]
```

### Example 3: Empty List Handling

```python
workflow = Workflow(
    steps=[
        TransformStep(name="load", transform=lambda _: {"items": []}),  # Empty list
        ForEachStep(
            name="process",
            items_var="items",
            loop_var="item",
            loop_steps=[LLMStep(name="analyze", prompt="Analyze: {item}")],
            output_var="results",
        ),
    ],
)

result = workflow.execute({})
print(result.output["results"])  # [] (empty list, loop body never executed)
```

### Example 4: Custom Max Iterations

```python
# Override default max_iterations (100) for this specific loop
ForEachStep(
    name="large_batch",
    items_var="large_dataset",
    loop_var="item",
    loop_steps=[LLMStep(name="process", prompt="Process: {item}")],
    output_var="results",
    max_iterations=500,  # Allow up to 500 iterations (instead of default 100)
)
```

---

## Multi-Way Dispatch (Switch/Case)

### Example 1: Route by Document Type

```python
from generative_ai_workflow import Workflow, SwitchStep, LLMStep, TransformStep

# Workflow: Classify document type, then process accordingly
workflow = Workflow(
    steps=[
        # Step 1: Classify document type
        LLMStep(
            name="classify_type",
            prompt="Classify this document type: {text}. Return only: email, report, or invoice.",
        ),

        # Step 2: Route by type
        SwitchStep(
            name="type_router",
            switch_on="classify_type_output",  # Variable from previous step
            cases={
                "email": [
                    LLMStep(name="process_email", prompt="Extract sender and subject from: {text}"),
                ],
                "report": [
                    LLMStep(name="summarize_report", prompt="Summarize key findings from: {text}"),
                ],
                "invoice": [
                    LLMStep(name="extract_invoice_data", prompt="Extract amount and date from: {text}"),
                ],
            },
            default_steps=[
                LLMStep(name="process_unknown", prompt="Handle unknown document type: {text}"),
            ],
        ),
    ],
)

# Execute with email
result = workflow.execute({"text": "From: john@example.com\nSubject: Meeting..."})
print(result.output["process_email_output"])  # Email extraction

# Execute with report
result = workflow.execute({"text": "Q4 2024 Sales Report..."})
print(result.output["summarize_report_output"])  # Report summary
```

### Example 2: Switch Without Default (Fails on No Match)

```python
SwitchStep(
    name="priority_router",
    switch_on="priority",
    cases={
        "high": [LLMStep(name="escalate", prompt="Escalate: {issue}")],
        "medium": [LLMStep(name="queue", prompt="Queue: {issue}")],
        "low": [LLMStep(name="defer", prompt="Defer: {issue}")],
    },
    # No default_steps → workflow FAILS if priority is "critical" or other unexpected value
)
```

### Example 3: Switch on Expression

```python
# Switch on calculated expression (not just variable reference)
SwitchStep(
    name="size_router",
    switch_on="len(items)",  # Expression: count items
    cases={
        "0": [TransformStep(name="empty_handler", transform=lambda _: {"msg": "No items"})],
        "1": [LLMStep(name="single_handler", prompt="Process single item: {items}")],
    },
    default_steps=[
        LLMStep(name="multi_handler", prompt="Process multiple items: {items}"),
    ],
)
```

---

## Nested Control Flow

Control flow steps can be nested up to 5 levels deep (configurable via `WorkflowConfig.max_nesting_depth`).

### Example: Loop Inside Conditional

```python
workflow = Workflow(
    steps=[
        ConditionalStep(
            name="check_batch",
            condition="len(items) > 0",
            true_steps=[
                # Nested loop: process items if list is non-empty
                ForEachStep(
                    name="process_items",
                    items_var="items",
                    loop_var="item",
                    loop_steps=[
                        LLMStep(name="analyze", prompt="Analyze: {item}"),
                    ],
                    output_var="results",
                ),
            ],
            false_steps=[
                TransformStep(name="empty_msg", transform=lambda _: {"msg": "No items"}),
            ],
        ),
    ],
)
```

### Example: Conditional Inside Loop

```python
ForEachStep(
    name="process_documents",
    items_var="documents",
    loop_var="doc",
    loop_steps=[
        # Nested conditional: route by document length
        ConditionalStep(
            name="length_router",
            condition="len(doc) > 1000",  # Long document
            true_steps=[
                LLMStep(name="summarize_long", prompt="Summarize long doc: {doc}"),
            ],
            false_steps=[
                LLMStep(name="summarize_short", prompt="Summarize short doc: {doc}"),
            ],
        ),
    ],
    output_var="summaries",
)
```

### Example: Switch Inside Loop

```python
ForEachStep(
    name="multi_type_processor",
    items_var="mixed_documents",
    loop_var="doc",
    loop_steps=[
        # Nested switch: route by document type
        SwitchStep(
            name="type_router",
            switch_on="doc['type']",  # Access nested field
            cases={
                "email": [LLMStep(name="email_handler", prompt="Process email: {doc}")],
                "report": [LLMStep(name="report_handler", prompt="Process report: {doc}")],
            },
            default_steps=[LLMStep(name="default_handler", prompt="Process unknown: {doc}")],
        ),
    ],
    output_var="results",
)
```

---

## Expression Reference

### Supported Operators

| Category | Operators | Example |
|----------|-----------|---------|
| **Comparison** | `==`, `!=`, `<`, `>`, `<=`, `>=` | `priority > 8`, `status == 'complete'` |
| **Membership** | `in`, `not in` | `type in ['email', 'sms']`, `'error' not in log` |
| **Logical** | `and`, `or`, `not` | `x > 5 and y < 10`, `not is_complete` |
| **Literals** | strings, numbers, lists, dicts | `'positive'`, `42`, `[1, 2, 3]`, `{'key': 'value'}` |
| **Functions** | `len()` | `len(items) > 0` |

### Variable References

Expressions can reference:
- **Input data**: Variables passed to `workflow.execute(data)`
- **Previous step outputs**: Variables from `previous_outputs` (e.g., `step1_output`)

```python
# Example context:
{
    "input_var": "value",              # From workflow.execute({"input_var": "value"})
    "step1_output": "result1",         # From previous step named "step1"
    "classify_output": "positive",     # From previous step named "classify"
}

# Valid expressions:
"input_var == 'value'"                 # Reference input
"step1_output == 'result1'"            # Reference step output
"classify_output == 'positive'"        # Reference step output
"len(items) > 0"                       # Function call on variable
```

### Expression Limitations

**NOT supported** (security restrictions):
- Function definitions: `def`, `lambda`
- Assignments: `=`, `+=`, etc.
- Imports: `import`, `from`
- Attribute access (except whitelisted): `.` operator restricted
- Dunder methods: `__builtins__`, `__import__`, etc.

```python
# ❌ INVALID (will raise ExpressionError)
"lambda x: x > 10"                     # Function definition
"items = [1, 2, 3]"                    # Assignment
"import os"                            # Import
"user.__dict__"                        # Dunder access
```

---

## Configuration

### WorkflowConfig Extensions

Control flow adds two new configuration options to `WorkflowConfig`:

```python
from generative_ai_workflow import WorkflowConfig, Workflow

config = WorkflowConfig(
    provider="openai",              # Existing config
    model="gpt-4o-mini",            # Existing config

    # NEW: Control flow limits (DoW prevention)
    max_iterations=100,             # Max loop iterations (default: 100)
    max_nesting_depth=5,            # Max control flow nesting depth (default: 5)
)

workflow = Workflow(steps=[...], config=config)
```

### Configuration Options

| Option | Default | Range | Purpose |
|--------|---------|-------|---------|
| `max_iterations` | 100 | 1-10000 | Maximum iterations for `ForEachStep` (prevents runaway loops) |
| `max_nesting_depth` | 5 | 1-20 | Maximum control flow nesting depth (prevents stack overflow) |

### Overriding Max Iterations Per Loop

You can override `max_iterations` for specific `ForEachStep` instances:

```python
# Global default: 100 iterations
config = WorkflowConfig(max_iterations=100)

workflow = Workflow(
    steps=[
        # This loop uses global default (100)
        ForEachStep(
            name="small_batch",
            items_var="items",
            loop_var="item",
            loop_steps=[...],
            output_var="results",
        ),

        # This loop overrides to 500
        ForEachStep(
            name="large_batch",
            items_var="large_dataset",
            loop_var="item",
            loop_steps=[...],
            output_var="results",
            max_iterations=500,  # Override
        ),
    ],
    config=config,
)
```

---

## Error Handling

### Undefined Variable

```python
ConditionalStep(
    name="router",
    condition="missing_var == 'value'",  # Variable not in context
    true_steps=[...],
)

# Raises: ExpressionError("Variable 'missing_var' not found in context (available: ['input', 'step1_output'])")
```

**Fix**: Ensure variable is produced by a previous step or passed in input data.

### Max Iterations Exceeded

```python
workflow = Workflow(
    steps=[
        TransformStep(name="load", transform=lambda _: {"items": list(range(200))}),  # 200 items
        ForEachStep(
            name="process",
            items_var="items",
            loop_var="item",
            loop_steps=[...],
            output_var="results",
            max_iterations=100,  # Default limit
        ),
    ],
)

# Raises: StepError("Max iterations (100) exceeded (got 200)")
```

**Fix**: Increase `max_iterations` for the loop or globally via `WorkflowConfig`.

### No Case Matched (Switch Without Default)

```python
SwitchStep(
    name="router",
    switch_on="type",
    cases={
        "email": [...],
        "report": [...],
    },
    # No default_steps
)

# If type == "invoice", raises: StepError("No case matched value 'invoice' and no default provided")
```

**Fix**: Add `default_steps` or ensure all possible values have cases.

### Invalid Expression Syntax

```python
ConditionalStep(
    name="router",
    condition="import os",  # Invalid: import not allowed
    true_steps=[...],
)

# Raises: ExpressionError("Invalid expression syntax: import statement forbidden")
```

**Fix**: Use only allowed operators (see [Expression Reference](#expression-reference)).

---

## Performance Considerations

### Overhead Targets

Control flow constructs add minimal overhead:

| Operation | Overhead | Benchmark |
|-----------|----------|-----------|
| Expression evaluation | <0.1ms | 10K evaluations of `sentiment == 'positive'` |
| Conditional dispatch | <0.2ms | 1K conditional evaluations + branch selection |
| Loop per-iteration | <0.1ms | 100-iteration loop with no-op body |
| Total overhead per construct | ≤5% | vs. equivalent plain `TransformStep` (SC-007) |

### Performance Tips

1. **Cache expressions**: If evaluating the same expression repeatedly, consider caching the compiled AST (advanced usage).
2. **Limit nesting**: Deeply nested control flow (>5 levels) increases overhead and complexity. Prefer flatter workflows.
3. **Use batch operations**: For large datasets, consider preprocessing outside the workflow and passing smaller batches.
4. **Profile hot paths**: Use Python's `cProfile` to identify bottlenecks before optimizing.

### 100-Iteration Loop Performance

Per SC-003, loops process at least 100 iterations without >10% degradation vs. equivalent manually-unrolled sequential workflows:

```python
# Loop version (100 iterations)
ForEachStep(
    name="batch",
    items_var="items",  # 100 items
    loop_var="item",
    loop_steps=[TransformStep(name="process", transform=lambda d: {"result": d["item"].upper()})],
    output_var="results",
)

# Equivalent manual version (100 sequential steps)
# [TransformStep(name=f"process_{i}", transform=...) for i in range(100)]

# Loop overhead: ≤10% (measured via benchmarks)
```

---

## Next Steps

- **API Reference**: See [contracts/control_flow_api.py](./contracts/control_flow_api.py) for detailed API documentation
- **Data Model**: See [data-model.md](./data-model.md) for entity definitions and validation rules
- **Examples**: See `examples/control_flow/` for more advanced usage patterns (coming soon)
- **Migration Guide**: Existing workflows (v0.1.0) work identically with v0.2.0 (no changes required)

---

**Questions?** File an issue at [github.com/yourorg/generative-ai-workflow/issues](https://github.com/yourorg/generative-ai-workflow/issues)
