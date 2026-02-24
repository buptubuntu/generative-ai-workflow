"""Workflow node abstractions and built-in node types.

Defines the WorkflowNode ABC that users and plugins implement, plus
the built-in LLMNode and TransformNode implementations.
"""

from __future__ import annotations

import asyncio
import io
import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from pydantic import BaseModel, Field

from generative_ai_workflow.exceptions import NodeError
from generative_ai_workflow.observability.logging import get_logger
from generative_ai_workflow.sd_model_registry import GenerationConfig, ModelRegistry
from generative_ai_workflow.workflow import NodeContext, NodeResult, NodeStatus

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# GeneratedImage — output data contract (T006)
# ---------------------------------------------------------------------------


class GeneratedImage(BaseModel):
    """Output record for a single image generation execution.

    Produced by ``StableDiffusionNode`` on successful completion and included
    in ``NodeResult.output`` under the key ``"generated_image"``.

    Attributes:
        file_path: Absolute path to the UUID-named PNG file on disk.
        image_bytes: Raw PNG-encoded bytes of the generated image.
        width: Actual width of the generated image in pixels.
        height: Actual height of the generated image in pixels.
        generation_duration_ms: Wall-clock time of the generation call, ms.
        model_id: Model identifier used (echoed from ``GenerationConfig``).
        inference_steps: Denoising steps actually used.
        guidance_scale: Guidance scale actually used.
        device_type: Device used for inference: ``"cuda"``, ``"mps"``, or
                     ``"cpu"``.

    Example::

        # Access from a downstream node's context:
        img: GeneratedImage = context.previous_outputs["render"]["generated_image"]
        print(img.file_path)               # /abs/path/<uuid>.png
        print(img.generation_duration_ms)  # e.g. 12341.5
    """

    file_path: str
    image_bytes: bytes
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    generation_duration_ms: float = Field(ge=0.0)
    model_id: str
    inference_steps: int = Field(ge=1)
    guidance_scale: float = Field(ge=0.0)
    device_type: str  # "cuda" | "mps" | "cpu"

    model_config = {"arbitrary_types_allowed": True}


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
            context: Execution context including input data
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
            model = (cfg.model if cfg and cfg.model else None) or "gpt-4o-mini"
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


# ---------------------------------------------------------------------------
# StableDiffusionNode — local text-to-image generation (T011–T021)
# ---------------------------------------------------------------------------

#: Key in NodeResult.output containing the GeneratedImage on success.
OUTPUT_KEY_GENERATED_IMAGE = "generated_image"

#: Key in NodeResult.output containing the absolute file path string.
OUTPUT_KEY_FILE_PATH = "image_file_path"

#: Key in NodeResult.output containing the raw PNG bytes.
OUTPUT_KEY_IMAGE_BYTES = "image_bytes"


