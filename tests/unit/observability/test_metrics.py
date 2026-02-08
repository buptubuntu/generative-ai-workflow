"""Unit tests for ExecutionMetrics and StepTimer."""

from __future__ import annotations

import time

import pytest

from generative_ai_workflow import ExecutionMetrics
from generative_ai_workflow.observability.metrics import StepTimer
from generative_ai_workflow.providers.base import TokenUsage


class TestStepTimer:
    def test_measures_duration(self) -> None:
        timer = StepTimer()
        with timer.measure("step1"):
            time.sleep(0.01)  # 10ms
        assert timer.durations["step1"] >= 10.0

    def test_multiple_steps(self) -> None:
        timer = StepTimer()
        with timer.measure("a"):
            pass
        with timer.measure("b"):
            pass
        assert "a" in timer.durations
        assert "b" in timer.durations

    def test_total_ms_sums_durations(self) -> None:
        timer = StepTimer()
        timer._durations = {"a": 10.0, "b": 20.0}
        assert timer.total_ms() == 30.0


class TestExecutionMetrics:
    def test_default_values(self) -> None:
        m = ExecutionMetrics()
        assert m.total_duration_ms == 0.0
        assert m.steps_completed == 0
        assert m.steps_failed == 0
        assert m.token_usage_total is None

    def test_step_duration_tracking(self) -> None:
        m = ExecutionMetrics()
        m.step_durations["step1"] = 15.5
        assert m.step_durations["step1"] == 15.5

    def test_token_usage_aggregation(self) -> None:
        m = ExecutionMetrics()
        m.token_usage_total = TokenUsage(
            prompt_tokens=10, completion_tokens=5, total_tokens=15, model="m", provider="p"
        )
        assert m.token_usage_total.total_tokens == 15
