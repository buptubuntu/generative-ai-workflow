"""Unit tests for StableDiffusionNode, GeneratedImage, and ModelRegistry.

Covers all cases required by SC-006:
  - Successful generation (mocked pipeline)
  - Non-critical failure mode
  - Missing template variable
  - Invalid construction parameters
  - Empty prompt after substitution

Also covers:
  - Structured log emission (FR-014, SC-007)
  - Parameter propagation to holder.run() (FR-003, FR-004)
  - Workflow continuation past non-critical failure (FR-010, SC-001)

All tests mock the ModelRegistry / _PipelineHolder — no real model
weights or GPU required.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import structlog.testing

from generative_ai_workflow.node import GeneratedImage, StableDiffusionNode
from generative_ai_workflow.workflow import NodeContext, NodeStatus, WorkflowStatus


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _minimal_png() -> bytes:
    """Return valid 1×1 white PNG bytes without a real Pillow/diffusers install."""
    # Minimal valid PNG header + IHDR + IDAT + IEND (1×1 white RGB pixel)
    import base64
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    return base64.b64decode(png_b64)


def _make_context(**kwargs: object) -> NodeContext:
    """Create a minimal NodeContext for testing."""
    return NodeContext(
        workflow_id=str(uuid.uuid4()),
        step_id=str(uuid.uuid4()),
        correlation_id=str(uuid.uuid4()),
        **kwargs,  # type: ignore[arg-type]
    )


def _make_mock_holder(png_bytes: bytes | None = None) -> MagicMock:
    """Return a mock _PipelineHolder whose .run() returns PNG bytes."""
    holder = MagicMock()
    holder.device = "cpu"
    holder.run.return_value = png_bytes or _minimal_png()
    return holder


# ---------------------------------------------------------------------------
# T007: Successful generation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_generation(tmp_path: Path) -> None:
    """T007: Mocked pipeline returns valid PNG; result is COMPLETED."""
    png_bytes = _minimal_png()
    mock_holder = _make_mock_holder(png_bytes)

    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        return_value=mock_holder,
    ):
        node = StableDiffusionNode(
            name="test_gen",
            prompt="a red apple on a table",
            model_id="test-model",
            output_dir=str(tmp_path),
        )
        context = _make_context(input_data={})
        result = await node.execute_async(context)

    assert result.status == NodeStatus.COMPLETED
    assert result.output is not None

    file_path: str = result.output["image_file_path"]
    assert file_path.endswith(".png")
    assert Path(file_path).is_absolute()
    assert Path(file_path).exists()

    generated: GeneratedImage = result.output["generated_image"]
    assert isinstance(generated, GeneratedImage)
    assert generated.generation_duration_ms >= 0.0
    assert generated.device_type == "cpu"
    assert generated.model_id == "test-model"
    assert generated.inference_steps == 20
    assert generated.guidance_scale == 7.5

    assert result.output["image_bytes"] == png_bytes


# ---------------------------------------------------------------------------
# T008: Missing template variable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_template_variable() -> None:
    """T008: Prompt references {color} but context has no 'color' key."""
    node = StableDiffusionNode(
        name="test_missing",
        prompt="a {color} apple",
        model_id="test-model",
    )
    context = _make_context(input_data={})
    result = await node.execute_async(context)

    assert result.status == NodeStatus.FAILED
    assert result.error is not None
    assert "color" in result.error


# ---------------------------------------------------------------------------
# T009: Empty rendered prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_rendered_prompt() -> None:
    """T009: Template resolves to empty string → FAILED."""
    node = StableDiffusionNode(
        name="test_empty",
        prompt="{var}",
        model_id="test-model",
    )
    context = _make_context(input_data={"var": "   "})  # whitespace-only
    result = await node.execute_async(context)

    assert result.status == NodeStatus.FAILED
    assert result.error is not None


# ---------------------------------------------------------------------------
# T010: Structured log emission (FR-014, SC-007)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structured_log_emission(tmp_path: Path) -> None:
    """T010: execute_async emits at least a start and a completion log event."""
    mock_holder = _make_mock_holder()

    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        return_value=mock_holder,
    ):
        node = StableDiffusionNode(
            name="test_logs",
            prompt="a landscape painting",
            model_id="test-model",
            output_dir=str(tmp_path),
        )
        context = _make_context(input_data={})

        with structlog.testing.capture_logs() as captured:
            result = await node.execute_async(context)

    assert result.status == NodeStatus.COMPLETED
    events = [entry["event"] for entry in captured]
    assert any("start" in e for e in events), f"No start event found in: {events}"
    assert any(
        "completed" in e or "success" in e for e in events
    ), f"No completion event found in: {events}"


@pytest.mark.asyncio
async def test_failure_log_emission() -> None:
    """T010 (failure path): execute_async emits a failure log event on error."""
    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        side_effect=RuntimeError("simulated OOM"),
    ):
        node = StableDiffusionNode(
            name="test_fail_logs",
            prompt="a mountain",
            model_id="test-model",
        )
        context = _make_context(input_data={})

        with structlog.testing.capture_logs() as captured:
            result = await node.execute_async(context)

    assert result.status == NodeStatus.FAILED
    events = [entry["event"] for entry in captured]
    assert any(
        "fail" in e or "error" in e for e in events
    ), f"No failure event found in: {events}"


# ---------------------------------------------------------------------------
# T015: Invalid construction parameters (FR-011, SC-005)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override",
    [
        {"width": 0},
        {"width": -8},
        {"height": 0},
        {"height": -16},
        {"width": 7},       # not multiple of 8
        {"height": 511},    # not multiple of 8
        {"num_inference_steps": 0},
        {"guidance_scale": -0.1},
        {"model_id": ""},
    ],
)
def test_invalid_construction_raises_value_error(override: dict) -> None:
    """T015: Invalid params raise ValueError at construction, before any I/O."""
    base: dict = {
        "name": "test",
        "prompt": "a red apple",
        "model_id": "some-model",
        "width": 512,
        "height": 512,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
    }
    base.update(override)
    with pytest.raises(ValueError):
        StableDiffusionNode(**base)


def test_empty_prompt_raises_value_error() -> None:
    """T015: Empty prompt string raises ValueError at construction."""
    with pytest.raises(ValueError, match="(?i)prompt"):
        StableDiffusionNode(name="test", prompt="", model_id="some-model")


def test_valid_defaults_do_not_raise() -> None:
    """T015 (positive): Minimal valid construction succeeds without error."""
    node = StableDiffusionNode(
        name="valid",
        prompt="a landscape",
        model_id="some-model",
    )
    assert node.name == "valid"
    assert node._config.width == 512
    assert node._config.height == 512
    assert node._config.num_inference_steps == 20
    assert node._config.guidance_scale == 7.5


# ---------------------------------------------------------------------------
# T016: Parameter propagation to holder.run() (FR-003, FR-004)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parameter_propagation(tmp_path: Path) -> None:
    """T016: Custom params are forwarded unchanged to holder.run()."""
    mock_holder = _make_mock_holder()

    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        return_value=mock_holder,
    ):
        node = StableDiffusionNode(
            name="test_params",
            prompt="a landscape",
            model_id="test-model",
            width=768,
            height=256,
            num_inference_steps=30,
            guidance_scale=8.0,
            output_dir=str(tmp_path),
        )
        context = _make_context(input_data={})
        result = await node.execute_async(context)

    assert result.status == NodeStatus.COMPLETED
    mock_holder.run.assert_called_once()

    # run(prompt, width, height, num_inference_steps, guidance_scale)
    args = mock_holder.run.call_args.args
    assert args[1] == 768    # width
    assert args[2] == 256    # height
    assert args[3] == 30     # num_inference_steps
    assert args[4] == 8.0    # guidance_scale


# ---------------------------------------------------------------------------
# T019: Non-critical failure (FR-008, FR-010, SC-003)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_critical_failure_returns_failed_no_exception() -> None:
    """T019: RuntimeError during inference → FAILED result, no propagated exception."""
    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        side_effect=RuntimeError("CUDA out of memory"),
    ):
        node = StableDiffusionNode(
            name="test_noncrit",
            prompt="a mountain at sunrise",
            model_id="test-model",
            is_critical=False,
        )
        context = _make_context(input_data={})
        # Must not raise
        result = await node.execute_async(context)

    assert result.status == NodeStatus.FAILED
    assert result.error is not None
    assert "memory" in result.error.lower() or "cuda" in result.error.lower()
    assert result.output is None


@pytest.mark.asyncio
async def test_critical_failure_also_returns_failed_no_exception() -> None:
    """T019 (critical=True): Critical node also returns FAILED cleanly."""
    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        side_effect=RuntimeError("model not found"),
    ):
        node = StableDiffusionNode(
            name="test_crit",
            prompt="landscape",
            model_id="missing-model",
            is_critical=True,
        )
        context = _make_context(input_data={})
        result = await node.execute_async(context)

    assert result.status == NodeStatus.FAILED
    assert result.error is not None


# ---------------------------------------------------------------------------
# T020: Workflow continues past non-critical failure (SC-001, FR-010)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_continues_after_non_critical_failure() -> None:
    """T020: Non-critical SD failure → workflow COMPLETED, downstream ran."""
    from generative_ai_workflow.node import TransformNode
    from generative_ai_workflow.workflow import Workflow

    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        side_effect=RuntimeError("model not found"),
    ):
        sd_node = StableDiffusionNode(
            name="optional_image",
            prompt="landscape",
            model_id="missing-model",
            is_critical=False,
        )
        transform_node = TransformNode(
            name="downstream",
            transform=lambda data: {"downstream_result": "ran"},
        )
        workflow = Workflow(nodes=[sd_node, transform_node])
        result = workflow.execute(input_data={})

    # Workflow should complete despite the non-critical SD failure
    assert result.status == WorkflowStatus.COMPLETED
    assert result.output is not None
    assert result.output.get("downstream_result") == "ran"


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_template_substitution_from_previous_outputs(tmp_path: Path) -> None:
    """Prompt variable resolved from previous_outputs dict (FR-009)."""
    mock_holder = _make_mock_holder()

    with patch(
        "generative_ai_workflow.node.ModelRegistry.get",
        return_value=mock_holder,
    ):
        node = StableDiffusionNode(
            name="test_sub",
            prompt="a {style} landscape",
            model_id="test-model",
            output_dir=str(tmp_path),
        )
        # variable comes from previous_outputs, not input_data
        context = _make_context(
            input_data={},
            previous_outputs={"style": "watercolour"},
        )
        result = await node.execute_async(context)

    assert result.status == NodeStatus.COMPLETED
    called_prompt = mock_holder.run.call_args.args[0]
    assert called_prompt == "a watercolour landscape"


def test_output_dir_is_created(tmp_path: Path) -> None:
    """output_dir is created automatically if it does not exist (FR-007)."""
    new_dir = tmp_path / "deep" / "nested" / "output"
    assert not new_dir.exists()

    mock_holder = _make_mock_holder()

    async def _run() -> None:
        with patch(
            "generative_ai_workflow.node.ModelRegistry.get",
            return_value=mock_holder,
        ):
            node = StableDiffusionNode(
                name="test_mkdir",
                prompt="a scene",
                model_id="test-model",
                output_dir=str(new_dir),
            )
            context = _make_context(input_data={})
            result = await node.execute_async(context)
        assert result.status == NodeStatus.COMPLETED
        assert new_dir.exists()

    import asyncio
    asyncio.run(_run())
