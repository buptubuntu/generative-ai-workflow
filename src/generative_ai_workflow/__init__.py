"""generative_ai_workflow — A generic AI workflow framework.

Build and execute multi-step LLM workflows with built-in OpenAI support,
async/sync execution modes, plugin extensibility, and structured observability.

Quick start::

    import asyncio
    from generative_ai_workflow import Workflow, LLMStep

    workflow = Workflow(
        steps=[LLMStep(name="summarize", prompt="Summarize: {text}")],
    )

    async def main():
        result = await workflow.execute_async({"text": "Long content here..."})
        print(result.status)

    asyncio.run(main())
"""

from generative_ai_workflow.config import FrameworkConfig
from generative_ai_workflow.engine import WorkflowEngine
from generative_ai_workflow.exceptions import (
    AbortError,
    ConfigurationError,
    FrameworkError,
    PluginError,
    PluginNotFoundError,
    PluginRegistrationError,
    ProviderAuthError,
    ProviderError,
    StepError,
    WorkflowError,
)
from generative_ai_workflow.plugins.registry import PluginRegistry
from generative_ai_workflow.providers.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    TokenUsage,
    detect_pii,
)
from generative_ai_workflow.providers.mock import MockLLMProvider
from generative_ai_workflow.step import LLMStep, TransformStep, WorkflowStep
from generative_ai_workflow.workflow import (
    ExecutionMetrics,
    StepContext,
    StepResult,
    StepStatus,
    Workflow,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStatus,
)

__all__ = [
    # Config
    "FrameworkConfig",
    # Engine
    "WorkflowEngine",
    # Exceptions
    "AbortError",
    "ConfigurationError",
    "FrameworkError",
    "PluginError",
    "PluginNotFoundError",
    "PluginRegistrationError",
    "ProviderAuthError",
    "ProviderError",
    "StepError",
    "WorkflowError",
    # Plugin system
    "PluginRegistry",
    # Providers
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "MockLLMProvider",
    "TokenUsage",
    "detect_pii",
    # Steps
    "LLMStep",
    "TransformStep",
    "WorkflowStep",
    # Workflow models
    "ExecutionMetrics",
    "StepContext",
    "StepResult",
    "StepStatus",
    "Workflow",
    "WorkflowConfig",
    "WorkflowResult",
    "WorkflowStatus",
]

__version__ = "0.1.0"
