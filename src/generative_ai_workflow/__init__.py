"""generative_ai_workflow — A generic AI workflow framework.

Build and execute multi-node LLM workflows with built-in OpenAI support,
async/sync execution modes, plugin extensibility, and structured observability.

Quick start::

    import asyncio
    from generative_ai_workflow import Workflow, LLMNode

    workflow = Workflow(
        nodes=[LLMNode(name="summarize", prompt="Summarize: {text}")],
    )

    async def main():
        result = await workflow.execute_async({"text": "Long content here..."})
        print(result.status)

    asyncio.run(main())
"""

from generative_ai_workflow.config import FrameworkConfig
from generative_ai_workflow.control_flow import (
    ConditionalNode,
    ExpressionError,
    ExpressionTimeoutError,
)
from generative_ai_workflow.engine import WorkflowEngine
from generative_ai_workflow.exceptions import (
    AbortError,
    ConfigurationError,
    FrameworkError,
    NodeError,
    PluginError,
    PluginNotFoundError,
    PluginRegistrationError,
    ProviderAuthError,
    ProviderError,
    WorkflowError,
)
from generative_ai_workflow.node import LLMNode, TransformNode, WorkflowNode
from generative_ai_workflow.plugins.registry import PluginRegistry
from generative_ai_workflow.providers.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    TokenUsage,
    detect_pii,
)
from generative_ai_workflow.providers.mock import MockLLMProvider
from generative_ai_workflow.workflow import (
    ExecutionMetrics,
    NodeContext,
    NodeResult,
    NodeStatus,
    Workflow,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStatus,
)

__all__ = [
    # Config
    "FrameworkConfig",
    # Control Flow
    "ConditionalNode",
    "ExpressionError",
    "ExpressionTimeoutError",
    # Engine
    "WorkflowEngine",
    # Exceptions
    "AbortError",
    "ConfigurationError",
    "FrameworkError",
    "NodeError",
    "PluginError",
    "PluginNotFoundError",
    "PluginRegistrationError",
    "ProviderAuthError",
    "ProviderError",
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
    # Nodes
    "LLMNode",
    "TransformNode",
    "WorkflowNode",
    # Workflow models
    "ExecutionMetrics",
    "NodeContext",
    "NodeResult",
    "NodeStatus",
    "Workflow",
    "WorkflowConfig",
    "WorkflowResult",
    "WorkflowStatus",
]

__version__ = "0.2.0"