class StableDiffusionNode(WorkflowNode):
    """A workflow node that generates images locally via Stable Diffusion.

    Runs text-to-image inference entirely on-device using a shared
    ``ModelRegistry`` singleton per model identifier.  The prompt supports
    ``{variable}`` placeholder substitution identical to ``LLMNode``.

    Requires the ``[stable-diffusion]`` optional extras::

        pip install "generative-ai-workflow[stable-diffusion]"

    Args:
        name: Node identifier used in logs and metrics.
        prompt: Prompt template with optional ``{variable}`` placeholders.
        model_id: HuggingFace Hub model ID (e.g.,
                  ``"runwayml/stable-diffusion-v1-5"``) or local directory
                  path containing ``model_index.json``.  Auto-detected.
        width: Output image width in pixels.  Must be a positive multiple
               of 8.  Default: 512.
        height: Output image height in pixels.  Must be a positive multiple
                of 8.  Default: 512.
        num_inference_steps: Number of denoising steps.  Must be ≥ 1.
                             Default: 20.
        guidance_scale: Classifier-free guidance scale.  Must be ≥ 0.0.
                        Default: 7.5.
        output_dir: Directory for saved PNG files.  Created automatically
                    if absent.  Default: ``"./generated_images"``.
        is_critical: If ``True`` (default), node failure aborts the workflow.
                     If ``False``, failure is logged and execution continues.

    Raises:
        ValueError: If any construction parameter fails validation.

    Example::

        node = StableDiffusionNode(
            name="render",
            prompt="a {style} painting of {subject}",
            model_id="runwayml/stable-diffusion-v1-5",
            width=512,
            height=512,
            num_inference_steps=20,
            guidance_scale=7.5,
        )
    """

    def __init__(
        self,
        name: str,
        prompt: str,
        model_id: str,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        output_dir: str = "./generated_images",
        is_critical: bool = True,
    ) -> None:
        super().__init__(name=name, is_critical=is_critical)
        if not prompt:
            raise ValueError("StableDiffusionNode requires a non-empty prompt.")

        self.prompt_template = prompt

        # Delegate parameter validation to GenerationConfig (T017).
        # Re-raise pydantic ValidationError as ValueError to keep the
        # public constructor contract consistent with LLMNode and FR-011.
        try:
            self._config = GenerationConfig(
                model_id=model_id,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                output_dir=output_dir,
            )
        except Exception as exc:
            raise ValueError(str(exc)) from exc

    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Execute image generation asynchronously.

        Behaviour:

        1. Substitute ``{variable}`` placeholders in the prompt template from
           ``context.input_data`` + ``context.previous_outputs``.
        2. If substitution fails (missing variable), return ``NodeResult``
           with ``status=FAILED`` and a descriptive error message.
        3. If rendered prompt is empty after substitution, return ``NodeResult``
           with ``status=FAILED``.
        4. Retrieve or create the shared model singleton via ``ModelRegistry``.
        5. Run inference under a ``threading.Lock`` (serialized per model_id).
        6. Save the generated image as ``<uuid>.png`` in ``output_dir``.
        7. Return ``NodeResult`` with ``status=COMPLETED`` and output dict::

               {
                   "generated_image": GeneratedImage(...),
                   "image_file_path": "/abs/path/<uuid>.png",
                   "image_bytes": b"\\x89PNG...",
               }

        8. On any error during generation, return ``NodeResult`` with
           ``status=FAILED`` and a descriptive error message.  NEVER raises.
        9. Emits structured log events at start, completion, and failure.
        10. Records ``generation_duration_ms`` in both the log and the
            returned ``GeneratedImage``.

        Args:
            context: Execution context with input_data and previous_outputs.

        Returns:
            ``NodeResult`` with status ``COMPLETED`` (success) or ``FAILED``
            (any error).  Never raises.
        """
        _log = get_logger(__name__).bind(
            node_name=self.name,
            model_id=self._config.model_id,
        )
        start = time.perf_counter()
        step_id = str(uuid.uuid4())

        # ------------------------------------------------------------------ #
        # Step 1–3: Render prompt template                                    #
        # ------------------------------------------------------------------ #
        try:
            variables = {**context.input_data, **context.previous_outputs}
            rendered_prompt = self.prompt_template.format_map(variables)
        except KeyError as exc:
            duration = (time.perf_counter() - start) * 1000
            return NodeResult(
                step_id=step_id,
                status=NodeStatus.FAILED,
                output=None,
                error=f"Missing template variable: {exc}",
                duration_ms=duration,
            )

        if not rendered_prompt.strip():
            duration = (time.perf_counter() - start) * 1000
            return NodeResult(
                step_id=step_id,
                status=NodeStatus.FAILED,
                output=None,
                error="Rendered prompt is empty after template substitution.",
                duration_ms=duration,
            )

        _log.info(
            "stable_diffusion_node.start",
            prompt_length=len(rendered_prompt),
            width=self._config.width,
            height=self._config.height,
            num_inference_steps=self._config.num_inference_steps,
            guidance_scale=self._config.guidance_scale,
        )

        # ------------------------------------------------------------------ #
        # Steps 4–8: Load model, run inference, save file, build result       #
        # ------------------------------------------------------------------ #
        try:
            holder = ModelRegistry.get(self._config.model_id)

            # Run blocking GPU inference in the default thread-pool executor
            # so we don't block the asyncio event loop (research.md Decision 4).
            loop = asyncio.get_running_loop()
            png_bytes: bytes = await loop.run_in_executor(
                None,
                lambda: holder.run(
                    rendered_prompt,
                    self._config.width,
                    self._config.height,
                    self._config.num_inference_steps,
                    self._config.guidance_scale,
                ),
            )

            duration = (time.perf_counter() - start) * 1000

            # Save PNG to output_dir with a UUID filename (research.md Decision 5)
            os.makedirs(self._config.output_dir, exist_ok=True)
            file_name = f"{uuid.uuid4()}.png"
            file_path = os.path.join(
                os.path.abspath(self._config.output_dir), file_name
            )
            with open(file_path, "wb") as fh:
                fh.write(png_bytes)

            generated = GeneratedImage(
                file_path=file_path,
                image_bytes=png_bytes,
                width=self._config.width,
                height=self._config.height,
                generation_duration_ms=duration,
                model_id=self._config.model_id,
                inference_steps=self._config.num_inference_steps,
                guidance_scale=self._config.guidance_scale,
                device_type=holder.device,
            )

            _log.info(
                "stable_diffusion_node.completed",
                file_path=file_path,
                generation_duration_ms=round(duration, 2),
                device_type=holder.device,
                width=self._config.width,
                height=self._config.height,
            )

            return NodeResult(
                step_id=step_id,
                status=NodeStatus.COMPLETED,
                output={
                    OUTPUT_KEY_GENERATED_IMAGE: generated,
                    OUTPUT_KEY_FILE_PATH: file_path,
                    OUTPUT_KEY_IMAGE_BYTES: png_bytes,
                },
                error=None,
                duration_ms=duration,
            )

        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            error_msg = str(exc)
            _log.error(
                "stable_diffusion_node.failed",
                error=error_msg,
                duration_ms=round(duration, 2),
            )
            return NodeResult(
                step_id=step_id,
                status=NodeStatus.FAILED,
                output=None,
                error=error_msg,
                duration_ms=duration,
            )
