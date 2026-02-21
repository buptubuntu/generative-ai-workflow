"""
Integration tests for control flow with LLM integration.

Tests verify:
- End-to-end workflows with ConditionalNode
- LLM provider integration (MockLLMProvider for testing)
- Token usage aggregation across branches
- Context threading through nested nodes
- Real-world conditional routing scenarios

Note: Using MockLLMProvider for deterministic testing.
For real LLM testing, set OPENAI_API_KEY and use OpenAIProvider.
"""

import pytest

from generative_ai_workflow import (
    ConditionalNode,
    LLMNode,
    MockLLMProvider,
    PluginRegistry,
    TransformNode,
    Workflow,
    WorkflowConfig,
    WorkflowStatus,
)


@pytest.fixture(autouse=True)
def setup_mock_provider():
    """Setup MockLLMProvider for all integration tests."""
    PluginRegistry.clear()
    mock = MockLLMProvider(
        responses={
            "sentiment": "positive",
            "negative_sentiment": "negative",
            "positive_response": "Great! I'm glad to hear that.",
            "negative_response": "I'm sorry to hear that. How can I help?",
            "neutral_response": "I understand.",
            "high_priority": "urgent",
            "low_priority": "normal",
        }
    )
    PluginRegistry.register_provider("mock", mock)
    yield
    PluginRegistry.clear()


