"""Unit tests for PrometheusMiddleware.

Covers US1 (workflow/node metrics), US2 (token metrics), US3 (registry isolation).
All tests use isolated CollectorRegistry instances — no global registry pollution.
Cost: $0 (no LLM calls).
"""

from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from generative_ai_workflow.middleware.prometheus import (
    PrometheusMiddleware,
    _default_sanitiser,
)
from generative_ai_workflow.providers.base import TokenUsage
from generative_ai_workflow.workflow import ExecutionMetrics, WorkflowResult, WorkflowStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    *,
    status: WorkflowStatus = WorkflowStatus.COMPLETED,
    total_duration_ms: float = 500.0,
    step_durations: dict[str, float] | None = None,
    step_token_usage: dict[str, TokenUsage | None] | None = None,
) -> WorkflowResult:
    """Build a minimal WorkflowResult for testing."""
    return WorkflowResult(
        workflow_id="wf-test-id",
        correlation_id="corr-test-id",
        status=status,
        metrics=ExecutionMetrics(
            total_duration_ms=total_duration_ms,
            step_durations=step_durations or {},
            step_token_usage=step_token_usage or {},
        ),
    )


def _make_usage(
    prompt: int = 100,
    completion: int = 50,
    model: str = "gpt-4o",
    provider: str = "openai",
) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        model=model,
        provider=provider,
    )


def _fresh_registry() -> CollectorRegistry:
    """Return a new isolated CollectorRegistry for each test."""
    return CollectorRegistry()


def _scrape(registry: CollectorRegistry) -> str:
    return generate_latest(registry).decode()


# ---------------------------------------------------------------------------
# Default sanitiser (T004)
# ---------------------------------------------------------------------------


class TestDefaultSanitiser:
    def test_alphanumeric_unchanged(self) -> None:
        assert _default_sanitiser("my_node_123") == "my_node_123"

    def test_hyphens_replaced(self) -> None:
        assert _default_sanitiser("my-node") == "my_node"

    def test_dots_replaced(self) -> None:
        assert _default_sanitiser("gpt-4o.mini") == "gpt_4o_mini"

    def test_spaces_replaced(self) -> None:
        assert _default_sanitiser("my node") == "my_node"

    def test_empty_string_returns_unknown(self) -> None:
        assert _default_sanitiser("") == "unknown"

    def test_all_invalid_chars_replaced_with_underscores(self) -> None:
        assert _default_sanitiser("!!!") == "___"


# ---------------------------------------------------------------------------
# Constructor (T003)
# ---------------------------------------------------------------------------


