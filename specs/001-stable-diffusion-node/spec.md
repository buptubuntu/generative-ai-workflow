# Feature Specification: Stable Diffusion Node

**Feature Branch**: `001-stable-diffusion-node`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "add node that can run stable diffusion model locally"

## Clarifications

### Session 2026-02-23

- Q: What format does the model identifier use? → A: Both accepted — auto-detect whether value is a local filesystem path or a HuggingFace model ID string.
- Q: How should concurrent model access be handled when multiple nodes use the same model? → A: Shared singleton — the model is loaded once and shared across all nodes that reference the same model identifier.
- Q: What file naming convention should generated images use to avoid overwrite collisions? → A: UUID-based — each generated image receives a unique random filename (e.g., `<uuid>.png`).
- Q: Should StableDiffusionNode emit structured logs and metrics? → A: Full parity with LLMNode — emit structured logs and metrics (start, success/failure, duration) consistent with existing framework observability.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Image from Text Prompt (Priority: P1)

A workflow author wants to add image generation to their workflow. They configure a `StableDiffusionNode` with a prompt template and insert it into their workflow alongside text-processing nodes. When the workflow runs, the node generates an image locally and passes the result to the next node.

**Why this priority**: Core functionality — without this, the node has no value. Enables multi-modal workflows that combine text and image generation entirely on local hardware.

**Independent Test**: Can be fully tested by creating a `StableDiffusionNode`, running it with a text prompt, and verifying a valid image is produced and accessible in the workflow output.

**Acceptance Scenarios**:

1. **Given** a workflow containing a `StableDiffusionNode` with a static prompt, **When** the workflow executes, **Then** the node produces a valid image and returns a `NodeResult` with `status=COMPLETED` and the image accessible via the output dict.
2. **Given** a `StableDiffusionNode` with a prompt template containing `{variable}` placeholders, **When** the workflow executes with matching context data, **Then** the placeholders are substituted and the rendered prompt is used for image generation.
3. **Given** a prompt template referencing a variable not present in the context, **When** the workflow executes, **Then** the node returns a `NodeResult` with `status=FAILED` and a descriptive error message.

---

### User Story 2 - Configure Generation Parameters (Priority: P2)

A workflow author wants control over image generation quality and dimensions. They can specify output image size, number of inference steps, and guidance scale when constructing the node, allowing them to balance quality against generation speed.

**Why this priority**: Generation parameters directly affect output quality and runtime. Sensible defaults enable quick use, while configuration supports production and experimentation use cases.

**Independent Test**: Can be fully tested by constructing nodes with different parameter combinations and verifying the output images reflect the specified dimensions and that execution time varies with step count.

**Acceptance Scenarios**:

1. **Given** a `StableDiffusionNode` constructed with default parameters, **When** it executes, **Then** it produces an image at the default resolution (512×512) using default inference settings.
2. **Given** a `StableDiffusionNode` constructed with custom width, height, and inference steps, **When** it executes, **Then** the output image matches the specified dimensions.
3. **Given** generation parameters outside valid ranges (e.g., zero steps, negative dimensions), **When** the node is constructed, **Then** a `ValueError` is raised with a descriptive message before any generation occurs.

---

### User Story 3 - Use Node as Non-Critical Step (Priority: P3)

A workflow author marks a `StableDiffusionNode` as non-critical (`is_critical=False`). When image generation fails (e.g., insufficient memory, missing model weights), the workflow continues executing subsequent nodes rather than aborting.

**Why this priority**: Consistent with the existing `WorkflowNode` contract. Enables resilient pipelines where image generation is optional or best-effort.

**Independent Test**: Can be tested by deliberately triggering a generation failure on a non-critical node and verifying the workflow engine continues to execute the remaining nodes.

**Acceptance Scenarios**:

1. **Given** a `StableDiffusionNode` with `is_critical=False` that encounters a generation error, **When** the workflow runs, **Then** the node returns `status=FAILED`, the error is logged, and the workflow continues with remaining nodes.

---

### Edge Cases

