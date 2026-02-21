# generative-ai-workflow

A generic AI workflow framework for building and executing multi-step LLM workflows.

**Status**: Pre-alpha (v0.x — no backward compatibility guarantees until v1.0.0)

## Features

- Define and execute multi-step LLM workflows with built-in OpenAI support
- Async and synchronous execution modes with optional timeout
- Built-in token usage tracking and execution metrics
- Plugin system for custom LLM providers and middleware
- Structured JSON logging with correlation IDs
- Testing utilities including mock providers and fixture record/replay

## Quick Start

See [specs/001-framework-foundation/quickstart.md](specs/001-framework-foundation/quickstart.md) for a comprehensive getting started guide.

```python
import asyncio
from generative_ai_workflow import Workflow, LLMNode

workflow = Workflow(
    nodes=[LLMNode(name="summarize", prompt="Summarize in one sentence: {text}")],
    name="my-first-workflow",
)

async def main():
    result = await workflow.execute_async({"text": "Long article content here..."})
    print(result.status)
    print(result.metrics.token_usage_total.total_tokens)

asyncio.run(main())
```

## Installation

```bash
pip install generative-ai-workflow
```

## Requirements

- Python 3.11+
- OpenAI API key (when using the built-in OpenAI provider)

## License

MIT
