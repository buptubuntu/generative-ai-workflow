# Data Model: Workflow Control Flow

**Feature**: 002-workflow-control-flow
**Date**: 2026-02-08
**Purpose**: Define entities, their relationships, validation rules, and state transitions for control flow primitives

---

## Entity Overview

This feature introduces 4 new classes and extends 1 existing class:

| Entity | Type | Purpose |
|--------|------|---------|
| `ExpressionEvaluator` | Service Class | Safe evaluation of user-supplied expressions |
| `ConditionalStep` | WorkflowStep Subclass | Conditional branching (if/else) |
| `ForEachStep` | WorkflowStep Subclass | Loop iteration over collections |
| `SwitchStep` | WorkflowStep Subclass | Multi-way dispatch (switch/case) |
| `WorkflowConfig` | Extended Model | Add max_iterations, max_nesting_depth config |

---

## 1. ExpressionEvaluator

**Purpose**: Safely evaluate boolean and categorical expressions on workflow context data without arbitrary code execution.

**Type**: Service class (not a Pydantic model, not a WorkflowStep)

**Interface**:

```python
class ExpressionEvaluator:
    """Safe expression evaluator using simpleeval library.

    Supports operators: ==, !=, <, >, <=, >=, in, not in, and, or, not
    Does NOT support: function calls (except whitelisted), attribute access, assignments
    """

    @staticmethod
    def evaluate(
        expression: str,
        context: dict[str, Any],
        *,
        max_string_length: int = 100000,
        max_power: int = 4000000,
    ) -> Any:
        """Evaluate expression against context data.

        Args:
            expression: Python-like expression string (e.g., "sentiment == 'positive'")
            context: Variable bindings (e.g., {"sentiment": "positive", "count": 42})
            max_string_length: Maximum string length (DoS protection)
            max_power: Maximum exponentiation base (DoS protection)

        Returns:
            Evaluation result (typically bool for conditionals, Any for switch expressions)

        Raises:
            ExpressionError: If expression is invalid or references undefined variables
            ExpressionTimeoutError: If evaluation exceeds workflow timeout (handled by engine)

        Examples:
            >>> ExpressionEvaluator.evaluate("x > 10", {"x": 42})
            True
            >>> ExpressionEvaluator.evaluate("type in ['email', 'sms']", {"type": "email"})
            True
        """
        ...

    @staticmethod
    def validate_expression(expression: str) -> None:
        """Validate expression syntax at workflow definition time (eager validation).

        Args:
            expression: Expression string to validate

        Raises:
            ExpressionError: If expression syntax is invalid

        Note:
            Does NOT check for undefined variables (context-dependent, checked at runtime)
        """
        ...
```

**Validation Rules**:
- Expression MUST NOT be empty string
- Expression MUST be valid Python syntax (AST parseable)
- Expression MUST NOT contain:
  - Function definitions (`def`, `lambda`)
  - Assignments (`=`, `+=`, etc.)
  - Import statements (`import`, `from`)
  - Attribute access on non-whitelisted objects (`.` operator restricted)
  - Dunder methods (`__builtins__`, `__import__`, etc.)
- Expression MAY contain:
  - Comparison operators: `==`, `!=`, `<`, `>`, `<=`, `>=`
  - Membership operators: `in`, `not in`
  - Logical operators: `and`, `or`, `not`
  - Literals: strings, numbers, lists, dicts
  - Variable references (resolved from context)

**Error Handling**:
- **Undefined variable**: `ExpressionError("Variable 'missing_var' not found in context (available: ['input', 'step1_output'])")`
- **Syntax error**: `ExpressionError("Invalid expression syntax: unexpected token at position 5")`
- **Evaluation failure**: `ExpressionError("Type mismatch: cannot compare 'str' with 'int'")`

**Dependencies**:
- `simpleeval.simple_eval()` for evaluation
- `simpleeval.DEFAULT_OPERATORS` for operator whitelist

---

## 2. ConditionalStep

**Purpose**: Execute one of two nested step sequences based on a boolean condition.

**Type**: `WorkflowStep` subclass (implements `execute_async()`)

**Model Definition**:

