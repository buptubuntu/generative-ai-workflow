"""Integration tests for full workflow execution.

These tests verify the complete pipeline using MockLLMProvider to avoid
real API calls. Marked as integration to allow tiered CI execution.
"""

from __future__ import annotations

import pytest

from generative_ai_workflow import (
    LLMStep,
    MockLLMProvider,
    PluginRegistry,
    TransformStep,
    Workflow,
    WorkflowConfig,
    WorkflowEngine,
    WorkflowStatus,
)


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    PluginRegistry.clear()
    mock = MockLLMProvider(
        responses={
            "default": "Integration test response with some content.",
        }
    )
    PluginRegistry.register_provider("mock", mock)
    yield


@pytest.mark.integration
class TestFullWorkflowExecution:
    """End-to-end workflow tests (SC-001: ≤15 lines of code)."""

    async def test_two_step_workflow_completes(self, cost_tracker) -> None:
        """2-step workflow: transform + LLM call."""
        workflow = Workflow(
            steps=[
                TransformStep(name="prep", transform=lambda d: {"clean": d["text"].strip()}),
                LLMStep(name="gen", prompt="Process: {clean}", provider="mock"),
            ],
            config=WorkflowConfig(provider="mock"),
        )

        result = await workflow.execute_async({"text": "  hello world  "})

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output is not None
        assert "gen_output" in result.output
        cost_tracker.record(result.metrics.token_usage_total)
        cost_tracker.assert_within_budget()

    async def test_three_step_llm_workflow_under_15_lines(self, cost_tracker) -> None:
        """Verify SC-001: 3-step workflow fits in ≤15 lines (shown here explicitly)."""
        workflow = Workflow(
            steps=[
                TransformStep(name="p", transform=lambda d: {"q": d["input"]}),
                LLMStep(name="s", prompt="Summarize: {q}", provider="mock"),
                LLMStep(name="a", prompt="Analyze: {s_output}", provider="mock"),
            ],
            config=WorkflowConfig(provider="mock"),
        )
        result = await workflow.execute_async({"input": "test content"})
        assert result.status == WorkflowStatus.COMPLETED
        assert result.metrics.steps_completed == 3

    def test_sync_execution_with_timeout(self, cost_tracker) -> None:
        """Sync execution with timeout returns completed within timeout."""
        workflow = Workflow(
            steps=[LLMStep(name="gen", prompt="Hello {text}", provider="mock")],
            config=WorkflowConfig(provider="mock"),
        )
        result = workflow.execute({"text": "world"}, timeout=30.0)
        assert result.status == WorkflowStatus.COMPLETED

    async def test_token_usage_tracked_across_steps(self, cost_tracker) -> None:
        """SC-003: 100% of LLM operations tracked."""
        workflow = Workflow(
            steps=[
                LLMStep(name="step1", prompt="First: {text}", provider="mock"),
                LLMStep(name="step2", prompt="Second: {text}", provider="mock"),
            ],
            config=WorkflowConfig(provider="mock"),
        )
        result = await workflow.execute_async({"text": "test"})

        assert result.metrics.token_usage_total is not None
        assert result.metrics.token_usage_total.total_tokens > 0
        assert "step1" in result.metrics.step_token_usage
        assert "step2" in result.metrics.step_token_usage

    async def test_custom_provider_plugin(self) -> None:
        """SC-004: Custom provider registered without modifying framework."""
        from generative_ai_workflow import LLMProvider, LLMRequest, LLMResponse, TokenUsage

        class CustomProvider(LLMProvider):
            async def complete_async(self, request: LLMRequest) -> LLMResponse:
                return LLMResponse(
                    content=f"Custom: {request.prompt}",
                    model="custom-model",
                    usage=TokenUsage(
                        prompt_tokens=5, completion_tokens=3,
                        total_tokens=8, model="custom-model", provider="custom",
                    ),
                    latency_ms=0.1,
                    finish_reason="stop",
                )

        PluginRegistry.register_provider("custom", CustomProvider())
        workflow = Workflow(
            steps=[LLMStep(name="gen", prompt="Hello {text}", provider="custom")],
            config=WorkflowConfig(provider="custom"),
        )
        result = await workflow.execute_async({"text": "world"})
        assert result.status == WorkflowStatus.COMPLETED
        assert "Custom:" in result.output["llm_response"]
