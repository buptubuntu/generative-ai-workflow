"""Workflow step abstractions and built-in step types.

Defines the WorkflowStep ABC that users and plugins implement, plus
the built-in LLMStep and TransformStep implementations.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from generative_ai_workflow.exceptions import StepError
from generative_ai_workflow.workflow import StepContext, StepResult, StepStatus

if TYPE_CHECKING:
    pass


class WorkflowStep(ABC):
    """Abstract base class for workflow step implementations.

    Implement this interface to add custom step behaviors (API calls,
    data validation, external service integrations, etc.) without
    modifying the framework.

    Attributes:
        name: Human-readable step identifier used in metrics and logs.
        is_critical: If True (default), step failure aborts the workflow.
                     If False, failure is logged and execution continues.

    Example::

        class SentimentStep(WorkflowStep):
            name = "sentiment_analysis"

            async def execute_async(self, context: StepContext) -> StepResult:
                text = context.input_data.get("text", "")
                sentiment = analyze(text)
                return StepResult(
                    step_id=context.step_id,
                    status=StepStatus.COMPLETED,
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
            raise ValueError("WorkflowStep must have a non-empty name.")
        self.is_critical = is_critical

    @abstractmethod
    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute this step asynchronously.

        Args:
            context: Execution context including input data, variables,
                     and outputs from previous steps.

        Returns:
            StepResult with output data and execution metadata.

        Raises:
            StepError: On unrecoverable step failure.
        """
        ...

    def execute(self, context: StepContext) -> StepResult:
        """Execute this step synchronously.

        Default implementation wraps execute_async in an event loop.
        Override for steps with native sync implementations.

        Args:
            context: Execution context.

        Returns:
            StepResult with output data.
        """
        import asyncio
        return asyncio.run(self.execute_async(context))


class LLMStep(WorkflowStep):
    """A workflow step that calls an LLM provider with a prompt template.

    The prompt supports ``{variable}`` placeholders that are substituted
    from the accumulated context data (input_data + previous_outputs).

    Args:
        name: Step identifier.
        prompt: Prompt template with optional ``{variable}`` placeholders.
        provider: Provider name to use (overrides workflow config default).
        is_critical: Whether step failure aborts the workflow.

    Example::

        step = LLMStep(
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
            raise ValueError("LLMStep requires a non-empty prompt.")
        self.prompt_template = prompt
        self.provider_name = provider

    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute the LLM step: render prompt, call provider, return result.

        Args:
            context: Execution context with input data and previous outputs.

        Returns:
            StepResult with LLM response and token usage.

        Raises:
            StepError: If prompt rendering or LLM call fails.
        """
        start = time.perf_counter()
        step_id = str(uuid.uuid4())

        try:
            # Build substitution variables: input_data + previous_outputs
            variables = {**context.input_data, **context.previous_outputs}
            rendered_prompt = self.prompt_template.format_map(variables)
        except KeyError as e:
            duration = (time.perf_counter() - start) * 1000
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
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

            return StepResult(
                step_id=step_id,
                status=StepStatus.COMPLETED,
                output={f"{self.name}_output": response.content, "llm_response": response.content},
                error=None,
                duration_ms=duration,
                token_usage=response.usage,
            )

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                output=None,
                error=str(e),
                duration_ms=duration,
            )


class TransformStep(WorkflowStep):
    """A workflow step that applies a pure Python transformation to data.

    Args:
        name: Step identifier.
        transform: Callable that takes a dict and returns a dict.
        is_critical: Whether step failure aborts the workflow.

    Example::

        step = TransformStep(
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

    async def execute_async(self, context: StepContext) -> StepResult:
        """Apply the transform function to the accumulated context data.

        Args:
            context: Execution context with input data and previous outputs.

        Returns:
            StepResult with transformed output.

        Raises:
            StepError: If the transform callable raises an exception.
        """
        start = time.perf_counter()
        step_id = str(uuid.uuid4())

        try:
            combined = {**context.input_data, **context.previous_outputs}
            result = self.transform(combined)
            duration = (time.perf_counter() - start) * 1000

            return StepResult(
                step_id=step_id,
                status=StepStatus.COMPLETED,
                output=result,
                error=None,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                output=None,
                error=f"Transform failed: {e}",
                duration_ms=duration,
            )
