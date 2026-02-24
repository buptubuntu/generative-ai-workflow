"""Stable Diffusion model registry.

Manages shared StableDiffusionPipeline singleton instances per model
identifier with thread-safe double-checked locking. Provides serialized
GPU inference via a per-instance threading.Lock.

Only available when the ``[stable-diffusion]`` optional extras are installed::

    pip install "generative-ai-workflow[stable-diffusion]"
"""

from __future__ import annotations

import threading
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Device / dtype detection (T002)
# ---------------------------------------------------------------------------


def _detect_device_and_dtype() -> tuple[str, Any]:
    """Auto-detect the best available compute device and matching dtype.

    Priority order: CUDA (float16) → Apple MPS (float32) → CPU (float32).

    MPS uses float32 because the float16 ``LayerNormKernelImpl`` is not fully
    implemented in diffusers ≥0.36 for Apple Silicon (research.md Decision 2).

    Returns:
        Tuple of ``(device_name, torch_dtype)`` where *device_name* is one of
        ``"cuda"``, ``"mps"``, or ``"cpu"``.
    """
    import torch

    if torch.cuda.is_available():
        return "cuda", torch.float16
    if torch.backends.mps.is_available():
        return "mps", torch.float32
    return "cpu", torch.float32


# ---------------------------------------------------------------------------
# GenerationConfig (T005)
# ---------------------------------------------------------------------------


class GenerationConfig(BaseModel):
    """Parameters controlling a single image generation run.

    Encapsulates all user-facing settings for one ``StableDiffusionNode``
    execution. Immutable after construction — validated once at node ``__init__``.

    Attributes:
        model_id: HuggingFace Hub model ID (e.g.,
                  ``"runwayml/stable-diffusion-v1-5"``) or an absolute /
                  relative local filesystem path to a directory containing
                  ``model_index.json``. Auto-detected at load time.
        width: Output image width in pixels. Must be a positive multiple of 8.
               Default: 512 (SD v1.x native resolution).
        height: Output image height in pixels. Must be a positive multiple of 8.
                Default: 512.
        num_inference_steps: Number of denoising steps. Higher = better
                             quality, slower. Must be ≥ 1. Default: 20.
        guidance_scale: Classifier-free guidance scale. 0.0 disables
                        guidance. Must be ≥ 0.0. Default: 7.5.
        output_dir: Directory where generated PNG files are saved. Created
                    automatically if absent. Default: ``"./generated_images"``.

    Example::

        config = GenerationConfig(
            model_id="runwayml/stable-diffusion-v1-5",
            width=768,
            height=512,
            num_inference_steps=30,
        )
    """

    model_id: str = Field(min_length=1)
    width: int = Field(default=512, ge=8, multiple_of=8)
    height: int = Field(default=512, ge=8, multiple_of=8)
    num_inference_steps: int = Field(default=20, ge=1)
    guidance_scale: float = Field(default=7.5, ge=0.0)
    output_dir: str = Field(default="./generated_images", min_length=1)


# ---------------------------------------------------------------------------
# _PipelineHolder (T003)
# ---------------------------------------------------------------------------


class _PipelineHolder:
    """Thread-safe wrapper around a loaded ``StableDiffusionPipeline``.

    Serializes GPU inference via a ``threading.Lock``. Clones the scheduler
    per call via ``from_pipe()`` to isolate stateful denoising counters and
    prevent ``IndexError`` / silent output corruption under concurrency
    (research.md Decision 3).

    Attributes:
        device: Device this pipeline runs on: ``"cuda"``, ``"mps"``, or
                ``"cpu"``.
    """

    def __init__(self, pipeline: Any, device: str) -> None:
        self._pipeline = pipeline
        self._device = device
        self._gpu_lock = threading.Lock()

    @property
    def device(self) -> str:
        """Device this pipeline runs on: ``"cuda"``, ``"mps"``, or ``"cpu"``."""
        return self._device

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
        import io

        from diffusers import StableDiffusionPipeline

        # Clone scheduler per call to avoid stateful denoising counter conflicts
        fresh_scheduler = self._pipeline.scheduler.from_config(
            self._pipeline.scheduler.config
        )
        request_pipe = StableDiffusionPipeline.from_pipe(
            self._pipeline, scheduler=fresh_scheduler
        )

        with self._gpu_lock:
            result = request_pipe(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )

        pil_image = result.images[0]
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        return buf.getvalue()