```python
class ConditionalStep(WorkflowStep):
    """Conditional branching workflow step (if/else).

    Evaluates a boolean expression on workflow context data and executes
    either the true branch or false branch based on the result.

    Attributes:
        name: Unique step name (inherited from WorkflowStep)
        condition: Boolean expression string (e.g., "sentiment == 'positive'")
        true_steps: Steps to execute if condition is True
        false_steps: Steps to execute if condition is False (optional, empty if omitted)
        is_critical: If True, step failure aborts workflow (inherited from WorkflowStep)

    Examples:
        >>> ConditionalStep(
        ...     name="sentiment_router",
        ...     condition="sentiment == 'positive'",
        ...     true_steps=[LLMStep(name="positive_response", prompt="...")],
        ...     false_steps=[LLMStep(name="negative_response", prompt="...")],
        ... )
    """

    condition: str  # Boolean expression evaluated on context
    true_steps: list[WorkflowStep]  # Steps if condition == True
    false_steps: list[WorkflowStep] = Field(default_factory=list)  # Steps if condition == False (optional)

    def __init__(
        self,
        name: str,
        condition: str,
        true_steps: list[WorkflowStep],
        false_steps: list[WorkflowStep] | None = None,
        is_critical: bool = True,
    ) -> None:
        super().__init__(name=name, is_critical=is_critical)
        self.condition = condition
        self.true_steps = true_steps
        self.false_steps = false_steps or []
        self._validate()

    def _validate(self) -> None:
        """Validate condition syntax and step structure at definition time."""
        if not self.condition:
            raise ValueError("ConditionalStep condition cannot be empty")
        ExpressionEvaluator.validate_expression(self.condition)
        if not self.true_steps:
            raise ValueError("ConditionalStep must have at least one true_step")
        # false_steps MAY be empty (no else branch)

    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute conditional branch based on context data.

        1. Evaluate condition expression on {**context.input_data, **context.previous_outputs}
        2. Select branch (true_steps if condition == True, false_steps otherwise)
        3. Execute selected branch steps sequentially
        4. Accumulate outputs from branch steps
        5. Return StepResult with accumulated output

        Error Handling:
        - If condition evaluation fails → StepResult(status=FAILED, error="Condition evaluation failed: ...")
        - If child step fails and is_critical → StepResult(status=FAILED, error="Child step 'X' failed: ...")
        - If child step fails and not is_critical → log warning, continue

        Returns:
            StepResult with:
            - output: Accumulated output from executed branch steps
            - duration_ms: Total execution time (condition eval + branch execution)
            - token_usage: Aggregated from nested LLMStep calls (if any)
        """
        ...
```

**Validation Rules**:
- `condition` MUST NOT be empty
- `condition` MUST be valid expression syntax (checked via `ExpressionEvaluator.validate_expression()`)
- `true_steps` MUST NOT be empty (at least one step required)
- `false_steps` MAY be empty (optional else branch)
- All nested steps MUST have unique names within the branch
- Nesting depth MUST NOT exceed `WorkflowConfig.max_nesting_depth` (default: 5)

**State Transitions**:
```
PENDING → RUNNING → [evaluate condition] → [select branch] → [execute branch steps] → COMPLETED
                                                                                       ↓
                                                                                     FAILED (if critical child fails)
```

**Output Structure**:
```python
{
    "<branch_step_1_name>_output": <step 1 output>,
    "<branch_step_2_name>_output": <step 2 output>,
    ...
}
```

**Relationships**:
- **Has-many**: `true_steps: list[WorkflowStep]`
- **Has-many**: `false_steps: list[WorkflowStep]`
- **Uses**: `ExpressionEvaluator` (composition)

---

## 3. ForEachStep

**Purpose**: Iterate over a collection and execute nested steps for each item.

**Type**: `WorkflowStep` subclass (implements `execute_async()`)

**Model Definition**:

