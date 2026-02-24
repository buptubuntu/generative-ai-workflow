# Research: Stable Diffusion Node

**Date**: 2026-02-23
**Branch**: `001-stable-diffusion-node`
**Resolved**: All NEEDS CLARIFICATION items from Technical Context

---

## Decision 1: Pipeline Loading API (FR-005)

**Decision**: Use `StableDiffusionPipeline.from_pretrained(model_id_or_path, ...)` — it auto-detects whether the argument is a HuggingFace Hub model ID string or a local filesystem directory path containing `model_index.json`. No separate code paths needed.

**Rationale**: The `from_pretrained()` method is the canonical entry point for both scenarios. When given a valid local directory, it skips all network calls entirely. When given a Hub model ID (e.g., `"runwayml/stable-diffusion-v1-5"`), it downloads to the HuggingFace cache directory. This satisfies FR-005 (auto-detect format) and FR-006 (no network calls during inference — model is cached locally before the node runs).

**Alternatives considered**:
- Separate code path for path vs Hub ID: rejected — unnecessary complexity, `from_pretrained()` already handles both.
- `from_single_file()` for `.ckpt` / `.safetensors` single-file models: deferred — single-file format is out of scope for this feature; directory-based models are the standard.

**Key API details**:
```python
pipe = StableDiffusionPipeline.from_pretrained(
    model_id_or_path,                             # Hub ID or local directory path
    torch_dtype=dtype,                            # float16 or float32
    variant="fp16" if dtype == torch.float16 else None,
    use_safetensors=True,
    safety_checker=None,
)
```

---

## Decision 2: Device Auto-Detection (FR-005, ModelConfig.device_preference)

**Decision**: Auto-detect in priority order: CUDA → Apple MPS → CPU. Use `float16` for CUDA, `float32` for MPS and CPU.

**Rationale**: As of diffusers 0.36.0, MPS `float16` raises `LayerNormKernelImpl not implemented for 'Half'` for some diffusion ops. `float32` is required for correctness on Apple Silicon. CPU uses `float32` by default (no performance benefit from fp16 on CPU). CUDA `float16` is the standard consumer GPU setting with ~2.6x speedup vs fp32.

**Pattern**:
```python
def _detect_device_and_dtype() -> tuple[str, torch.dtype]:
    if torch.cuda.is_available():
        return "cuda", torch.float16
    elif torch.backends.mps.is_available():
        return "mps", torch.float32
    return "cpu", torch.float32
```

**Alternatives considered**:
- Allow user to force device: supported via `ModelConfig.device_preference`; auto-detect is the default.
- `bfloat16` on Ampere+ GPUs: valid optimization but adds complexity; default to `float16` for broad compatibility; document `bfloat16` as advanced config.

---

## Decision 3: Thread Safety — Shared Singleton with Serialized Inference (FR-013)

**Decision**: Use double-checked locking for singleton creation; share model weights across nodes via a single loaded pipeline; clone the scheduler per inference call via `from_pipe()`; serialize GPU inference with `threading.Lock()`.

**Rationale**: `StableDiffusionPipeline` is **not thread-safe** — the scheduler (e.g., `PNDMScheduler`, `DDIMScheduler`) is stateful (mutable `counter`, `timesteps`). Concurrent calls corrupt each other's denoising state, causing `IndexError` or silent output corruption. The official diffusers solution is `from_pipe()`, which shares the heavy GPU model weights but gives each call a fresh scheduler instance. A `threading.Lock` serializes GPU use (one inference at a time).

**Pattern**:
```python
# Per-call: clone scheduler (lightweight, no GPU memory)
fresh_scheduler = self._pipeline.scheduler.from_config(
    self._pipeline.scheduler.config
)
request_pipe = StableDiffusionPipeline.from_pipe(
    self._pipeline, scheduler=fresh_scheduler
)

# Serialize GPU access
with self._gpu_lock:
    result = request_pipe(prompt=..., ...)
```

**Alternatives considered**:
- Separate pipeline instance per node: rejected — reloads GBs of weights per node; prohibitive memory usage.
- No locking (assume single-threaded workflows): rejected — FR-013 explicitly requires thread safety.
- `asyncio.Lock` instead of `threading.Lock`: rejected — `execute_async` runs inside `asyncio.run_in_executor`, which spawns threads; a `threading.Lock` is the correct primitive.

---

## Decision 4: Async Integration (execute_async contract)

**Decision**: Wrap blocking GPU inference in `asyncio.get_event_loop().run_in_executor(None, ...)` to remain non-blocking in the asyncio context, consistent with how `LLMNode.execute_async` calls the provider.

**Rationale**: The `WorkflowNode` contract requires `execute_async`. Stable Diffusion inference is a blocking CPU/GPU computation. Using `run_in_executor` offloads it to the default thread pool, freeing the event loop. This matches the framework's existing async pattern.

---

## Decision 5: Output — PIL Image → PNG Bytes + File

**Decision**: Convert `result.images[0]` (PIL `Image`) to raw PNG bytes via `io.BytesIO`; also save to `output_dir/<uuid>.png`. Both the file path and raw bytes are included in `NodeResult.output`.

**Rationale**: Downstream nodes may need either: a file path (for tools that read from disk) or raw bytes (for in-memory processing). Providing both is the most composable output format. UUID filename guarantees no overwrite collisions (per clarification Q3).

```python
pil_image = result.images[0]
buf = io.BytesIO()
pil_image.save(buf, format="PNG")
png_bytes = buf.getvalue()

output_path = output_dir / f"{uuid.uuid4()}.png"
pil_image.save(str(output_path))
```

---

## Decision 6: Dependency Packaging

**Decision**: Package SD dependencies as an optional extras group `[stable-diffusion]` in `pyproject.toml`. Core framework installs remain lightweight.

**Rationale**: `torch` + `diffusers` require 2–10+ GB of storage depending on CUDA variant. Making them optional extras follows Python best practices (e.g., `requests[security]`, `pandas[parquet]`) and ensures existing users are unaffected.

**Pinned version ranges**:
```toml
[project.optional-dependencies]
stable-diffusion = [
    "diffusers>=0.31.0,<1.0",
    "transformers>=4.41.2,<5.0",
    "accelerate>=0.31.0",
    "safetensors>=0.3.1",
    "Pillow>=9.0",
    "torch>=2.0.0",
]
```

**Install**: `pip install generative-ai-workflow[stable-diffusion]`

---

## Decision 7: Default Generation Parameters

**Decision**: `width=512`, `height=512`, `num_inference_steps=20`, `guidance_scale=7.5`.

**Rationale**:
- 512×512 is the native training resolution for SD v1.x; other sizes work but quality may degrade.
- 20 steps balances quality and speed (SC-002 references 20 steps).
- `guidance_scale=7.5` is the diffusers default and the widest-tested value for SD v1.x.
- All dimensions must be multiples of 8 (VAE/UNet constraint); validated at construction time.

---

## NEEDS CLARIFICATION — All Resolved

All items from Technical Context are now resolved. No remaining unknowns.
