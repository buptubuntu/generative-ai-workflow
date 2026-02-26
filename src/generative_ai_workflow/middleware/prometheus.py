"""Prometheus metrics middleware for generative-ai-workflow.

Exports workflow execution metrics to Prometheus via the existing Middleware
hook system. Install the optional dependency before importing this module::

    pip install 'generative-ai-workflow[observability]'

Example::

    from generative_ai_workflow import WorkflowEngine
    from generative_ai_workflow.middleware.prometheus import PrometheusMiddleware

    engine = WorkflowEngine()
    engine.use(PrometheusMiddleware())
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

try:
    from prometheus_client import (
        REGISTRY as _DEFAULT_REGISTRY,
    )
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Histogram,
    )
except ImportError as _exc:
    raise ImportError(
        "prometheus-client is required for PrometheusMiddleware. "
        "Install it with: pip install 'generative-ai-workflow[observability]'"
    ) from _exc

import structlog

from generative_ai_workflow.middleware.base import Middleware

# Default histogram buckets (seconds) — mirrors prometheus_client Histogram defaults.
_DEFAULT_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0,
)

if TYPE_CHECKING:
    from generative_ai_workflow.workflow import WorkflowResult

logger = structlog.get_logger(__name__)

_INVALID_LABEL_CHARS = re.compile(r"[^a-zA-Z0-9_]")


def _default_sanitiser(value: str) -> str:
    """Replace non-alphanumeric/underscore characters with underscores.

    Args:
        value: Raw label value (e.g. node name, model name, workflow name).

    Returns:
        Sanitised string safe for use as a Prometheus label value.
        Returns ``"unknown"`` if the sanitised result is empty.
    """
    sanitised = _INVALID_LABEL_CHARS.sub("_", value)
    return sanitised if sanitised else "unknown"


class PrometheusMiddleware(Middleware):
    """Prometheus metrics middleware for workflow observability.

    Records 6 metric families on every workflow execution:

    - ``{prefix}_duration_seconds`` (Histogram): total workflow wall-clock time
    - ``{prefix}_total`` (Counter): workflow completions by status
    - ``{prefix}_node_duration_seconds`` (Histogram): per-node wall-clock time
    - ``{prefix}_node_errors_total`` (Counter): per-node error count
    - ``{prefix}_tokens_prompt_total`` (Counter): prompt tokens per node/model
    - ``{prefix}_tokens_completion_total`` (Counter): completion tokens per node/model

    All metric errors are caught and logged as warnings — this middleware
    never interrupts workflow execution.

    Args:
        prefix: Namespace prepended to all metric names. Defaults to
            ``"workflow"``.
        registry: Prometheus ``CollectorRegistry`` to register metrics
            against. Defaults to the global ``prometheus_client.REGISTRY``.
            Pass a fresh ``CollectorRegistry()`` for isolated metrics.
        buckets: Histogram bucket boundaries in seconds. Defaults to
            ``prometheus_client.DEFAULT_BUCKETS``.
        label_sanitiser: Optional callable that transforms raw label values
            (node names, model names, workflow names) into valid Prometheus
            label strings. Replaces the built-in sanitiser entirely when
            provided.

    Example::

        from prometheus_client import CollectorRegistry
        from generative_ai_workflow.middleware.prometheus import PrometheusMiddleware

        # Isolated registry (safe for embedding in larger apps)
        registry = CollectorRegistry()
        engine.use(PrometheusMiddleware(registry=registry))

        # Custom prefix to avoid collisions
        engine.use(PrometheusMiddleware(prefix="myapp_llm"))

        # Hash-based sanitiser for sensitive node names
        import hashlib
        engine.use(PrometheusMiddleware(
            label_sanitiser=lambda v: "h_" + hashlib.md5(v.encode()).hexdigest()[:8]
        ))
    """

    def __init__(
        self,
        *,
        prefix: str = "workflow",
        registry: CollectorRegistry | None = None,
        buckets: Sequence[float] = _DEFAULT_BUCKETS,
        label_sanitiser: Callable[[str], str] | None = None,
    ) -> None:
        if not prefix:
            raise ValueError("prefix must not be empty")

        self._prefix = prefix
        self._registry = registry if registry is not None else _DEFAULT_REGISTRY
        self._sanitise: Callable[[str], str] = label_sanitiser or _default_sanitiser

        def _register(collector: object) -> object:
            """Register collector, ignoring duplicate-registration errors."""
            try:
                self._registry.register(collector)
            except ValueError:
                logger.warning(
                    "prometheus.duplicate_registration",
                    metric=str(collector),
                )
            return collector

        self._workflow_duration: Histogram = _register(
            Histogram(
                f"{prefix}_duration_seconds",
                "Total workflow wall-clock duration in seconds",
                labelnames=["workflow_name", "status"],
                buckets=list(buckets),
                registry=None,
            )
        )
        self._workflow_total: Counter = _register(
            Counter(
                f"{prefix}_total",
                "Workflow execution count by terminal status",
                labelnames=["workflow_name", "status"],
                registry=None,
            )
        )
        self._node_duration: Histogram = _register(
            Histogram(
                f"{prefix}_node_duration_seconds",
                "Per-node wall-clock duration in seconds",
                labelnames=["workflow_name", "node"],
                buckets=list(buckets),
                registry=None,
            )
        )
        self._node_errors: Counter = _register(
            Counter(
                f"{prefix}_node_errors_total",
                "Per-node error count",
                labelnames=["workflow_name", "node"],
                registry=None,
            )
        )
        self._tokens_prompt: Counter = _register(
            Counter(
                f"{prefix}_tokens_prompt_total",
                "Prompt tokens consumed per node and model",
                labelnames=["workflow_name", "node", "model"],
                registry=None,
            )
        )
        self._tokens_completion: Counter = _register(
            Counter(
                f"{prefix}_tokens_completion_total",
                "Completion tokens consumed per node and model",
                labelnames=["workflow_name", "node", "model"],
                registry=None,
            )
        )

    async def on_workflow_end(
        self,
        result: WorkflowResult,
        context: dict[str, Any],
    ) -> None:
        """Record workflow-level and node-level metrics on completion.

        Observes duration, increments completion counter, records per-node
        durations, and accumulates token usage counters. All errors are
        swallowed and logged as warnings.

        Args:
            result: Completed workflow result containing metrics.
            context: Engine context with ``workflow_name``, ``workflow_id``,
                ``correlation_id``.
        """
        try:
            raw_wf = context.get("workflow_name") or ""
            wf_name = self._sanitise(raw_wf) if raw_wf else ""
            status = result.status.value

            # Workflow-level metrics
            self._workflow_duration.labels(
                workflow_name=wf_name, status=status
            ).observe(result.metrics.total_duration_ms / 1000.0)

            self._workflow_total.labels(
                workflow_name=wf_name, status=status
            ).inc()

            # Per-node duration metrics
            for node_name, duration_ms in result.metrics.step_durations.items():
                node_label = self._sanitise(node_name)
                self._node_duration.labels(
                    workflow_name=wf_name, node=node_label
                ).observe(duration_ms / 1000.0)

            # Per-node token metrics (LLM nodes only)
            for node_name, usage in result.metrics.step_token_usage.items():
                if usage is None:
                    continue
                node_label = self._sanitise(node_name)
                model_label = self._sanitise(usage.model or "unknown")
                self._tokens_prompt.labels(
                    workflow_name=wf_name, node=node_label, model=model_label
                ).inc(usage.prompt_tokens)
                self._tokens_completion.labels(
                    workflow_name=wf_name, node=node_label, model=model_label
                ).inc(usage.completion_tokens)

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "prometheus.on_workflow_end.error",
                error=str(exc),
                workflow_id=context.get("workflow_id"),
            )

    async def on_node_error(
        self,
        error: Exception,
        node_name: str,
        context: dict[str, Any],
    ) -> None:
        """Increment node error counter when a workflow node fails.

        Args:
            error: The exception that caused the node failure.
            node_name: Name of the failed node.
            context: Engine context with ``workflow_name``.
        """
        try:
            raw_wf = context.get("workflow_name") or ""
            wf_name = self._sanitise(raw_wf) if raw_wf else ""
            node_label = self._sanitise(node_name)
            self._node_errors.labels(
                workflow_name=wf_name, node=node_label
            ).inc()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "prometheus.on_node_error.error",
                error=str(exc),
                node_name=node_name,
            )