```python
class ForEachStep(WorkflowStep):
    """Loop iteration workflow step (for-each).

    Iterates over a list from workflow context and executes loop body steps
    for each item. Collects results from all iterations.

    Attributes:
        name: Unique step name (inherited from WorkflowStep)
        items_var: Variable name containing list to iterate over (e.g., "documents")
        loop_var: Variable name for current item (e.g., "doc") - available in loop body
        loop_steps: Steps to execute for each item
        output_var: Variable name for collected results (e.g., "summaries")
        max_iterations: Maximum iterations allowed (default: None = use WorkflowConfig.max_iterations)
        is_critical: If True, step failure aborts workflow (inherited from WorkflowStep)

    Examples:
        >>> ForEachStep(
        ...     name="batch_processor",
        ...     items_var="documents",    # Read from context.previous_outputs["documents"]
        ...     loop_var="doc",           # Current item available as context.variables["doc"]
        ...     loop_steps=[
        ...         LLMStep(name="summarize", prompt="Summarize: {doc}"),
        ...     ],
        ...     output_var="summaries",   # Results stored in output["summaries"]
        ... )
    """

    items_var: str  # Variable name containing list (read from context)
    loop_var: str  # Variable name for current item (injected into nested step context)
    loop_steps: list[WorkflowStep]  # Steps executed for each item
    output_var: str  # Variable name for collected results
    max_iterations: int | None = None  # Override WorkflowConfig.max_iterations (optional)

    def __init__(
        self,
        name: str,
        items_var: str,
        loop_var: str,
        loop_steps: list[WorkflowStep],
        output_var: str,
        max_iterations: int | None = None,
        is_critical: bool = True,
    ) -> None:
        super().__init__(name=name, is_critical=is_critical)
        self.items_var = items_var
        self.loop_var = loop_var
        self.loop_steps = loop_steps
        self.output_var = output_var
        self.max_iterations = max_iterations
        self._validate()

    def _validate(self) -> None:
        """Validate loop configuration at definition time."""
        if not self.items_var:
            raise ValueError("ForEachStep items_var cannot be empty")
        if not self.loop_var:
            raise ValueError("ForEachStep loop_var cannot be empty")
        if not self.loop_steps:
            raise ValueError("ForEachStep must have at least one loop_step")
        if not self.output_var:
            raise ValueError("ForEachStep output_var cannot be empty")
        if self.max_iterations is not None and self.max_iterations <= 0:
            raise ValueError("ForEachStep max_iterations must be > 0")

    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute loop body for each item in collection.

        1. Resolve items_var from {**context.input_data, **context.previous_outputs}
        2. Validate items is a list
        3. Check iteration count against max_iterations limit
        4. For each item:
           a. Inject loop_var into child context.variables
           b. Execute loop_steps sequentially
           c. Collect output from iteration
           d. Aggregate token usage
        5. Return StepResult with collected results under output_var key

        Error Handling:
        - If items_var not found → StepResult(status=FAILED, error="Variable 'X' not found")
        - If items is not a list → StepResult(status=FAILED, error="Expected list, got <type>")
        - If iteration count > max_iterations → StepResult(status=FAILED, error="Max iterations (100) exceeded")
        - If loop body step fails and is_critical → StepResult(status=FAILED, error="Iteration 5: step 'X' failed: ...")
        - If loop body step fails and not is_critical → log warning, continue to next iteration

        Returns:
            StepResult with:
            - output: {output_var: [result1, result2, ...]}
            - duration_ms: Total execution time (all iterations + overhead)
            - token_usage: Aggregated from all iterations' LLMStep calls
        """
        ...
```

**Validation Rules**:
- `items_var` MUST NOT be empty
- `loop_var` MUST NOT be empty
- `loop_steps` MUST NOT be empty (at least one step required)
- `output_var` MUST NOT be empty
- `max_iterations` MUST be > 0 if specified (default: `WorkflowConfig.max_iterations = 100`)
- Nesting depth MUST NOT exceed `WorkflowConfig.max_nesting_depth` (default: 5)
- `items` resolved from context MUST be a list (not dict, not string, not scalar)

**State Transitions**:
```
PENDING → RUNNING → [resolve items_var] → [for each item: execute loop_steps] → COMPLETED
                                                                                 ↓
                                                                               FAILED (if max_iterations exceeded or critical child fails)
```

**Output Structure**:
```python
{
    output_var: [
        iteration_1_output,  # Aggregated output from loop_steps for item 1
        iteration_2_output,  # Aggregated output from loop_steps for item 2
        ...
    ]
}
```

**Relationships**:
- **Has-many**: `loop_steps: list[WorkflowStep]`
- **References**: `items_var` (variable name, resolved from context)
- **Declares**: `loop_var` (injected into nested step context)
- **Declares**: `output_var` (output key name)

