"""
Complete Workflow Example - Demonstrates All Implemented Features

This example showcases:
1. Basic workflow creation and execution
2. LLMStep with provider configuration
3. TransformStep for data manipulation
4. ConditionalStep for branching logic
5. Nested conditionals
6. Context threading across steps
7. Token usage tracking
8. Error handling (critical vs non-critical steps)
9. Async and sync execution modes
10. MockLLMProvider for testing

Scenario: Customer Support Ticket Triage System
- Analyzes customer tickets
- Routes based on sentiment and priority
- Generates appropriate responses
- Escalates critical issues
"""

import asyncio
from generative_ai_workflow import (
    Workflow,
    WorkflowConfig,
    LLMStep,
    TransformStep,
    ConditionalStep,
    MockLLMProvider,
    PluginRegistry,
)


# ============================================================================
# Example 1: Basic Workflow with LLM and Transform Steps
# ============================================================================

def example_1_basic_workflow():
    """Basic workflow: analyze sentiment and generate response."""
    print("\n" + "="*70)
    print("Example 1: Basic Workflow")
    print("="*70)

    # Setup MockLLMProvider for demonstration (no API key needed)
    PluginRegistry.clear()
    mock = MockLLMProvider(responses={
        "sentiment": "positive",
        "response": "Thank you for your feedback! We're glad you're enjoying our service.",
    })
    PluginRegistry.register_provider("mock", mock)

    # Create workflow
    workflow = Workflow(
        steps=[
            # Step 1: Extract ticket text
            TransformStep(
                name="extract_ticket",
                transform=lambda d: {"text": d["ticket"]["message"]}
            ),

            # Step 2: Analyze sentiment using LLM
            LLMStep(
                name="analyze_sentiment",
                prompt="Analyze the sentiment of this customer message: {text}",
                provider="mock",
            ),

            # Step 3: Generate response
            LLMStep(
                name="generate_response",
                prompt="Generate a response to this {analyze_sentiment_output} customer message",
                provider="mock",
            ),
        ],
        config=WorkflowConfig(provider="mock"),
    )

    # Execute
    result = workflow.execute({
        "ticket": {
            "id": "T-001",
            "message": "Your product is amazing! Best purchase ever!",
        }
    })

    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Token Usage: {result.metrics.token_usage_total}")
    print(f"Duration: {result.metrics.total_duration_ms:.2f}ms")


# ============================================================================
# Example 2: Conditional Branching - Sentiment-Based Routing
# ============================================================================

def example_2_conditional_branching():
    """Conditional workflow: route based on sentiment analysis."""
    print("\n" + "="*70)
    print("Example 2: Conditional Branching (Sentiment-Based Routing)")
    print("="*70)

    # Setup provider
    PluginRegistry.clear()
    mock = MockLLMProvider(responses={
        "negative_sentiment": "negative",
        "positive_response": "Thank you for your positive feedback!",
        "negative_response": "We apologize for the inconvenience. Let me help you.",
    })
    PluginRegistry.register_provider("mock", mock)

    # Create positive/negative response steps
    positive_response = LLMStep(
        name="positive_response",
        prompt="Generate a thank you message",
        provider="mock",
    )

    negative_response = LLMStep(
        name="negative_response",
        prompt="Generate an empathetic apology",
        provider="mock",
    )

    # Create workflow with conditional routing
    workflow = Workflow(
        steps=[
            # Prepare context
            TransformStep(
                name="prepare",
                transform=lambda d: {
                    "text": d["message"],
                    "sentiment": "negative"  # Simulated sentiment
                }
            ),

            # Route based on sentiment
            ConditionalStep(
                name="sentiment_router",
                condition="sentiment == 'positive'",
                true_steps=[positive_response],
                false_steps=[negative_response],
            ),
        ],
        config=WorkflowConfig(provider="mock"),
    )

    # Test with negative sentiment
    result = workflow.execute({
        "message": "This product is terrible! It doesn't work at all!",
    })

    print(f"Status: {result.status}")
    print(f"Response Type: {'Positive' if 'positive_response_output' in result.output else 'Negative'}")
    print(f"Output: {result.output}")


