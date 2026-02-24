"""
Contract: ModelRegistry public interface.

Defines the public API for the model registry that manages shared
StableDiffusionPipeline singleton instances with thread-safe access.

Implementation lives in generative_ai_workflow/sd_model_registry.py.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Protocol


# ---------------------------------------------------------------------------
# Pipeline holder protocol
# ---------------------------------------------------------------------------


class PipelineHolder(Protocol):
    """Protocol for a loaded pipeline ready to run inference.

    Concrete implementation wraps StableDiffusionPipeline with a threading.Lock
    that serializes inference calls (one at a time per model).
    """

    @property
    def device(self) -> str:
        """Device this pipeline runs on: "cuda", "mps", or "cpu"."""
        ...

    def run(
        self,
        prompt: str,
        width: int,
        height: int,
        num_inference_steps: int,
        guidance_scale: float,
    ) -> bytes:
        """Run inference and return raw PNG bytes.

        Clones the scheduler per call to isolate stateful denoising counters,
        then acquires the GPU lock before calling the pipeline.

        Args:
            prompt: Rendered (substituted) text prompt.
            width: Image width in pixels.
            height: Image height in pixels.
            num_inference_steps: Number of denoising steps.
            guidance_scale: Classifier-free guidance scale.

        Returns:
            Raw PNG-encoded bytes of the generated image.

        Raises:
            RuntimeError: If inference fails (e.g., OOM, corrupt model).
        """
        ...


# ---------------------------------------------------------------------------
# Registry interface
# ---------------------------------------------------------------------------


class ModelRegistryInterface(ABC):
    """Abstract interface for the model singleton registry.

    The concrete implementation (ModelRegistry in sd_model_registry.py)
    uses a module-level dict guarded by a class-level threading.Lock for
    double-checked locking on first access per model_id.

    Thread safety guarantees:
        - get() is safe to call concurrently from multiple threads.
        - Different model_ids can be loaded concurrently (separate locks).
        - Same model_id: only one thread performs the load; others wait.

    Example::

        holder = ModelRegistry.get("runwayml/stable-diffusion-v1-5")
        png_bytes = holder.run(
            prompt="a red apple",
            width=512,
            height=512,
            num_inference_steps=20,
            guidance_scale=7.5,
        )
    """

    @classmethod
    @abstractmethod
    def get(cls, model_id: str) -> PipelineHolder:
        """Return the PipelineHolder for model_id, loading it if necessary.

        The first call for a given model_id loads the pipeline (may take
        30–120s depending on hardware and model size). Subsequent calls
        return the cached holder immediately.

        Args:
            model_id: HuggingFace Hub model ID string (e.g.,
                      "runwayml/stable-diffusion-v1-5") or an absolute /
                      relative local filesystem path to a model directory
                      containing model_index.json. Auto-detected.

        Returns:
            A PipelineHolder ready to run inference.

        Raises:
            RuntimeError: If the model cannot be loaded (path not found,
                          unsupported model architecture, OOM during load).
            ValueError: If model_id is empty.
        """
        ...

    @classmethod
    @abstractmethod
    def clear(cls) -> None:
        """Remove all cached pipeline instances.

        Intended for use in tests to reset registry state between test cases.
        NOT safe to call while inference is in progress.
        """
        ...

    @classmethod
    @abstractmethod
    def loaded_model_ids(cls) -> list[str]:
        """Return the list of currently loaded model identifiers.

        Useful for observability (logging loaded models at startup) and tests.
        """
        ...