- What happens when the local machine has no GPU and the model requires one? The node must gracefully report a clear error rather than hanging or silently producing garbage output.
- What happens when the model weights are missing or the specified model cannot be loaded? The node must fail fast with a descriptive error message before attempting generation.
- What happens when available memory (RAM or GPU VRAM) is insufficient for the configured image size? The node must return a failed `NodeResult` with a memory-related error message.
- What happens when the prompt string is empty after template substitution? The node must return a failed `NodeResult` rather than proceeding with an empty prompt.
- What happens when two workflow nodes attempt to load the same model simultaneously? The framework maintains a shared singleton per model identifier — the model is loaded once and reused across all nodes referencing the same identifier. Concurrent inference requests against the shared instance must be serialized to prevent state corruption.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The framework MUST provide a `StableDiffusionNode` class that extends `WorkflowNode` and integrates with the existing workflow engine without modifications to the engine.
- **FR-002**: `StableDiffusionNode` MUST accept a prompt template supporting `{variable}` placeholder substitution, consistent with `LLMNode` behavior.
- **FR-003**: `StableDiffusionNode` MUST accept configurable image width and height, with valid defaults (512×512 pixels).
- **FR-004**: `StableDiffusionNode` MUST accept a configurable number of inference steps and guidance scale, with sensible defaults.
- **FR-005**: `StableDiffusionNode` MUST accept a model identifier that specifies which Stable Diffusion model variant to use. The identifier MUST support both a local filesystem path to model weights and a HuggingFace model ID string (e.g., `"runwayml/stable-diffusion-v1-5"`); the node auto-detects which format is provided.
- **FR-006**: The node MUST run image generation entirely on the local machine without making external network calls during inference.
- **FR-007**: The node MUST return a `NodeResult` with `status=COMPLETED` containing the generated image as both a file path (saved to a configurable output directory) and raw image bytes in the output dict.
- **FR-008**: The node MUST return a `NodeResult` with `status=FAILED` and a descriptive error message when generation fails for any reason, without raising unhandled exceptions.
- **FR-009**: The node MUST substitute prompt template variables from the accumulated workflow context (input data + previous node outputs), consistent with `LLMNode`.
- **FR-010**: The node MUST respect the `is_critical` flag: when `False`, failures are logged and workflow execution continues.
- **FR-011**: The node MUST validate construction parameters (prompt non-empty, dimensions positive integers, steps positive integer) and raise `ValueError` on invalid inputs.
- **FR-012**: The framework MUST allow `StableDiffusionNode` to be registered as a plugin via `PluginRegistry` or used directly without registration.
- **FR-013**: The framework MUST maintain a shared model singleton per model identifier — when multiple nodes reference the same identifier, the model is loaded exactly once and shared across those nodes. Concurrent inference calls against the shared instance MUST be serialized to prevent state corruption.
- **FR-014**: `StableDiffusionNode` MUST emit structured logs and metrics consistent with `LLMNode`, including: execution start, completion/failure status, and generation duration. This integrates with the existing framework observability infrastructure without requiring changes to it.

### Key Entities

- **StableDiffusionNode**: A `WorkflowNode` subclass responsible for local image generation. Attributes: name, prompt template, model identifier, image width, image height, inference steps, guidance scale, output directory, is_critical.
- **GeneratedImage**: Represents the output of one image generation run. Attributes: file path (where the image was saved), raw bytes, width, height, generation duration in milliseconds.
- **ModelConfig**: Configuration for the Stable Diffusion model to load. Attributes: model identifier (local path or HuggingFace model ID — auto-detected), device preference (auto-detect), precision setting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `StableDiffusionNode` can be added to an existing workflow and executed end-to-end without changes to the workflow engine or runner.
- **SC-002**: Image generation completes and produces a valid image file on a machine with a compatible GPU within 60 seconds for a 512×512 image at 20 inference steps.
- **SC-003**: 100% of `NodeResult` objects returned by the node carry a non-None `status` of either `COMPLETED` or `FAILED` — the node never raises an unhandled exception to the workflow engine.
- **SC-004**: Prompt template substitution works correctly for at least all variable patterns already supported by `LLMNode`, verified by unit tests covering both static and dynamic prompts.
- **SC-005**: All construction-time validation errors are caught before any model loading or generation begins, verified by tests that confirm no file system side-effects occur on invalid inputs.
- **SC-006**: The feature ships with unit tests covering: successful generation, failed generation (non-critical), missing template variable, invalid construction parameters, and empty-prompt edge case.
- **SC-007**: Every execution of `StableDiffusionNode` — successful or failed — produces at least one structured log entry and records a duration metric, verifiable by inspecting the observability output in tests.

## Assumptions

- The local machine has a compatible hardware setup (GPU with sufficient VRAM, or CPU as fallback with degraded performance).
- Model weights must be downloaded separately by the user before using the node; the node does not auto-download models.
- The output directory for saving generated images defaults to a `./generated_images` folder relative to the working directory; it is created automatically if it does not exist.
- Each generated image is saved with a UUID-based filename (e.g., `<uuid>.png`) to guarantee uniqueness across runs; no overwriting occurs.
- Image output format defaults to PNG.
- Only text-to-image generation is in scope for this feature; image-to-image and inpainting are out of scope.
- The node supports one image per execution; batch generation is out of scope.
- Thread safety within a single workflow execution is in scope; cross-workflow model sharing/caching is out of scope for this feature.
