"""Middleware package for generative-ai-workflow.

Provides the Middleware base class and optional integrations.

Optional extras:
    observability: Prometheus metrics via PrometheusMiddleware.
        Install with: pip install 'generative-ai-workflow[observability]'
"""

from __future__ import annotations

from generative_ai_workflow.middleware.base import Middleware

__all__ = ["Middleware"]
