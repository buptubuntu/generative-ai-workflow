# Quickstart: Framework Foundation

**Target**: New user executes first workflow in <15 minutes (SC-007)

## Installation

```bash
pip install generative-ai-workflow
```

## Prerequisites

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

## Execute Your First Workflow (Async — Recommended)

```python
import asyncio
from generative_ai_workflow import Workflow, LLMStep

# Define a 2-step workflow: format prompt → call LLM
workflow = Workflow(
    steps=[
        LLMStep(name="summarize", prompt="Summarize in one sentence: {text}"),
    ],
    name="my-first-workflow",
)

# Execute asynchronously
async def main():
    result = await workflow.execute_async({"text": "Long article content here..."})
    print(result.status)          # "completed"
    print(result.output["text"])  # LLM response
    print(result.metrics.token_usage_total.total_tokens)  # token count

asyncio.run(main())
```

## Execute Synchronously (with timeout)

```python
result = workflow.execute(
    {"text": "Long article content here..."},
    timeout=30.0,  # fail after 30 seconds
)
print(result.status)  # "completed" or "timeout"
```

## Multi-Step Workflow with Variable Passing

```python
from generative_ai_workflow import Workflow, LLMStep, TransformStep

workflow = Workflow(
    steps=[
        TransformStep(
            name="prepare",
            transform=lambda data: {"prompt_input": data["text"].strip()},
        ),
        LLMStep(
            name="analyze",
            prompt="Analyze the sentiment of: {prompt_input}",
        ),
        LLMStep(
            name="summarize",
            prompt="Given this analysis: {analyze_output}\nProvide a brief summary.",
        ),
    ]
)
```

## Add Custom Middleware

```python
from generative_ai_workflow import WorkflowEngine, Middleware, LLMResponse

class CostLogger(Middleware):
    async def after_llm_call(self, response: LLMResponse, context: dict):
        print(f"Tokens used: {response.usage.total_tokens}")
        return None  # don't modify response

engine = WorkflowEngine()
engine.use(CostLogger())

result = await engine.run_async(workflow, {"text": "..."})
```

## Register a Custom LLM Provider

```python
from generative_ai_workflow import PluginRegistry, LLMProvider, LLMRequest, LLMResponse

class MyLocalProvider(LLMProvider):
    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        # Your custom LLM integration
        ...

PluginRegistry.register_provider("my_local", MyLocalProvider)

# Use it in a workflow
workflow = Workflow(
    steps=[LLMStep(name="gen", prompt="...", provider="my_local")]
)
```

## Use Mock Provider for Testing (Zero Cost)

```python
from generative_ai_workflow.providers import MockLLMProvider
from generative_ai_workflow import PluginRegistry

# Register mock with canned responses
mock = MockLLMProvider(responses={"default": "This is a mock response."})
PluginRegistry.register_provider("mock", mock)

# Use in tests — no API calls, zero cost
result = workflow.execute({"text": "anything"})
assert result.status == "completed"
```

## Configuration

```bash
# Environment variables (all optional, sensible defaults provided)
export GENAI_WORKFLOW_DEFAULT_MODEL="gpt-4o-mini"
export GENAI_WORKFLOW_DEFAULT_TEMPERATURE="0.7"
export GENAI_WORKFLOW_DEFAULT_MAX_TOKENS="1024"
export GENAI_WORKFLOW_MAX_RETRIES="3"
export GENAI_WORKFLOW_LOG_LEVEL="INFO"
export GENAI_WORKFLOW_LOG_PROMPTS="false"  # opt-in to log prompts
```

## Observability

All workflow executions emit structured JSON logs automatically:

```json
{
  "event": "workflow.completed",
  "workflow_id": "abc-123",
  "correlation_id": "xyz-456",
  "status": "completed",
  "duration_ms": 1250.3,
  "total_tokens": 342,
  "steps_completed": 3,
  "timestamp": "2026-02-08T10:00:00Z"
}
```

Token usage is available programmatically:

```python
result = await workflow.execute_async({"text": "..."})
usage = result.metrics.token_usage_total
print(f"Total cost data: {usage.prompt_tokens} prompt + {usage.completion_tokens} completion")
```