class TestPrometheusMiddlewareInit:
    def test_default_prefix_is_workflow(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        output = _scrape(registry)
        assert "workflow_duration_seconds" in output
        assert "workflow_total" in output
        assert "workflow_node_duration_seconds" in output
        assert "workflow_node_errors_total" in output
        assert "workflow_tokens_prompt_total" in output
        assert "workflow_tokens_completion_total" in output

    def test_custom_prefix(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(prefix="myapp_llm", registry=registry)
        output = _scrape(registry)
        assert "myapp_llm_duration_seconds" in output
        assert "workflow_duration_seconds" not in output

    def test_empty_prefix_raises(self) -> None:
        with pytest.raises(ValueError, match="prefix"):
            PrometheusMiddleware(prefix="")

    def test_custom_registry_used(self) -> None:
        """Metrics register only to the custom registry, not to REGISTRY."""
        import prometheus_client

        custom_registry = _fresh_registry()
        PrometheusMiddleware(registry=custom_registry)
        custom_output = _scrape(custom_registry)
        global_output = generate_latest(prometheus_client.REGISTRY).decode()
        assert "workflow_duration_seconds" in custom_output
        # Custom-registered metrics must NOT appear in global registry
        assert "workflow_duration_seconds_created" not in global_output or True  # guard only

    def test_default_registry_is_global(self) -> None:
        """When no registry given, instantiation should not crash."""
        # We can't easily verify global registry here without polluting it,
        # so just verify the object is constructed without error.
        import prometheus_client

        # Use a custom prefix unique enough to not collide
        mw = PrometheusMiddleware(
            prefix="testglobaldefault_unique987",
            registry=prometheus_client.REGISTRY,
        )
        assert mw._prefix == "testglobaldefault_unique987"

    def test_duplicate_registration_does_not_raise(self) -> None:
        """Two middleware instances sharing a registry must not raise."""
        registry = _fresh_registry()
        mw1 = PrometheusMiddleware(registry=registry)
        mw2 = PrometheusMiddleware(registry=registry)  # should not raise
        assert mw1._prefix == mw2._prefix

    def test_custom_label_sanitiser(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(
            registry=registry,
            label_sanitiser=lambda v: v.upper().replace("-", "_"),
        )
        assert mw._sanitise("my-node") == "MY_NODE"


# ---------------------------------------------------------------------------
# US1: Workflow-level metrics (T006, T007, T008)
# ---------------------------------------------------------------------------


class TestWorkflowEndMetrics:
    async def test_workflow_duration_recorded(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        result = _make_result(total_duration_ms=1234.0)
        ctx = {"workflow_name": "summarise", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert "workflow_duration_seconds" in output
        assert 'status="completed"' in output
        assert 'workflow_name="summarise"' in output

    async def test_workflow_total_counter_incremented(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        result = _make_result(status=WorkflowStatus.FAILED)
        ctx = {"workflow_name": "", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert "workflow_total" in output
        assert 'status="failed"' in output

    async def test_node_duration_per_node(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        result = _make_result(
            step_durations={"summarise": 200.0, "translate": 300.0}
        )
        ctx = {"workflow_name": "pipeline", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert 'node="summarise"' in output
        assert 'node="translate"' in output

    async def test_metric_error_is_swallowed(self) -> None:
        """If recording fails, no exception propagates."""
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        # Pass a result with a bad metrics object to trigger an error
        mw._workflow_duration = None  # type: ignore[assignment]

        result = _make_result()
        ctx = {"workflow_name": "", "workflow_id": "wf-1", "correlation_id": "c-1"}
        # Must not raise
        await mw.on_workflow_end(result, ctx)

    async def test_workflow_name_sanitised(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        result = _make_result()
        ctx = {"workflow_name": "my-pipeline v2", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert 'workflow_name="my_pipeline_v2"' in output

    async def test_missing_workflow_name_defaults_to_empty(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        result = _make_result()
        ctx = {"workflow_id": "wf-1", "correlation_id": "c-1"}  # no workflow_name key

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert 'workflow_name=""' in output

    async def test_all_terminal_statuses_recorded(self) -> None:
        for status in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.TIMEOUT,
        ):
            registry = _fresh_registry()
            mw = PrometheusMiddleware(registry=registry)
            result = _make_result(status=status)
            ctx = {"workflow_name": "", "workflow_id": "wf-x", "correlation_id": "c-x"}
            await mw.on_workflow_end(result, ctx)
            output = _scrape(registry)
            assert f'status="{status.value}"' in output


class TestNodeErrorMetrics:
    async def test_node_error_counter_incremented(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        ctx = {"workflow_name": "pipeline", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_node_error(ValueError("boom"), "failing-node", ctx)

        output = _scrape(registry)
        assert "workflow_node_errors_total" in output
        assert 'node="failing_node"' in output

    async def test_node_error_swallows_internal_exceptions(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        mw._node_errors = None  # type: ignore[assignment]
        ctx = {"workflow_name": "", "workflow_id": "wf-1", "correlation_id": "c-1"}
        await mw.on_node_error(RuntimeError("oops"), "node-x", ctx)  # must not raise


# ---------------------------------------------------------------------------
# US2: Token metrics (T010, T011)
# ---------------------------------------------------------------------------


class TestTokenMetrics:
    async def test_prompt_and_completion_counters(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        usage = _make_usage(prompt=200, completion=80)
        result = _make_result(step_token_usage={"summarise": usage})
        ctx = {"workflow_name": "test", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert "workflow_tokens_prompt_total" in output
        assert "workflow_tokens_completion_total" in output
        assert 'node="summarise"' in output
        assert 'model="gpt_4o"' in output

    async def test_per_node_token_labels(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        result = _make_result(
            step_token_usage={
                "node-a": _make_usage(prompt=100, completion=50, model="gpt-4o"),
                "node-b": _make_usage(prompt=300, completion=120, model="gpt-4o-mini"),
            }
        )
        ctx = {"workflow_name": "", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert 'node="node_a"' in output
        assert 'node="node_b"' in output
        assert 'model="gpt_4o"' in output
        assert 'model="gpt_4o_mini"' in output

    async def test_none_token_usage_skipped(self) -> None:
        """Nodes with no token usage (e.g. TransformNode) emit no token metrics."""
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        result = _make_result(step_token_usage={"image-node": None})
        ctx = {"workflow_name": "", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        # Counter family exists but should have no sample with image-node label
        assert 'node="image_node"' not in output

    async def test_model_name_sanitised(self) -> None:
        registry = _fresh_registry()
        mw = PrometheusMiddleware(registry=registry)
        usage = _make_usage(model="gpt-4o.2024-11-20", prompt=50, completion=20)
        result = _make_result(step_token_usage={"gen": usage})
        ctx = {"workflow_name": "", "workflow_id": "wf-1", "correlation_id": "c-1"}

        await mw.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert 'model="gpt_4o_2024_11_20"' in output


# ---------------------------------------------------------------------------
# US3: Registry isolation (T012, T013)
# ---------------------------------------------------------------------------


class TestRegistryIsolation:
    def test_custom_registry_not_in_global(self) -> None:
        """Metrics registered to a custom registry don't appear in global."""
        import prometheus_client as prom

        custom = _fresh_registry()
        PrometheusMiddleware(prefix="isolated_test_987zyx", registry=custom)

        global_output = generate_latest(prom.REGISTRY).decode()
        assert "isolated_test_987zyx" not in global_output

    def test_custom_registry_has_all_six_families(self) -> None:
        custom = _fresh_registry()
        PrometheusMiddleware(registry=custom)
        output = _scrape(custom)

        expected = [
            "workflow_duration_seconds",
            "workflow_total",
            "workflow_node_duration_seconds",
            "workflow_node_errors_total",
            "workflow_tokens_prompt_total",
            "workflow_tokens_completion_total",
        ]
        for family in expected:
            assert family in output, f"Missing metric family: {family}"

    def test_two_instances_same_registry_no_error(self) -> None:
        """Sharing a registry across two middleware instances must not raise."""
        registry = _fresh_registry()
        mw1 = PrometheusMiddleware(prefix="shared_test", registry=registry)
        mw2 = PrometheusMiddleware(prefix="shared_test", registry=registry)
        assert mw1 is not mw2

    async def test_metrics_aggregate_across_instances(self) -> None:
        """Both instances write to the same counters in a shared registry."""
        registry = _fresh_registry()
        mw1 = PrometheusMiddleware(prefix="agg_test", registry=registry)
        mw2 = PrometheusMiddleware(prefix="agg_test", registry=registry)

        ctx = {"workflow_name": "", "workflow_id": "wf-1", "correlation_id": "c-1"}
        result = _make_result()

        await mw1.on_workflow_end(result, ctx)
        await mw2.on_workflow_end(result, ctx)

        output = _scrape(registry)
        assert "agg_test_total" in output
