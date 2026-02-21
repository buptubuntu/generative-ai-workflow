"""Unit tests for TokenUsageTracker."""

from __future__ import annotations

import pytest

from generative_ai_workflow.observability.tracker import TokenUsageTracker
from generative_ai_workflow.providers.base import TokenUsage


@pytest.fixture
def tracker() -> TokenUsageTracker:
    return TokenUsageTracker()


@pytest.fixture
def usage1() -> TokenUsage:
    return TokenUsage(
        prompt_tokens=10, completion_tokens=5, total_tokens=15, model="m", provider="p"
    )


@pytest.fixture
def usage2() -> TokenUsage:
    return TokenUsage(
        prompt_tokens=20, completion_tokens=8, total_tokens=28, model="m", provider="p"
    )


class TestTokenUsageTracker:
    def test_initial_total_is_none(self, tracker: TokenUsageTracker) -> None:
        assert tracker.total is None

    def test_record_single_node(self, tracker: TokenUsageTracker, usage1: TokenUsage) -> None:
        tracker.record("node1", usage1)
        assert tracker.total is not None
        assert tracker.total.total_tokens == 15

    def test_accumulates_multiple_nodes(
        self, tracker: TokenUsageTracker, usage1: TokenUsage, usage2: TokenUsage
    ) -> None:
        tracker.record("node1", usage1)
        tracker.record("node2", usage2)
        assert tracker.total.prompt_tokens == 30
        assert tracker.total.completion_tokens == 13
        assert tracker.total.total_tokens == 43

    def test_per_node_query(
        self, tracker: TokenUsageTracker, usage1: TokenUsage
    ) -> None:
        tracker.record("summarize", usage1)
        result = tracker.get_node_usage("summarize")
        assert result.total_tokens == 15

    def test_missing_node_returns_none(self, tracker: TokenUsageTracker) -> None:
        assert tracker.get_node_usage("nonexistent") is None

    def test_all_node_usage(
        self, tracker: TokenUsageTracker, usage1: TokenUsage, usage2: TokenUsage
    ) -> None:
        tracker.record("node1", usage1)
        tracker.record("node2", usage2)
        all_usage = tracker.all_node_usage
        assert set(all_usage.keys()) == {"node1", "node2"}

    def test_reset_clears_all(
        self, tracker: TokenUsageTracker, usage1: TokenUsage
    ) -> None:
        tracker.record("node1", usage1)
        tracker.reset()
        assert tracker.total is None
        assert tracker.all_node_usage == {}