---

## 4. SwitchStep

**Purpose**: Multi-way dispatch based on categorical expression value.

**Type**: `WorkflowStep` subclass (implements `execute_async()`)

**Model Definition**:

```python
class SwitchStep(WorkflowStep):
    """Multi-way dispatch workflow step (switch/case).

    Evaluates an expression and executes the steps for the matching case.
    If no case matches and default_steps are provided, executes default branch.

    Attributes:
        name: Unique step name (inherited from WorkflowStep)
        switch_on: Expression to evaluate (e.g., "document_type")
        cases: Mapping of case values to step lists (e.g., {"email": [...], "report": [...]})
        default_steps: Steps to execute if no case matches (optional)
        is_critical: If True, step failure aborts workflow (inherited from WorkflowStep)

    Examples:
        >>> SwitchStep(
        ...     name="type_router",
        ...     switch_on="document_type",  # Evaluate context.previous_outputs["document_type"]
        ...     cases={
        ...         "email": [LLMStep(name="process_email", prompt="...")],
        ...         "report": [LLMStep(name="process_report", prompt="...")],
        ...         "invoice": [LLMStep(name="process_invoice", prompt="...")],
        ...     },
        ...     default_steps=[LLMStep(name="process_unknown", prompt="...")],  # Optional
        ... )
    """

    switch_on: str  # Expression evaluated on context (typically variable reference like "type")
    cases: dict[str, list[WorkflowStep]]  # Mapping of case values to step lists
    default_steps: list[WorkflowStep] = Field(default_factory=list)  # Fallback if no match (optional)

    def __init__(
        self,
        name: str,
        switch_on: str,
        cases: dict[str, list[WorkflowStep]],
        default_steps: list[WorkflowStep] | None = None,
        is_critical: bool = True,
    ) -> None:
        super().__init__(name=name, is_critical=is_critical)
        self.switch_on = switch_on
        self.cases = cases
        self.default_steps = default_steps or []
        self._validate()

    def _validate(self) -> None:
        """Validate switch configuration at definition time."""
        if not self.switch_on:
            raise ValueError("SwitchStep switch_on cannot be empty")
        ExpressionEvaluator.validate_expression(self.switch_on)
        if not self.cases:
            raise ValueError("SwitchStep must have at least one case")
        for case_name, case_steps in self.cases.items():
            if not case_steps:
                raise ValueError(f"SwitchStep case '{case_name}' must have at least one step")
        # default_steps MAY be empty (no default branch)

    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute steps for matching case.

        1. Evaluate switch_on expression on {**context.input_data, **context.previous_outputs}
        2. Convert result to string for case matching (str(result))
        3. Lookup case in cases dict
        4. If match found → execute case steps
        5. If no match and default_steps exist → execute default_steps
        6. If no match and no default_steps → return FAILED
        7. Accumulate outputs from executed steps

        Error Handling:
        - If switch_on evaluation fails → StepResult(status=FAILED, error="Switch evaluation failed: ...")
        - If no case matches and no default → StepResult(status=FAILED, error="No case matched value 'X' and no default provided")
        - If case step fails and is_critical → StepResult(status=FAILED, error="Case 'X': step 'Y' failed: ...")
        - If case step fails and not is_critical → log warning, continue

        Returns:
            StepResult with:
            - output: Accumulated output from executed case/default steps
            - duration_ms: Total execution time (evaluation + case execution)
            - token_usage: Aggregated from nested LLMStep calls (if any)
        """
        ...
```

**Validation Rules**:
- `switch_on` MUST NOT be empty
- `switch_on` MUST be valid expression syntax (checked via `ExpressionEvaluator.validate_expression()`)
- `cases` MUST NOT be empty (at least one case required)
- Each case MUST have at least one step
- `default_steps` MAY be empty (optional default branch)
- All nested steps across all cases MUST have unique names
- Nesting depth MUST NOT exceed `WorkflowConfig.max_nesting_depth` (default: 5)

**State Transitions**:
```
PENDING → RUNNING → [evaluate switch_on] → [lookup case] → [execute case steps] → COMPLETED
                                                                                   ↓
                                                                                 FAILED (if no match & no default, or critical child fails)
```

