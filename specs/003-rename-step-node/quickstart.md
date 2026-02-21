# Quickstart: Workflow Node API

**Feature**: 003-rename-step-node
**Date**: 2026-02-21

This guide shows how to build and execute workflows with the renamed node API.
All "Step" names from v0.1.x are replaced with "Node" names in v0.2.0.

---

## Migration from v0.1.x

```python
# v0.1.x (removed)
from generative_ai_workflow import Workflow, LLMStep, TransformStep, WorkflowStep
from generative_ai_workflow.step import WorkflowStep
from generative_ai_workflow.control_flow import ConditionalStep

workflow = Workflow(steps=[LLMStep(name="summarize", prompt="Summarize: {text}")])

# v0.2.0 (new)
from generative_ai_workflow import Workflow, LLMNode, TransformNode, WorkflowNode
from generative_ai_workflow.node import WorkflowNode
from generative_ai_workflow.control_flow import ConditionalNode

workflow = Workflow(nodes=[LLMNode(name="summarize", prompt="Summarize: {text}")])
```

---

## Basic Workflow

```python
import asyncio
from generative_ai_workflow import Workflow, LLMNode

workflow = Workflow(
    nodes=[LLMNode(name="summarize", prompt="Summarize in one sentence: {text}")],
    name="my-first-workflow",
)

async def main():
    result = await workflow.execute_async({"text": "Long article content here..."})
    print(result.status)                               # "completed"
    print(result.metrics.token_usage_total.total_tokens)

asyncio.run(main())
```

---

## Multi-Node Pipeline

```python
from generative_ai_workflow import Workflow, LLMNode, TransformNode

workflow = Workflow(
    nodes=[
        TransformNode(
            name="prepare",
            transform=lambda data: {"cleaned": data["raw"].strip()},
        ),
        LLMNode(
            name="analyze",
            prompt="Analyze the sentiment of: {cleaned}",
        ),
        LLMNode(
            name="summarize",
            prompt="Summarize this analysis in one sentence: {analyze_output}",
        ),
    ],
)

result = workflow.execute({"raw": "  The product is excellent!  "})
print(result.output)
```

---

## Conditional Branching

```python
from generative_ai_workflow import Workflow, LLMNode
from generative_ai_workflow.control_flow import ConditionalNode

workflow = Workflow(
    nodes=[
        LLMNode(name="detect", prompt="Reply with only 'positive' or 'negative': {text}"),
        ConditionalNode(
            name="router",
            condition="detect_output == 'positive'",
            true_nodes=[LLMNode(name="upsell", prompt="Write an upsell message for: {text}")],
            false_nodes=[LLMNode(name="recover", prompt="Write a recovery message for: {text}")],
        ),
    ],
)

result = workflow.execute({"text": "I love this product!"})
print(result.status)
```

---

## Custom Node

```python
from generative_ai_workflow import WorkflowNode, Workflow, LLMNode
from generative_ai_workflow.workflow import NodeContext, NodeResult, NodeStatus


class WordCountNode(WorkflowNode):
    """A custom node that counts words in the input text."""

    name = "word_count"

    async def execute_async(self, context: NodeContext) -> NodeResult:
        import time
        start = time.perf_counter()
        text = context.input_data.get("text", "")
        count = len(text.split())
        duration = (time.perf_counter() - start) * 1000
        return NodeResult(
            step_id=context.step_id,
            status=NodeStatus.COMPLETED,
            output={"word_count": count},
            error=None,
            duration_ms=duration,
        )


workflow = Workflow(
    nodes=[
        WordCountNode(),
        LLMNode(
            name="summarize",
            prompt="Text has {word_count} words. Summarize in one sentence: {text}",
        ),
    ],
)

result = workflow.execute({"text": "The quick brown fox jumps over the lazy dog."})
print(result.output)
```

---

## Sync Execution with Timeout

```python
result = workflow.execute({"text": "..."}, timeout=30.0)
if result.status == "timeout":
    print("Workflow exceeded 30 second limit")
else:
    print(result.output)
```

---

## Token Usage and Metrics

```python
result = await workflow.execute_async({"text": "..."})

# Total token usage across all LLM nodes
print(result.metrics.token_usage_total.total_tokens)
print(result.metrics.token_usage_total.prompt_tokens)
print(result.metrics.token_usage_total.completion_tokens)

# Per-node durations
for node_name, duration_ms in result.metrics.step_durations.items():
    print(f"{node_name}: {duration_ms:.1f}ms")
```