# ============================================================================
# Example 3: Nested Conditionals - Priority-Based Escalation
# ============================================================================

def example_3_nested_conditionals():
    """Nested conditionals: multi-level priority and severity checks."""
    print("\n" + "="*70)
    print("Example 3: Nested Conditionals (Priority Escalation)")
    print("="*70)

    PluginRegistry.clear()

    # Inner conditional: severity-based action
    severity_router = ConditionalStep(
        name="severity_router",
        condition="severity == 'critical'",
        true_steps=[
            TransformStep(
                name="escalate_to_manager",
                transform=lambda d: {
                    **d,
                    "action": "escalate",
                    "assigned_to": "manager",
                    "sla": "1 hour",
                }
            )
        ],
        false_steps=[
            TransformStep(
                name="assign_to_agent",
                transform=lambda d: {
                    **d,
                    "action": "assign",
                    "assigned_to": "support_agent",
                    "sla": "24 hours",
                }
            )
        ],
    )

    # Outer conditional: priority-based routing
    priority_router = ConditionalStep(
        name="priority_router",
        condition="priority > 7",
        true_steps=[
            TransformStep(
                name="mark_urgent",
                transform=lambda d: {**d, "severity": "critical"}
            ),
            severity_router,  # Nested conditional
        ],
        false_steps=[
            TransformStep(
                name="mark_normal",
                transform=lambda d: {**d, "severity": "normal"}
            ),
            severity_router,  # Same nested conditional
        ],
    )

    # Create workflow
    workflow = Workflow(
        steps=[
            TransformStep(
                name="analyze_priority",
                transform=lambda d: {
                    "ticket_id": d["id"],
                    "priority": d["priority_score"],
                }
            ),
            priority_router,
        ],
    )

    # Test high priority ticket
    result = workflow.execute({
        "id": "T-123",
        "priority_score": 9,
    })

    print(f"Status: {result.status}")
    print(f"Action: {result.output.get('action')}")
    print(f"Assigned To: {result.output.get('assigned_to')}")
    print(f"Severity: {result.output.get('severity')}")
    print(f"SLA: {result.output.get('sla')}")


# ============================================================================
# Example 4: Complex Expression Evaluation
# ============================================================================

def example_4_complex_expressions():
    """Demonstrate complex boolean expressions in conditions."""
    print("\n" + "="*70)
    print("Example 4: Complex Expression Evaluation")
    print("="*70)

    PluginRegistry.clear()

    workflow = Workflow(
        steps=[
            TransformStep(
                name="setup",
                transform=lambda d: {
                    "user_type": d["user_type"],
                    "usage": d["current_usage"],
                    "limit": 1000 if d["user_type"] == "premium" else 100,
                }
            ),

            # Complex condition: (premium AND under limit) OR admin
            ConditionalStep(
                name="access_check",
                condition="(user_type == 'premium' and usage < limit) or user_type == 'admin'",
                true_steps=[
                    TransformStep(
                        name="grant_access",
                        transform=lambda d: {**d, "access": "granted"}
                    )
                ],
                false_steps=[
                    TransformStep(
                        name="deny_access",
                        transform=lambda d: {**d, "access": "denied", "reason": "limit_exceeded"}
                    )
                ],
            ),
        ],
    )

    # Test premium user within limits
    result1 = workflow.execute({
        "user_type": "premium",
        "current_usage": 500,
    })
    print(f"Premium user (500/1000): Access = {result1.output['access']}")

    # Test standard user exceeding limits
    result2 = workflow.execute({
        "user_type": "standard",
        "current_usage": 150,
    })
    print(f"Standard user (150/100): Access = {result2.output['access']}")


# ============================================================================
# Example 5: Token Usage Tracking Across Branches
# ============================================================================