# ---------------------------------------------------------------------------
# ModelRegistry (T004)
# ---------------------------------------------------------------------------


class ModelRegistry:
    """Process-level singleton registry for ``StableDiffusionPipeline`` instances.

    Manages model lifecycle: the first call for a given ``model_id`` loads
    the pipeline (may take 30–120 s); subsequent calls return the cached
    ``_PipelineHolder`` immediately without re-loading.

    Uses double-checked locking so concurrent first-calls for the *same*
    ``model_id`` are safe, while concurrent calls for *different* model IDs
    proceed in parallel (separate lock domains).

    Thread-safety guarantees:
        - ``get()`` is safe to call concurrently from multiple threads.
        - Different ``model_id`` values can be loaded concurrently.
        - Same ``model_id``: only one thread performs the load; others wait
          and receive the cached holder on return.

    Note:
        This is an intentional module-level singleton that follows the same
        pattern as ``PluginRegistry``. See ``plan.md`` Complexity Tracking for
        the justified deviation from pure DI (FR-001 forbids engine changes).

    Example::

        holder = ModelRegistry.get("runwayml/stable-diffusion-v1-5")
        png_bytes = holder.run(
            prompt="a red apple on a wooden table",
            width=512,
            height=512,
            num_inference_steps=20,
            guidance_scale=7.5,
        )
    """

    _instances: dict[str, _PipelineHolder] = {}
    _class_lock: threading.Lock = threading.Lock()

    @classmethod
    def get(cls, model_id: str) -> _PipelineHolder:
        """Return the ``_PipelineHolder`` for *model_id*, loading if necessary.

        Args:
            model_id: HuggingFace Hub model ID string (e.g.,
                      ``"runwayml/stable-diffusion-v1-5"``) or an absolute /
                      relative local filesystem path containing
                      ``model_index.json``. Auto-detected.

        Returns:
            A ``_PipelineHolder`` ready to run inference.

        Raises:
            ValueError: If *model_id* is empty.
            RuntimeError: If the model cannot be loaded (path not found,
                          unsupported architecture, OOM during load).
        """
        if not model_id:
            raise ValueError("model_id must be non-empty.")

        # Fast path — already cached (no lock needed for reads)
        if model_id in cls._instances:
            return cls._instances[model_id]

        # Slow path — double-checked locking
        with cls._class_lock:
            if model_id in cls._instances:
                return cls._instances[model_id]

            import torch
            from diffusers import StableDiffusionPipeline

            device, dtype = _detect_device_and_dtype()

            try:
                pipeline = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    variant="fp16" if dtype == torch.float16 else None,
                    use_safetensors=True,
                    safety_checker=None,
                )
                pipeline = pipeline.to(device)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load model {model_id!r}: {exc}"
                ) from exc

            holder = _PipelineHolder(pipeline, device)
            cls._instances[model_id] = holder
            return holder

    @classmethod
    def clear(cls) -> None:
        """Remove all cached pipeline instances.

        Intended for use in tests to reset registry state between test cases.
        NOT safe to call while inference is in progress.
        """
        with cls._class_lock:
            cls._instances.clear()

    @classmethod
    def loaded_model_ids(cls) -> list[str]:
        """Return the list of currently loaded model identifiers.

        Useful for observability (logging loaded models at startup) and tests.
        """
        return list(cls._instances.keys())