class TestConditionalNodeWithLLMIntegration:
    """Integration tests for ConditionalNode with LLM calls (T033-T037)."""

    def test_sentiment_routing_workflow(self) -> None:
        """Test ConditionalNode routing based on sentiment analysis (T033).

        Workflow:
        1. Analyze sentiment of input text
        2. Route to positive or negative response branch based on sentiment
        3. Generate appropriate response
        """
        # Node 1: Sentiment analysis (produces sentiment output)
        sentiment_node = LLMNode(
            name="analyze_sentiment",
            prompt="Analyze sentiment: {text}",
            provider="mock",
        )

        # Node 2a: Positive branch
        positive_node = LLMNode(
            name="positive_response",
            prompt="Generate positive response",
            provider="mock",
        )

        # Node 2b: Negative branch
        negative_node = LLMNode(
            name="negative_response",
            prompt="Generate empathetic response",
            provider="mock",
        )

        # Node 3: Conditional routing
        conditional = ConditionalNode(
            name="sentiment_router",
            condition="sentiment == 'positive'",
            true_nodes=[positive_node],
            false_nodes=[negative_node],
        )

        # Create workflow
        workflow = Workflow(
            nodes=[
                TransformNode(
                    name="prepare_context",
                    transform=lambda d: {"text": d["user_input"], "sentiment": "positive"}
                ),
                conditional,
            ],
            config=WorkflowConfig(provider="mock"),
        )

        # Execute
        result = workflow.execute({"user_input": "I love this product!"})

        # Verify
        assert result.status == WorkflowStatus.COMPLETED
        assert "positive_response_output" in result.output or "llm_response" in result.output  # Positive branch executed
        assert "negative_response_output" not in result.output  # Negative branch skipped

    def test_conditional_with_no_else_branch(self) -> None:
        """Test ConditionalNode with no false branch (T034).

        When condition is false and no false_nodes defined, workflow continues
        with empty output from conditional.
        """
        transform_node = TransformNode(
            name="check_threshold",
            transform=lambda d: {"priority": d.get("priority", 5)}
        )

        high_priority_node = LLMNode(
            name="urgent_handler",
            prompt="Handle urgent case",
            provider="mock",
        )

        conditional = ConditionalNode(
            name="priority_filter",
            condition="priority > 8",
            true_nodes=[high_priority_node],
            false_nodes=[],  # No else branch
        )

        workflow = Workflow(
            nodes=[transform_node, conditional],
            config=WorkflowConfig(provider="mock"),
        )

        # Test with low priority (condition false, no else branch)
        result = workflow.execute({"priority": 3})

        assert result.status == WorkflowStatus.COMPLETED
        assert "urgent_handler" not in result.output  # Branch not executed
        assert result.output == {"priority": 3}  # Only transform node output

    def test_nested_conditionals_with_context_threading(self) -> None:
        """Test nested ConditionalNode with context threading (T035).

        Verifies that context data flows correctly through nested conditional branches.
        """
        # Inner conditional
        inner_conditional = ConditionalNode(
            name="severity_check",
            condition="severity == 'high'",
            true_nodes=[
                TransformNode(
                    name="escalate",
                    transform=lambda d: {"action": "escalate", "severity": d["severity"]}
                )
            ],
            false_nodes=[
                TransformNode(
                    name="standard_process",
                    transform=lambda d: {"action": "standard", "severity": d["severity"]}
                )
            ],
        )

        # Outer conditional
        outer_conditional = ConditionalNode(
            name="type_router",
            condition="issue_type == 'bug'",
            true_nodes=[
                TransformNode(
                    name="set_severity",
                    transform=lambda d: {"severity": "high", "issue_type": d["issue_type"]}
                ),
                inner_conditional,
            ],
            false_nodes=[
                TransformNode(
                    name="feature_handler",
                    transform=lambda d: {"action": "feature_review"}
                )
            ],
        )

        workflow = Workflow(
            nodes=[
                TransformNode(
                    name="prepare",
                    transform=lambda d: {"issue_type": "bug"}
                ),
                outer_conditional,
            ],
        )

        result = workflow.execute({})

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["action"] == "escalate"  # Inner true branch executed
        assert result.output["severity"] == "high"

    def test_token_usage_aggregation_across_branches(self) -> None:
        """Test token usage aggregation across conditional branches (T036).

        Verifies that token usage from nested LLM nodes is correctly aggregated.
        """
        # Create mock provider
        PluginRegistry.clear()
        mock = MockLLMProvider(
            responses={"default": "test response content"}  # Token usage simulated from length
        )
        PluginRegistry.register_provider("mock_tokens", mock)

        node1 = LLMNode(name="step1", prompt="prompt1", provider="mock_tokens")
        node2 = LLMNode(name="step2", prompt="prompt2", provider="mock_tokens")
        node3 = LLMNode(name="step3", prompt="prompt3", provider="mock_tokens")

        conditional = ConditionalNode(
            name="router",
            condition="route == 'multi'",
            true_nodes=[node1, node2, node3],  # 3 LLM calls
            false_nodes=[node1],  # 1 LLM call
        )

        workflow = Workflow(
            nodes=[
                TransformNode(
                    name="setup",
                    transform=lambda d: {"route": "multi"}
                ),
                conditional,
            ],
            config=WorkflowConfig(provider="mock_tokens"),
        )

        result = workflow.execute({})

        assert result.status == WorkflowStatus.COMPLETED
        # Should have aggregated tokens from 3 LLM nodes (true branch)
        assert result.metrics.token_usage_total is not None
        # Token usage should be > 0 and aggregated from all 3 nodes
        assert result.metrics.token_usage_total.prompt_tokens > 0
        assert result.metrics.token_usage_total.completion_tokens > 0
        assert result.metrics.token_usage_total.total_tokens > 0

    def test_complex_routing_with_multiple_conditions(self) -> None:
        """Test ConditionalNode with complex multi-stage routing (T037).

        Simulates a real-world scenario with multiple decision points.
        """
        # Stage 1: Check user type
        user_check = ConditionalNode(
            name="user_type_check",
            condition="user_type == 'premium'",
            true_nodes=[
                TransformNode(
                    name="premium_features",
                    transform=lambda d: {
                        **d,
                        "features": ["advanced", "priority_support"],
                        "limit": 1000
                    }
                )
            ],
            false_nodes=[
                TransformNode(
                    name="standard_features",
                    transform=lambda d: {
                        **d,
                        "features": ["basic"],
                        "limit": 100
                    }
                )
            ],
        )

        # Stage 2: Check usage limits
        usage_check = ConditionalNode(
            name="usage_check",
            condition="current_usage < limit",
            true_nodes=[
                TransformNode(
                    name="allow_request",
                    transform=lambda d: {**d, "status": "allowed"}
                )
            ],
            false_nodes=[
                TransformNode(
                    name="deny_request",
                    transform=lambda d: {**d, "status": "denied", "reason": "limit_exceeded"}
                )
            ],
        )

        workflow = Workflow(
            nodes=[
                TransformNode(
                    name="prepare",
                    transform=lambda d: {
                        "user_type": d["user_type"],
                        "current_usage": d["usage"]
                    }
                ),
                user_check,
                usage_check,
            ],
        )

        # Test premium user within limits
        result1 = workflow.execute({"user_type": "premium", "usage": 500})
        assert result1.status == WorkflowStatus.COMPLETED
        assert result1.output["status"] == "allowed"
        assert result1.output["limit"] == 1000

        # Test standard user exceeding limits
        result2 = workflow.execute({"user_type": "standard", "usage": 150})
        assert result2.status == WorkflowStatus.COMPLETED
        assert result2.output["status"] == "denied"
        assert result2.output["limit"] == 100

    def test_conditional_with_previous_node_outputs(self) -> None:
        """Test ConditionalNode accessing outputs from previous nodes.

        Verifies that conditional expressions can reference any previous node output.
        """
        workflow = Workflow(
            nodes=[
                TransformNode(
                    name="step1",
                    transform=lambda d: {"score": 85}
                ),
                TransformNode(
                    name="step2",
                    transform=lambda d: {"threshold": 80}
                ),
                ConditionalNode(
                    name="evaluator",
                    condition="score > threshold",  # References both previous nodes
                    true_nodes=[
                        TransformNode(
                            name="pass",
                            transform=lambda d: {"result": "PASS"}
                        )
                    ],
                    false_nodes=[
                        TransformNode(
                            name="fail",
                            transform=lambda d: {"result": "FAIL"}
                        )
                    ],
                ),
            ],
        )

        result = workflow.execute({})

        assert result.status == WorkflowStatus.COMPLETED
        assert result.output["result"] == "PASS"
        assert result.output["score"] == 85
        assert result.output["threshold"] == 80
