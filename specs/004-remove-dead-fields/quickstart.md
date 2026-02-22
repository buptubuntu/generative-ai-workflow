# Quickstart: Remove Dead Fields (v0.3.0)

**Branch**: `004-remove-dead-fields` | **Date**: 2026-02-21

## Migration Guide

This is a minor cleanup change. For the vast majority of users, **no code changes are required**.

### If you accessed `NodeContext.variables` directly

This field no longer exists. Remove all reads and writes:

```python
# Before (v0.2.0)
class MyNode(WorkflowNode):
    async def execute(self, context: NodeContext) -> NodeResult:
        vars = context.variables  # ← remove this

# After (v0.3.0)
class MyNode(WorkflowNode):
    async def execute(self, context: NodeContext) -> NodeResult:
        # Use context.input_data or context.previous_outputs instead
        data = context.input_data
```

### If you created `NodeContext` objects in tests

```python
# Before (v0.2.0)
ctx = NodeContext(
    workflow_id="wf-1",
    step_id="s-1",
    correlation_id="c-1",
    variables={},          # ← remove this line
)

# After (v0.3.0)
ctx = NodeContext(
    workflow_id="wf-1",
    step_id="s-1",
    correlation_id="c-1",
)
```

## Verification

After upgrading, confirm the field is gone:

```python
from generative_ai_workflow.workflow import NodeContext
assert not hasattr(NodeContext.model_fields, "variables")  # ← should pass
```