async def example_5_token_tracking():
    """Track token usage across conditional branches."""
    print("\n" + "="*70)
    print("Example 5: Token Usage Tracking")
    print("="*70)

    PluginRegistry.clear()
    mock = MockLLMProvider(responses={
        "default": "This is a test response with multiple words for token counting",
    })
    PluginRegistry.register_provider("mock", mock)

    # Create steps with LLM calls
    step1 = LLMStep(name="step1", prompt="prompt1", provider="mock")
    step2 = LLMStep(name="step2", prompt="prompt2", provider="mock")
    step3 = LLMStep(name="step3", prompt="prompt3", provider="mock")

    workflow = Workflow(
        steps=[
            TransformStep(
                name="setup",
                transform=lambda d: {"route": d["path"]}
            ),
            ConditionalStep(
                name="router",
                condition="route == 'multi'",
                true_steps=[step1, step2, step3],  # 3 LLM calls
                false_steps=[step1],  # 1 LLM call
            ),
        ],
        config=WorkflowConfig(provider="mock"),
    )

    # Execute with multi path (3 LLM calls)
    result = await workflow.execute_async({"path": "multi"})

    print(f"Status: {result.status}")
    print(f"Total Tokens: {result.metrics.token_usage_total.total_tokens}")
    print(f"Prompt Tokens: {result.metrics.token_usage_total.prompt_tokens}")
    print(f"Completion Tokens: {result.metrics.token_usage_total.completion_tokens}")
    print(f"Steps Executed: 3 LLM steps in true branch")


# ============================================================================
# Example 6: Error Handling - Critical vs Non-Critical Steps
# ============================================================================

def example_6_error_handling():
    """Demonstrate critical vs non-critical step failure handling."""
    print("\n" + "="*70)
    print("Example 6: Error Handling (Critical vs Non-Critical)")
    print("="*70)

    PluginRegistry.clear()

    # Create a step that will fail
    def failing_transform(d):
        raise ValueError("Simulated step failure")

    # Test 1: Critical step failure (workflow should fail)
    workflow_critical = Workflow(
        steps=[
            TransformStep(
                name="step1",
                transform=lambda d: {"data": "success"}
            ),
            TransformStep(
                name="failing_step",
                transform=failing_transform,
                is_critical=True,  # Critical step
            ),
            TransformStep(
                name="step3",
                transform=lambda d: {"final": "done"}
            ),
        ],
    )

    result1 = workflow_critical.execute({})
    print(f"Critical Failure Test:")
    print(f"  Status: {result1.status}")
    print(f"  Error: {result1.error[:50] if result1.error else None}...")

    # Test 2: Non-critical step failure (workflow should continue)
    workflow_noncritical = Workflow(
        steps=[
            TransformStep(
                name="step1",
                transform=lambda d: {"data": "success"}
            ),
            TransformStep(
                name="failing_step",
                transform=failing_transform,
                is_critical=False,  # Non-critical step
            ),
            TransformStep(
                name="step3",
                transform=lambda d: {**d, "final": "done"}
            ),
        ],
    )

    result2 = workflow_noncritical.execute({})
    print(f"\nNon-Critical Failure Test:")
    print(f"  Status: {result2.status}")
    print(f"  Output: {result2.output}")
    print(f"  Note: Workflow continued despite step2 failure")


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("GENERATIVE AI WORKFLOW FRAMEWORK - COMPLETE FEATURE SHOWCASE")
    print("="*70)

    # Run synchronous examples
    example_1_basic_workflow()
    example_2_conditional_branching()
    example_3_nested_conditionals()
    example_4_complex_expressions()
    example_6_error_handling()

    # Run async examples
    asyncio.run(example_5_token_tracking())

    print("\n" + "="*70)
    print("All examples completed successfully!")
    print("="*70)
    print("\nKey Features Demonstrated:")
    print("✓ Basic workflow creation and execution")
    print("✓ LLMStep with provider configuration")
    print("✓ TransformStep for data transformation")
    print("✓ ConditionalStep for if/else branching")
    print("✓ Nested conditionals (multi-level)")
    print("✓ Complex boolean expressions")
    print("✓ Context threading across steps")
    print("✓ Token usage tracking and aggregation")
    print("✓ Error handling (critical vs non-critical)")
    print("✓ Async and sync execution modes")
    print("✓ MockLLMProvider for zero-cost testing")
    print("\nNext: Try with real OpenAI provider by setting OPENAI_API_KEY!")
