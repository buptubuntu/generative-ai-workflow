# Quickstart: Stable Diffusion Node

**Date**: 2026-02-23
**Branch**: `001-stable-diffusion-node`

---

## Prerequisites

1. Install the optional `stable-diffusion` extras:

```bash
pip install "generative-ai-workflow[stable-diffusion]"
# PyTorch must be installed separately for your CUDA version:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

2. Download model weights (once, before running any workflows):

```bash
python -c "
from diffusers import StableDiffusionPipeline
StableDiffusionPipeline.from_pretrained('runwayml/stable-diffusion-v1-5', use_safetensors=True)
print('Model cached.')
"
```

Or place a local model directory at any path (must contain `model_index.json`).

---

## Example 1 — Minimal: Static Prompt

```python
from generative_ai_workflow import Workflow, WorkflowConfig
from generative_ai_workflow.node import StableDiffusionNode

# Create a node with a static prompt
node = StableDiffusionNode(
    name="generate_logo",
    prompt="a minimalist logo of a mountain at sunset, flat design",
    model_id="runwayml/stable-diffusion-v1-5",
)

workflow = Workflow(
    nodes=[node],
    config=WorkflowConfig(),
)

result = workflow.execute(input_data={})

if result.success:
    path = result.node_outputs["generate_logo"]["image_file_path"]
    print(f"Image saved to: {path}")
```

---

## Example 2 — Template Prompt with Context Data

The `prompt` parameter supports `{variable}` substitution from workflow context, identical to `LLMNode`.

```python
from generative_ai_workflow import Workflow, WorkflowConfig
from generative_ai_workflow.node import LLMNode, StableDiffusionNode

# Step 1: LLM generates a scene description
describe = LLMNode(
    name="describe_scene",
    prompt="In 10 words or fewer, describe a scenic landscape for: {theme}",
)

# Step 2: Use LLM output as the image prompt
generate = StableDiffusionNode(
    name="render_scene",
    prompt="{describe_scene_output}, photorealistic, 4k",  # references LLM output
    model_id="runwayml/stable-diffusion-v1-5",
    width=512,
    height=512,
    num_inference_steps=25,
    guidance_scale=8.0,
)

workflow = Workflow(
    nodes=[describe, generate],
    config=WorkflowConfig(provider="openai"),
)

result = workflow.execute(input_data={"theme": "autumn forest"})
```

---

## Example 3 — Local Model Path

```python
node = StableDiffusionNode(
    name="local_gen",
    prompt="a cozy cabin in the woods, oil painting style",
    model_id="/models/stable-diffusion-v1-5",  # local directory
    output_dir="./my_outputs",
)
```

---

## Example 4 — Non-Critical Node (Workflow Continues on Failure)

```python
node = StableDiffusionNode(
    name="optional_image",
    prompt="product photo of {product_name}",
    model_id="runwayml/stable-diffusion-v1-5",
    is_critical=False,   # workflow continues even if generation fails
)
```

---

## Example 5 — Custom Output Directory

```python
node = StableDiffusionNode(
    name="banner",
    prompt="wide banner image, {style} style, high quality",
    model_id="runwayml/stable-diffusion-v1-5",
    width=768,
    height=256,
    output_dir="./banners",
)
```

---

## Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Node identifier (used in logs and metrics) |
| `prompt` | `str` | required | Prompt template; supports `{variable}` substitution |
| `model_id` | `str` | required | HuggingFace model ID or local directory path |
| `width` | `int` | `512` | Image width in pixels (multiple of 8) |
| `height` | `int` | `512` | Image height in pixels (multiple of 8) |
| `num_inference_steps` | `int` | `20` | Denoising steps (more = better quality, slower) |
| `guidance_scale` | `float` | `7.5` | Prompt adherence strength (7–8 typical) |
| `output_dir` | `str` | `"./generated_images"` | Directory for saved PNG files |
| `is_critical` | `bool` | `True` | If `False`, failures are logged and workflow continues |

---

## NodeResult Output Keys

On success, the node's output dict contains:

| Key | Type | Description |
|-----|------|-------------|
| `image_file_path` | `str` | Absolute path to the saved UUID-named PNG |
| `image_bytes` | `bytes` | Raw PNG bytes (for in-memory downstream use) |
| `generated_image` | `GeneratedImage` | Full structured output with all metadata |

Access in downstream nodes via `context.previous_outputs["render_scene"]["image_file_path"]`.

---

## Notes

- **Model weights are never auto-downloaded** during workflow execution. Pre-download before running.
- **One image per execution** — batch generation is not supported.
- **Device is auto-detected**: CUDA GPU → Apple MPS → CPU fallback.
- **Generated image filenames are UUID-based** — no two runs overwrite each other.
- **Concurrent workflows** using the same `model_id` share one model instance in memory. Inference calls are serialized (one at a time per model).
