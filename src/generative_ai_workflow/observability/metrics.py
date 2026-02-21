"""Execution metrics collection utilities.

Provides helpers for timing nodes and collecting structured metrics.
The ExecutionMetrics model is in workflow.py; this module adds collection helpers.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator


class NodeTimer:
    """Context manager / utility for measuring node execution time.

    Example::

        timer = NodeTimer()
        with timer.measure("my_node"):
            # ... node execution ...
        print(f"Duration: {timer.durations['my_node']}ms")
    """

    def __init__(self) -> None:
        self._durations: dict[str, float] = {}

    @contextmanager
    def measure(self, node_name: str) -> Generator[None, None, None]:
        """Measure the wall-clock time for a node.

        Args:
            node_name: Node identifier for the duration dict.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            self._durations[node_name] = (time.perf_counter() - start) * 1000

    @property
    def durations(self) -> dict[str, float]:
        """Recorded node durations in milliseconds."""
        return dict(self._durations)

    def total_ms(self) -> float:
        """Sum of all measured node durations."""
        return sum(self._durations.values())


# Backward-compatible alias — removed in v0.2.0; use NodeTimer
StepTimer = NodeTimer