**Output Structure**:
```python
{
    "<case_step_1_name>_output": <step 1 output>,
    "<case_step_2_name>_output": <step 2 output>,
    ...
}
```

**Relationships**:
- **Has-many**: `cases: dict[str, list[WorkflowStep]]`
- **Has-many**: `default_steps: list[WorkflowStep]`
- **Uses**: `ExpressionEvaluator` (composition)

---

## 5. WorkflowConfig (Extended)

**Purpose**: Add configuration options for control flow limits.

**Type**: Pydantic `BaseModel` (existing class, extended with new fields)

**Extended Model**:

```python
class WorkflowConfig(BaseModel):
    """Per-workflow configuration overrides.

    Existing fields:
        provider: str = "openai"
        model: str | None = None
        temperature: float | None = None
        max_tokens: int | None = None

    NEW fields for control flow:
        max_iterations: Maximum loop iterations (DoW prevention)
        max_nesting_depth: Maximum control flow nesting depth (DoW prevention)
    """

    # Existing fields (unchanged)
    provider: str = Field(default="openai")
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)

    # NEW fields for control flow
    max_iterations: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum iterations for ForEachStep (DoW prevention)",
    )
    max_nesting_depth: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum control flow nesting depth (DoW prevention)",
    )
```

**Validation Rules**:
- `max_iterations` MUST be >= 1 and <= 10000 (Pydantic validation)
- `max_nesting_depth` MUST be >= 1 and <= 20 (Pydantic validation)
- All existing validation rules remain unchanged (backward compatible)

**Usage**:
```python
config = WorkflowConfig(
    provider="openai",
    max_iterations=50,  # Override default 100
    max_nesting_depth=3,  # Override default 5
)
workflow = Workflow(steps=[...], config=config)
```

---

## Entity Relationships

```
ExpressionEvaluator (service)
    ↑ uses
    |
ConditionalStep ──has-many──> true_steps: list[WorkflowStep]
                └──has-many──> false_steps: list[WorkflowStep]

ForEachStep ──has-many──> loop_steps: list[WorkflowStep]
           └──references──> items_var: str
           └──declares───> loop_var: str, output_var: str

SwitchStep ──has-many──> cases: dict[str, list[WorkflowStep]]
          └──has-many──> default_steps: list[WorkflowStep]
          └──uses──────> ExpressionEvaluator

WorkflowConfig (extended)
    ↓ configures
    |
WorkflowEngine ──enforces limits──> max_iterations, max_nesting_depth
```

---

## Error Taxonomy

| Error Type | Raised By | Condition | Message Example |
|------------|-----------|-----------|-----------------|
| `ExpressionError` | `ExpressionEvaluator` | Invalid syntax | "Invalid expression syntax: unexpected token" |
| `ExpressionError` | `ExpressionEvaluator` | Undefined variable | "Variable 'missing_var' not found (available: ['input', 'step1'])' |
| `ValueError` | `ConditionalStep.__init__()` | Empty condition | "ConditionalStep condition cannot be empty" |
| `ValueError` | `ForEachStep.__init__()` | Empty items_var | "ForEachStep items_var cannot be empty" |
| `ValueError` | `SwitchStep.__init__()` | No cases | "SwitchStep must have at least one case" |
| `StepError` | `ForEachStep.execute_async()` | Max iterations exceeded | "Max iterations (100) exceeded (got 150)" |
| `StepError` | `ForEachStep.execute_async()` | Items not a list | "Expected list for items_var 'docs', got <class 'str'>" |
| `StepError` | `SwitchStep.execute_async()` | No match, no default | "No case matched value 'unknown' and no default provided" |

---

## Performance Characteristics

| Operation | Target Latency | Notes |
|-----------|---------------|-------|
| Expression evaluation | <0.1ms | Cached AST, simpleeval overhead |
| ConditionalStep dispatch | <0.2ms | Condition eval + branch selection |
| ForEachStep per-iteration overhead | <0.1ms | Context creation + output accumulation |
| SwitchStep dispatch | <0.2ms | Expression eval + case lookup |
| Nested step context creation | <0.05ms | StepContext instantiation |

---

**Data Model Complete** | Ready for Contracts Generation
