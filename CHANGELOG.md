# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 0.4.0

### Added

- `StableDiffusionNode` — a new `WorkflowNode` subclass for local text-to-image
  generation via Stable Diffusion. Supports `{variable}` prompt templates
  (identical to `LLMNode`), configurable image dimensions, inference steps,
  guidance scale, and a custom output directory. Emits structured logs and
  metrics at full parity with `LLMNode` (FR-014, SC-007).
- `GeneratedImage` — Pydantic output model returned in `NodeResult.output`
  under the key `"generated_image"`. Carries `file_path`, `image_bytes`,
  `width`, `height`, `generation_duration_ms`, `model_id`, `inference_steps`,
  `guidance_scale`, and `device_type`.
- `sd_model_registry.ModelRegistry` — process-level singleton registry for
  `StableDiffusionPipeline` instances. Thread-safe via double-checked locking;
  inference serialized per model via `threading.Lock`; scheduler cloned per
  call via `from_pipe()`.
- `sd_model_registry.GenerationConfig` — Pydantic model for validated
  image-generation parameters (width/height multiples of 8, steps ≥ 1,
  guidance ≥ 0.0).
- Optional dependency group `[stable-diffusion]` in `pyproject.toml` —
  `diffusers>=0.31.0,<1.0`, `transformers>=4.41.2,<5.0`, `accelerate>=0.31.0`,
  `safetensors>=0.3.1`, `Pillow>=9.0`, `torch>=2.0.0`. Install with:
  `pip install "generative-ai-workflow[stable-diffusion]"`.

### No Breaking Changes

All existing `WorkflowNode`, `LLMNode`, `TransformNode`, `Workflow`, and engine
APIs are unchanged. The new optional extras group does not affect users who do
not install it.

---

## [0.3.0] - 2026-02-22

### Removed

- `NodeContext.variables` field (`dict[str, Any]`) — was always `{}`, never populated by the engine; no user code or test referenced it
- Unreachable `_framework_config` lookup in `LLMNode` simplified to direct `"gpt-4o-mini"` default

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
