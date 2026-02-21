"""Workflow node abstractions and built-in node types.

Defines the WorkflowNode ABC that users and plugins implement, plus
the built-in LLMNode and TransformNode implementations.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from generative_ai_workflow.exceptions import NodeError
from generative_ai_workflow.workflow import NodeContext, NodeResult, NodeStatus

if TYPE_CHECKING:
    pass


class WorkflowNode(ABC):
    """Abstract base class for workflow node implementations.

    Implement this interface to add custom node behaviors (API calls,
    data validation, external service integrations, etc.) without
    modifying the framework.

    Attributes:
        name: Human-readable node identifier used in metrics and logs.
        is_critical: If True (default), node failure aborts the workflow.
                     If False, failure is logged and execution continues.

    Example::

        class SentimentNode(WorkflowNode):
            name = "sentiment_analysis"

            async def execute_async(self, context: NodeContext) -> NodeResult:
                text = context.input_data.get("text", "")
                sentiment = analyze(text)
                return NodeResult(
                    step_id=context.step_id,
                    status=NodeStatus.COMPLETED,
                    output={"sentiment": sentiment},
                    error=None,
                    duration_ms=0.0,
                )
    """

    name: str = ""
    is_critical: bool = True

    def __init__(self, name: str = "", is_critical: bool = True) -> None:
        if name:
            self.name = name
        if not self.name:
            raise ValueError("WorkflowNode must have a non-empty name.")
        self.is_critical = is_critical

    @abstractmethod
    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Execute this node asynchronously.

        Args:
            context: Execution context including input data, variables,
                     and outputs from previous nodes.

        Returns:
            NodeResult with output data and execution metadata.

        Raises:
            NodeError: On unrecoverable node failure.
        """
        ...

    def execute(self, context: NodeContext) -> NodeResult:
        """Execute this node synchronously.

        Default implementation wraps execute_async in an event loop.
        Override for nodes with native sync implementations.

        Args:
            context: Execution context.

        Returns:
            NodeResult with output data.
        """
        import asyncio
        return asyncio.run(self.execute_async(context))


class LLMNode(WorkflowNode):
    """A workflow node that calls an LLM provider with a prompt template.

    The prompt supports ``{variable}`` placeholders that are substituted
    from the accumulated context data (input_data + previous_outputs).

    Args:
        name: Node identifier.
        prompt: Prompt template with optional ``{variable}`` placeholders.
        provider: Provider name to use (overrides workflow config default).
        is_critical: Whether node failure aborts the workflow.

    Example::

        node = LLMNode(
            name="summarize",
            prompt="Summarize in one sentence: {text}",
        )
    """

    def __init__(
        self,
        name: str,
        prompt: str,
        provider: str | None = None,
        is_critical: bool = True,
    ) -> None:
        super().__init__(name=name, is_critical=is_critical)
        if not prompt:
            raise ValueError("LLMNode requires a non-empty prompt.")
        self.prompt_template = prompt
        self.provider_name = provider

    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Execute the LLM node: render prompt, call provider, return result.

        Args:
            context: Execution context with input data and previous outputs.

        Returns:
            NodeResult with LLM response and token usage.

        Raises:
            NodeError: If prompt rendering or LLM call fails.
        """
        start = time.perf_counter()
        step_id = str(uuid.uuid4())

        try:
            # Build substitution variables: input_data + previous_outputs
            variables = {**context.input_data, **context.previous_outputs}
            rendered_prompt = self.prompt_template.format_map(variables)
        except KeyError as e:
            duration = (time.perf_counter() - start) * 1000
            return NodeResult(
                step_id=step_id,
                status=NodeStatus.FAILED,
                output=None,
                error=f"Missing template variable: {e}",
                duration_ms=duration,
            )

        try:
            from generative_ai_workflow.plugins.registry import PluginRegistry
            from generative_ai_workflow.providers.base import LLMRequest

            provider_name = self.provider_name or (
                context.config.provider if context.config else "openai"
            )
            provider = PluginRegistry.get_provider(provider_name)

            # Build request from context config
            cfg = context.config
            model = (cfg.model if cfg and cfg.model else None) or (
                context.variables.get("_framework_config", {}).get("default_model", "gpt-4o-mini")
                if isinstance(context.variables.get("_framework_config"), dict)
                else "gpt-4o-mini"
            )
            temperature = (cfg.temperature if cfg and cfg.temperature is not None else None) or 0.7
            max_tokens = (cfg.max_tokens if cfg and cfg.max_tokens is not None else None) or 1024

            request = LLMRequest(
                prompt=rendered_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = await provider.complete_async(request)
            duration = (time.perf_counter() - start) * 1000

            return NodeResult(
                step_id=step_id,
                status=NodeStatus.COMPLETED,
                output={f"{self.name}_output": response.content, "llm_response": response.content},
                error=None,
                duration_ms=duration,
                token_usage=response.usage,
            )

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return NodeResult(
                step_id=step_id,
                status=NodeStatus.FAILED,
                output=None,
                error=str(e),
                duration_ms=duration,
            )


class TransformNode(WorkflowNode):
    """A workflow node that applies a pure Python transformation to data.

    Args:
        name: Node identifier.
        transform: Callable that takes a dict and returns a dict.
        is_critical: Whether node failure aborts the workflow.

    Example::

        node = TransformNode(
            name="prepare",
            transform=lambda data: {"prompt_input": data["text"].strip()},
        )
    """

    def __init__(
        self,
        name: str,
        transform: Callable[[dict[str, Any]], dict[str, Any]],
        is_critical: bool = True,
    ) -> None:
        super().__init__(name=name, is_critical=is_critical)
        self.transform = transform

    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Apply the transform function to the accumulated context data.

        Args:
            context: Execution context with input data and previous outputs.

        Returns:
            NodeResult with transformed output.

        Raises:
            NodeError: If the transform callable raises an exception.
        """
        start = time.perf_counter()
        step_id = str(uuid.uuid4())

        try:
            combined = {**context.input_data, **context.previous_outputs}
            result = self.transform(combined)
            duration = (time.perf_counter() - start) * 1000

            return NodeResult(
                step_id=step_id,
                status=NodeStatus.COMPLETED,
                output=result,
                error=None,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return NodeResult(
                step_id=step_id,
                status=NodeStatus.FAILED,
                output=None,
                error=f"Transform failed: {e}",
                duration_ms=duration,
            )
