"""Execution metrics collection utilities.

Provides helpers for timing steps and collecting structured metrics.
The ExecutionMetrics model is in workflow.py; this module adds collection helpers.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator


class StepTimer:
    """Context manager / utility for measuring step execution time.

    Example::

        timer = StepTimer()
        with timer.measure("my_step"):
            # ... step execution ...
        print(f"Duration: {timer.durations['my_step']}ms")
    """

    def __init__(self) -> None:
        self._durations: dict[str, float] = {}

    @contextmanager
    def measure(self, step_name: str) -> Generator[None, None, None]:
        """Measure the wall-clock time for a step.

        Args:
            step_name: Step identifier for the duration dict.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            self._durations[step_name] = (time.perf_counter() - start) * 1000

    @property
    def durations(self) -> dict[str, float]:
        """Recorded step durations in milliseconds."""
        return dict(self._durations)

    def total_ms(self) -> float:
        """Sum of all measured step durations."""
        return sum(self._durations.values())
