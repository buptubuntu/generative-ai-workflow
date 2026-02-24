# Data Model: Stable Diffusion Node

**Date**: 2026-02-23
**Branch**: `001-stable-diffusion-node`

---

## Overview

Three primary entities support the `StableDiffusionNode` feature. All are Pydantic `BaseModel` subclasses consistent with existing framework patterns (`TokenUsage`, `LLMRequest`, `LLMResponse` in `providers/base.py`).

---

## Entity 1: `GenerationConfig`

Encapsulates all user-facing parameters for a single image generation call. Constructed at `StableDiffusionNode` construction time and validated eagerly.

```python
class GenerationConfig(BaseModel):
    """Parameters controlling a single image generation run.

    Attributes:
        model_id: HuggingFace model ID string (e.g., "runwayml/stable-diffusion-v1-5")
                  or an absolute/relative local filesystem path to a model directory.
                  Auto-detected at load time.
        width: Output image width in pixels. Must be a positive multiple of 8.
               Default: 512 (SD v1.x native resolution).
        height: Output image height in pixels. Must be a positive multiple of 8.
                Default: 512 (SD v1.x native resolution).
        num_inference_steps: Number of denoising steps. Higher = better quality, slower.
                             Must be >= 1. Default: 20.
        guidance_scale: Classifier-free guidance scale. Higher = more prompt-adherent,
                        less diverse. Must be >= 0.0. Default: 7.5.
        output_dir: Directory where generated images are saved. Created automatically
                    if it does not exist. Default: "./generated_images".
    """
    model_id: str = Field(min_length=1)
    width: int = Field(default=512, ge=8, multiple_of=8)
    height: int = Field(default=512, ge=8, multiple_of=8)
    num_inference_steps: int = Field(default=20, ge=1)
    guidance_scale: float = Field(default=7.5, ge=0.0)
    output_dir: str = Field(default="./generated_images", min_length=1)
```

**Validation rules**:
- `model_id`: non-empty string
- `width`, `height`: positive integer, multiple of 8 (VAE/UNet architectural constraint)
- `num_inference_steps`: positive integer (≥1)
- `guidance_scale`: non-negative float (0.0 disables classifier-free guidance)
- `output_dir`: non-empty string (path created if absent at first run)

**State transitions**: Immutable after construction — all fields are validated once at `StableDiffusionNode.__init__`.

---

## Entity 2: `GeneratedImage`

Represents the output of one successful image generation run. Returned in `NodeResult.output` under a well-known key.

```python
class GeneratedImage(BaseModel):
    """Output record for a single image generation execution.

    Attributes:
        file_path: Absolute path to the saved PNG file (UUID-named).
        image_bytes: Raw PNG-encoded bytes of the generated image.
        width: Actual width of the generated image in pixels.
        height: Actual height of the generated image in pixels.
        generation_duration_ms: Wall-clock time for the generation call in milliseconds.
        model_id: Model identifier used for this generation (echoed from config).
        inference_steps: Actual inference steps used.
        guidance_scale: Actual guidance scale used.
        device_type: Device used for inference: "cuda", "mps", or "cpu".
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
```

**Key in `NodeResult.output`**:
```python
{
    "generated_image": GeneratedImage(...),          # structured output
    "image_file_path": "/abs/path/to/<uuid>.png",    # convenience key for downstream nodes
    "image_bytes": b"\x89PNG...",                    # raw bytes for in-memory processing
}
```

**Relationships**:
- Produced by `StableDiffusionNode.execute_async()` on success.
- Consumed by downstream `WorkflowNode` instances via `context.previous_outputs`.

---

## Entity 3: `ModelRegistry` (internal)

A module-level singleton registry that manages the lifecycle of loaded `StableDiffusionPipeline` instances. Not a Pydantic model — a plain Python class with class-level state.

```
ModelRegistry
├── _instances: dict[str, _PipelineHolder]   # keyed by model_id (normalized)
├── _class_lock: threading.Lock              # guards singleton creation
└── get(model_id: str) -> _PipelineHolder   # double-checked locking factory

_PipelineHolder
├── pipeline: StableDiffusionPipeline       # loaded once; weights shared
├── _gpu_lock: threading.Lock               # serializes inference calls
├── device: str                             # "cuda" | "mps" | "cpu"
├── dtype: torch.dtype                      # float16 | float32
└── run(prompt, width, height, steps, guidance_scale) -> bytes
```

**Lifecycle**:
1. `ModelRegistry.get(model_id)` called from `StableDiffusionNode.execute_async`.
2. If `model_id` not yet loaded → acquire `_class_lock` → load pipeline → cache in `_instances`.
3. Subsequent calls for the same `model_id` return the cached `_PipelineHolder` without re-loading.
4. `_PipelineHolder.run()` clones the scheduler per call (`from_pipe()`), acquires `_gpu_lock`, runs inference.
5. No explicit eviction — registry lives for the process lifetime (consistent with `PluginRegistry` pattern).

**Thread safety invariants**:
- `_class_lock` prevents concurrent double-initialization of the same model.
- `_gpu_lock` (per `_PipelineHolder`) prevents concurrent inference on the same GPU.
- Multiple models with different `model_id` values can be loaded concurrently (separate locks).

---

## Entity Relationships

```
StableDiffusionNode
    │
    ├── has-a ──► GenerationConfig         (1:1, set at construction)
    │
    ├── uses ───► ModelRegistry            (module singleton)
    │                  └── holds ──► _PipelineHolder (1 per model_id)
    │
    └── produces ► GeneratedImage          (0..1 per execution; 0 on failure)
                        └── included in ► NodeResult.output
```

---

## Output Dictionary Contract

On success, `NodeResult.output` contains:

| Key | Type | Description |
|-----|------|-------------|
| `generated_image` | `GeneratedImage` | Full structured output |
| `image_file_path` | `str` | Absolute path of saved PNG (convenience) |
| `image_bytes` | `bytes` | Raw PNG bytes (convenience) |

On failure, `NodeResult.output` is `None` and `NodeResult.error` contains a descriptive message.
