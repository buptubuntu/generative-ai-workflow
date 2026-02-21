# Data Model: Rename Step Concept to Node

**Feature**: 003-rename-step-node
**Date**: 2026-02-21

---

## Entity Rename Map

All public names containing "Step" are renamed to "Node". Old names are permanently removed with no aliases.

| Old Name (removed) | New Name | Source File (old → new) | Role |
|--------------------|----------|-------------------------|------|
| `WorkflowStep` | `WorkflowNode` | `step.py` → `node.py` | Abstract base class for all workflow nodes |
| `LLMStep` | `LLMNode` | `step.py` → `node.py` | Built-in node: calls an LLM provider |
| `TransformStep` | `TransformNode` | `step.py` → `node.py` | Built-in node: applies a Python transform |
| `ConditionalStep` | `ConditionalNode` | `control_flow.py` | Built-in node: boolean expression branching |
| `StepResult` | `NodeResult` | `workflow.py` | Result returned from a node execution |
| `StepContext` | `NodeContext` | `workflow.py` | Execution context passed into each node |
| `StepStatus` | `NodeStatus` | `workflow.py` | Enum of node lifecycle states |
| `StepError` | `NodeError` | `exceptions.py` | Exception for unrecoverable node failure |
| `steps=` (Workflow param) | `nodes=` | `workflow.py` | Constructor keyword argument |
| `workflow.steps` (attribute) | `workflow.nodes` | `workflow.py` | Public attribute on Workflow instance |
| `true_steps=` (ConditionalStep) | `true_nodes=` | `control_flow.py` | Branch parameter |
| `false_steps=` (ConditionalStep) | `false_nodes=` | `control_flow.py` | Branch parameter |
| `generative_ai_workflow.step` | `generative_ai_workflow.node` | module path | Python import path |

---

## Entity Definitions (Post-Rename)

### WorkflowNode (abstract base)

- **Identity**: Identified by `name: str` — non-empty, unique within a `Workflow`
- **Attributes**: `name: str`, `is_critical: bool = True`
- **Contract**: Subclasses MUST implement `execute_async(context: NodeContext) -> NodeResult`
- **Sync fallback**: Default `execute()` wraps `execute_async()` via event loop
- **Relationship**: Contained in `Workflow.nodes: list[WorkflowNode]`
- **Validation**: `name` must be non-empty at construction time

### LLMNode

- **Inherits**: `WorkflowNode`
- **Attributes**: `name`, `prompt_template: str`, `provider_name: str | None`, `is_critical`
- **Behaviour**: Renders prompt template against `{**context.input_data, **context.previous_outputs}` → resolves LLM provider via `PluginRegistry` → calls `provider.complete_async(request)` → returns `NodeResult` with LLM text and `TokenUsage`
- **Validation**: `prompt` must be non-empty at construction time

### TransformNode

- **Inherits**: `WorkflowNode`
- **Attributes**: `name`, `transform: Callable[[dict[str, Any]], dict[str, Any]]`, `is_critical`
- **Behaviour**: Applies `transform` callable to `{**context.input_data, **context.previous_outputs}` → returns `NodeResult` with transformed dict

### ConditionalNode

- **Does NOT inherit WorkflowNode** (same pattern as former `ConditionalStep` — duck-typed with `execute_async`)
- **Attributes**: `name`, `condition: str`, `true_nodes: list[WorkflowNode]`, `false_nodes: list[WorkflowNode]`, `is_critical`
- **Behaviour**: Evaluates `condition` via `ExpressionEvaluator` → executes `true_nodes` or `false_nodes` sequentially → accumulates outputs and token usage → returns aggregated `NodeResult`
- **Validation**: `condition` non-empty and syntactically valid (checked at construction); `true_nodes` non-empty

### NodeContext

- **Type**: Pydantic `BaseModel`
- **Fields**: `workflow_id: str`, `step_id: str`, `correlation_id: str`, `input_data: dict`, `variables: dict`, `previous_outputs: dict`, `config: Any`
- **Note**: Internal field `step_id` retains its name in this release (it is a UUID identifying the execution slot, not the node type concept). May be renamed to `node_id` in a future pass if desired.

### NodeResult

- **Type**: Pydantic `BaseModel`
- **Fields**: `step_id: str`, `status: NodeStatus`, `output: dict | None`, `error: str | None`, `duration_ms: float ≥ 0`, `token_usage: TokenUsage | None`

### NodeStatus

- **Type**: `str` Enum
- **Values**: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `SKIPPED`
- **Methods**: `is_terminal: bool` property — True for COMPLETED, FAILED, SKIPPED

### NodeError

- **Inherits**: `FrameworkError`
- **Usage**: Raised on unrecoverable node execution failure

---

## State Transitions

```
NodeStatus:  PENDING → RUNNING → COMPLETED
                               → FAILED
                               → SKIPPED

WorkflowStatus:  PENDING → RUNNING → COMPLETED
                                   → FAILED
                                   → CANCELLED
                                   → TIMEOUT
```

---

## Module Import Path Change

```python
# Old (removed)
from generative_ai_workflow.step import WorkflowStep, LLMStep, TransformStep
from generative_ai_workflow import LLMStep, TransformStep, WorkflowStep

# New
from generative_ai_workflow.node import WorkflowNode, LLMNode, TransformNode
from generative_ai_workflow import LLMNode, TransformNode, WorkflowNode
```
