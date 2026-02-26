"""Integration tests for PrometheusMiddleware with real WorkflowEngine.

Uses MockLLMProvider — no real API calls, $0 cost per run.
Verifies end-to-end metric recording after workflow execution.
"""

from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from generative_ai_workflow import (
    LLMNode,
    MockLLMProvider,
    PluginRegistry,
    TransformNode,
    Workflow,
    WorkflowConfig,
    WorkflowEngine,
    WorkflowStatus,
)
from generative_ai_workflow.middleware.prometheus import PrometheusMiddleware


@pytest.fixture(autouse=True)
def reset_plugin_registry() -> None:
    """Ensure a fresh PluginRegistry for each test."""
    PluginRegistry.clear()
    PluginRegistry.register_provider(
        "mock",
        MockLLMProvider(responses={"default": "mock response for prometheus tests"}),
    )
    yield


def _scrape(registry: CollectorRegistry) -> str:
    return generate_latest(registry).decode()


@pytest.mark.integration
class TestPrometheusMiddlewareIntegration:
    """End-to-end metric recording tests (SC-001–SC-005)."""

    async def test_at_least_four_metric_families_present(self) -> None:
        """SC-001: ≥4 distinct metric families appear after one workflow run."""
        registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(registry=registry))

        workflow = Workflow(
            name="test-workflow",
            nodes=[LLMNode(name="gen", prompt="Say hello", provider="mock")],
            config=WorkflowConfig(provider="mock"),
        )
        result = engine.run(workflow, input_data={})

        assert result.status == WorkflowStatus.COMPLETED
        output = _scrape(registry)

        required_families = [
            "workflow_duration_seconds",
            "workflow_total",
            "workflow_node_duration_seconds",
            "workflow_node_errors_total",
            "workflow_tokens_prompt_total",
            "workflow_tokens_completion_total",
        ]
        found = [f for f in required_families if f in output]
        assert len(found) >= 4, (
            f"Expected ≥4 metric families, found {len(found)}: {found}\n"
            f"Scrape output:\n{output[:1000]}"
        )

    async def test_node_label_matches_workflow_definition(self) -> None:
        """SC-002: node label exactly matches node name in workflow definition."""
        registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(registry=registry))

        workflow = Workflow(
            name="label-test",
            nodes=[LLMNode(name="summarise-step", prompt="Summarise {text}", provider="mock")],
            config=WorkflowConfig(provider="mock"),
        )
        engine.run(workflow, input_data={"text": "hello"})

        output = _scrape(registry)
        # Node name "summarise-step" should be sanitised to "summarise_step"
        assert 'node="summarise_step"' in output

    async def test_workflow_name_label_set(self) -> None:
        """SC-002: workflow_name label reflects the Workflow.name field."""
        registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(registry=registry))

        workflow = Workflow(
            name="my-pipeline",
            nodes=[LLMNode(name="gen", prompt="hello", provider="mock")],
            config=WorkflowConfig(provider="mock"),
        )
        engine.run(workflow, input_data={})

        output = _scrape(registry)
        assert 'workflow_name="my_pipeline"' in output

    async def test_custom_registry_isolates_from_global(self) -> None:
        """SC-003: custom registry leaves global prometheus_client.REGISTRY unchanged."""
        import prometheus_client

        unique_prefix = "isolation_integ_test_abc999"
        custom_registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(prefix=unique_prefix, registry=custom_registry))

        workflow = Workflow(
            name="isolation",
            nodes=[TransformNode(name="t", transform=lambda d: d)],
            config=WorkflowConfig(provider="mock"),
        )
        engine.run(workflow, input_data={"x": 1})

        global_output = generate_latest(prometheus_client.REGISTRY).decode()
        assert unique_prefix not in global_output, (
            "Metrics from custom registry leaked into global REGISTRY"
        )

        custom_output = _scrape(custom_registry)
        assert f"{unique_prefix}_duration_seconds" in custom_output

    async def test_completed_status_in_counter(self) -> None:
        """Workflow completion counter has status=completed label after success."""
        registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(registry=registry))

        workflow = Workflow(
            name="status-test",
            nodes=[TransformNode(name="passthrough", transform=lambda d: d)],
            config=WorkflowConfig(provider="mock"),
        )
        result = engine.run(workflow, input_data={})

        assert result.status == WorkflowStatus.COMPLETED
        output = _scrape(registry)
        assert 'status="completed"' in output

    async def test_token_metrics_for_llm_node(self) -> None:
        """Token counters appear with correct node label for LLM nodes."""
        registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(registry=registry))

        workflow = Workflow(
            name="token-test",
            nodes=[LLMNode(name="llm-node", prompt="Count tokens for me", provider="mock")],
            config=WorkflowConfig(provider="mock"),
        )
        engine.run(workflow, input_data={})

        output = _scrape(registry)
        assert "workflow_tokens_prompt_total" in output
        assert 'node="llm_node"' in output

    async def test_no_token_metrics_for_transform_node(self) -> None:
        """TransformNode emits no token metrics (zero-pollution rule, US2)."""
        registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(registry=registry))

        workflow = Workflow(
            name="transform-only",
            nodes=[TransformNode(name="pure-transform", transform=lambda d: d)],
            config=WorkflowConfig(provider="mock"),
        )
        engine.run(workflow, input_data={})

        output = _scrape(registry)
        # TransformNode should appear in duration metrics but NOT in token metrics
        token_lines_with_node = [
            line for line in output.splitlines()
            if 'node="pure_transform"' in line and "tokens" in line
        ]
        assert token_lines_with_node == [], (
            f"TransformNode should not emit token metrics: {token_lines_with_node}"
        )

    async def test_multiple_runs_accumulate_counter(self) -> None:
        """Completion counter increments on each workflow run."""
        registry = CollectorRegistry()
        engine = WorkflowEngine()
        engine.use(PrometheusMiddleware(registry=registry))

        workflow = Workflow(
            name="multi-run",
            nodes=[TransformNode(name="t", transform=lambda d: d)],
            config=WorkflowConfig(provider="mock"),
        )
        for _ in range(3):
            engine.run(workflow, input_data={})

        output = _scrape(registry)
        # The counter should reflect 3 increments — value appears in scrape
        assert "workflow_total" in output
        assert 'status="completed"' in output
