"""
Contract: StableDiffusionNode public interface.

This file defines the public API contract for StableDiffusionNode.
Implementation must satisfy all method signatures, docstrings, and
validation rules described here.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

# Reference existing framework types — do NOT modify these.
from generative_ai_workflow.workflow import NodeContext, NodeResult
from generative_ai_workflow.node import WorkflowNode

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Output data contract
# ---------------------------------------------------------------------------


class GeneratedImage(BaseModel):
    """Output record for a single image generation execution.

    Produced by StableDiffusionNode on successful completion and included
    in NodeResult.output under the key "generated_image".

    Attributes:
        file_path: Absolute path to the UUID-named PNG file on disk.
        image_bytes: Raw PNG-encoded bytes of the generated image.
        width: Actual width of the generated image in pixels.
        height: Actual height of the generated image in pixels.
        generation_duration_ms: Wall-clock time of the generation call, ms.
        model_id: Model identifier used (echoed from GenerationConfig).
        inference_steps: Denoising steps actually used.
        guidance_scale: Guidance scale actually used.
        device_type: Device used for inference: "cuda", "mps", or "cpu".

    Example::

        # Access from a downstream node's context:
        img: GeneratedImage = context.previous_outputs["render"]["generated_image"]
        print(img.file_path)           # /abs/path/<uuid>.png
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
    device_type: str  # Literal["cuda", "mps", "cpu"]

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Node contract
# ---------------------------------------------------------------------------


class StableDiffusionNodeContract(WorkflowNode):
    """Contract (abstract specification) for StableDiffusionNode.

    Concrete implementation lives in generative_ai_workflow/node.py alongside
    LLMNode and TransformNode.

    Construction Contract:
        StableDiffusionNode(
            name: str,
            prompt: str,
            model_id: str,
            width: int = 512,
            height: int = 512,
            num_inference_steps: int = 20,
            guidance_scale: float = 7.5,
            output_dir: str = "./generated_images",
            is_critical: bool = True,
        )

    Raises:
        ValueError: If any construction parameter fails validation:
            - name is empty
            - prompt is empty
            - model_id is empty
            - width or height are not positive multiples of 8
            - num_inference_steps < 1
            - guidance_scale < 0.0

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

    @abstractmethod
    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Execute image generation asynchronously.

        Behaviour:
        1. Substitute {variable} placeholders in the prompt template from
           context.input_data + context.previous_outputs (same as LLMNode).
        2. If substitution fails (missing variable), return NodeResult with
           status=FAILED and a descriptive error message.
        3. If rendered prompt is empty after substitution, return NodeResult
           with status=FAILED.
        4. Retrieve or create the shared model singleton via ModelRegistry.
        5. Run inference under a threading.Lock (serialized per model_id).
        6. Save the generated image as <uuid>.png in output_dir.
        7. Return NodeResult with status=COMPLETED and output dict:
               {
                   "generated_image": GeneratedImage(...),
                   "image_file_path": "/abs/path/<uuid>.png",
                   "image_bytes": b"\\x89PNG...",
               }
        8. On any error during generation, return NodeResult with
           status=FAILED and a descriptive error message. NEVER raise
           an unhandled exception to the caller.
        9. Emit structured log events at start, completion, and failure
           via generative_ai_workflow.observability.logging.get_logger().
        10. Record generation_duration_ms in the structured log and in
            the returned GeneratedImage.

        Args:
            context: Execution context with input_data and previous_outputs.

        Returns:
            NodeResult with status COMPLETED (success) or FAILED (any error).
            Never raises.

        Note:
            This method MUST NOT make external network calls during inference
            (FR-006). Model weights must be pre-loaded from local storage.
        """
        ...


# ---------------------------------------------------------------------------
# NodeResult output contract (documented as constants for reference)
# ---------------------------------------------------------------------------

#: Key in NodeResult.output containing the GeneratedImage on success.
OUTPUT_KEY_GENERATED_IMAGE = "generated_image"

#: Key in NodeResult.output containing the absolute file path string.
OUTPUT_KEY_FILE_PATH = "image_file_path"

#: Key in NodeResult.output containing the raw PNG bytes.
OUTPUT_KEY_IMAGE_BYTES = "image_bytes"
