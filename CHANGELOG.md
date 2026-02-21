# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-21

### Breaking Changes — Migration Required

All public API symbols containing "Step" have been permanently renamed to "Node".
There are **no backward-compatible aliases**. Update your code using the table below.

#### Symbol Renames

| Removed (v0.1.x) | Replacement (v0.2.0) | Module |
|-------------------|----------------------|--------|
| `WorkflowStep` | `WorkflowNode` | `generative_ai_workflow.node` |
| `LLMStep` | `LLMNode` | `generative_ai_workflow.node` |
| `TransformStep` | `TransformNode` | `generative_ai_workflow.node` |
| `ConditionalStep` | `ConditionalNode` | `generative_ai_workflow.control_flow` |
| `StepResult` | `NodeResult` | `generative_ai_workflow.workflow` |
| `StepContext` | `NodeContext` | `generative_ai_workflow.workflow` |
| `StepStatus` | `NodeStatus` | `generative_ai_workflow.workflow` |
| `StepError` | `NodeError` | `generative_ai_workflow.exceptions` |
| `Workflow(steps=[...])` | `Workflow(nodes=[...])` | `generative_ai_workflow.workflow` |
| `workflow.steps` | `workflow.nodes` | `generative_ai_workflow.workflow` |
| `ConditionalStep(true_steps=[...])` | `ConditionalNode(true_nodes=[...])` | `generative_ai_workflow.control_flow` |
| `ConditionalStep(false_steps=[...])` | `ConditionalNode(false_nodes=[...])` | `generative_ai_workflow.control_flow` |

#### Module Path Change

```python
# Removed
from generative_ai_workflow.step import WorkflowStep, LLMStep, TransformStep

# Replacement
from generative_ai_workflow.node import WorkflowNode, LLMNode, TransformNode
```

#### Quick Migration Example

```python
# v0.1.x
from generative_ai_workflow import Workflow, LLMStep, TransformStep
workflow = Workflow(steps=[TransformStep(name="prep", transform=fn), LLMStep(name="gen", prompt="...")])

# v0.2.0
from generative_ai_workflow import Workflow, LLMNode, TransformNode
workflow = Workflow(nodes=[TransformNode(name="prep", transform=fn), LLMNode(name="gen", prompt="...")])
```

### Removed

- `WorkflowStep`, `LLMStep`, `TransformStep` classes and `generative_ai_workflow.step` module
- `StepResult`, `StepContext`, `StepStatus`, `StepError` types
- `ConditionalStep` and its `true_steps`/`false_steps` parameters
- `Workflow(steps=...)` constructor parameter and `.steps` attribute

## [Unreleased]

### Added
- Initial framework foundation
- Multi-step LLM workflow execution (async and sync modes)
- Built-in OpenAI provider integration
- Plugin system for custom LLM providers and middleware
- Token usage tracking and execution metrics
- Structured JSON logging with correlation IDs
- MockLLMProvider for testing without API costs
- Fixture record/replay for deterministic integration tests
