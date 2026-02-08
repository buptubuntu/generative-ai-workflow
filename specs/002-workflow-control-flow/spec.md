# Feature Specification: Workflow Control Flow

**Feature Branch**: `002-workflow-control-flow`
**Created**: 2026-02-08
**Status**: Draft
**Input**: User description: "Add control flow support (for loops, conditionals, branching) to the workflow engine"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conditional Branching in Workflows (Priority: P1) 🎯 MVP

As a framework user, I want to define conditional branches in my workflow so that different steps execute based on the output of a previous step (e.g., route to a summarization path vs. a classification path depending on input content).

**Why this priority**: Conditional logic (if/else) is the most fundamental control flow primitive. Without it, workflows cannot adapt to runtime data, severely limiting real-world usefulness.

**Independent Test**: Can be tested by defining a 3-step workflow where step 2 is a conditional that routes to either step 3A or step 3B based on step 1's output, executing it, and verifying the correct branch ran.

**Acceptance Scenarios**:

1. **Given** a workflow with a conditional branch defined on a step output, **When** the condition evaluates to true, **Then** the workflow executes the "true" branch steps and skips the "false" branch steps
2. **Given** a workflow with a conditional branch, **When** the condition evaluates to false, **Then** the workflow executes the "false" branch steps and skips the "true" branch steps
3. **Given** a conditional branch with no matching condition and no default branch, **When** the workflow executes, **Then** the framework raises a clear error indicating the unhandled condition
4. **Given** a conditional branch where the condition expression references an undefined variable, **When** the workflow executes, **Then** the framework raises a descriptive error identifying the missing variable

---

### User Story 2 - Loop Iteration Over Collections (Priority: P2)

As a framework user, I want to iterate over a collection of items and apply the same set of steps to each item so that I can process lists of inputs (e.g., summarize each document in a batch) without duplicating workflow steps.

**Why this priority**: Loops enable batch processing — a very common AI workflow pattern (process N documents, analyze N records). Builds directly on the conditional MVP.

**Independent Test**: Can be tested by defining a workflow that iterates over a list of 3 strings, applying a single LLM step to each, and verifying the output contains 3 individual results collected into the final workflow output.

**Acceptance Scenarios**:

1. **Given** a workflow with a for-each loop over a list of items, **When** the workflow executes, **Then** each item in the list is processed by the loop body steps in order
2. **Given** a for-each loop, **When** all iterations complete, **Then** the collected results from all iterations are available as a single list in the workflow context for subsequent steps
3. **Given** a for-each loop over an empty list, **When** the workflow executes, **Then** the loop body is skipped and an empty collection is passed forward
4. **Given** a for-each loop where one iteration fails, **When** the workflow executes, **Then** the framework raises an error with attribution identifying the failing iteration index and the step that failed

---

### User Story 3 - Multi-Way Dispatch (Switch/Case) (Priority: P3)

As a framework user, I want to dispatch workflow execution to one of several named branches based on a categorical value so that I can route to specialized sub-workflows without chaining multiple if/else conditions (e.g., route by document type: "email" → email handler, "report" → report handler, "invoice" → invoice handler).

**Why this priority**: Extends conditional branching to N-way dispatch, simplifying complex routing logic that would otherwise require nested conditionals.

**Independent Test**: Can be tested by defining a workflow with a switch on a "type" variable with 3 cases, executing it 3 times with different type values, and verifying each execution follows the correct branch.

**Acceptance Scenarios**:

1. **Given** a switch construct with multiple named cases and a default, **When** the switch value matches a defined case, **Then** that case's steps execute
2. **Given** a switch construct with a default case, **When** the switch value matches no defined case, **Then** the default case's steps execute
3. **Given** a switch construct with no default case, **When** the switch value matches no defined case, **Then** the framework raises a clear error indicating the unmatched value

---

### Edge Cases

- What happens when a conditional expression references a step output that does not exist yet (forward reference)?
- How does the framework handle runaway loops (a loop whose collection is dynamically grown inside the loop body)?
- What happens when nested control flow structures exceed the configured depth limit?
- How does token usage and execution metrics aggregate across loop iterations?
- What happens when a loop body contains a conditional that itself branches?
- How does timeout interact with loops — does timeout apply to total workflow execution time or per-iteration?
- What happens when a branch condition produces an error during evaluation (e.g., type mismatch, missing key)?
- How does cancellation of an async workflow interact with mid-loop execution?

## Requirements *(mandatory)*

### Functional Requirements

**Conditional Branching:**
- **FR-001**: System MUST allow users to define a conditional construct that evaluates a boolean expression on workflow context data and routes execution to one of two branches (true branch, false branch)
- **FR-002**: System MUST support boolean expressions referencing any variable present in the current workflow context (step outputs, input data)
- **FR-003**: System MUST execute only the branch matching the condition result; the non-matching branch MUST be skipped entirely
- **FR-004**: System MUST raise a descriptive error when a conditional expression references an undefined variable
- **FR-005**: System MUST support an optional else/default branch that executes when the condition is false and no explicit false-branch is defined

**Loop Iteration:**
- **FR-006**: System MUST allow users to define a for-each loop that iterates over a list value from the workflow context
- **FR-007**: System MUST make the current iteration item available within the loop body as a named context variable
- **FR-008**: System MUST collect loop body outputs from all iterations into a list and expose it in the workflow context after the loop completes
- **FR-009**: System MUST skip loop execution and pass an empty collection forward when the loop target is an empty list
- **FR-010**: System MUST enforce a configurable maximum iteration limit (default: 100) to prevent runaway loops; exceeding the limit raises a clear error
- **FR-011**: System MUST provide step-level error attribution within loops, including the iteration index of the failing step

**Multi-Way Dispatch (Switch):**
- **FR-012**: System MUST allow users to define a switch construct that evaluates a single expression and dispatches to one of N named cases
- **FR-013**: System MUST support an optional default case that executes when no named case matches
- **FR-014**: System MUST raise a descriptive error when no case matches and no default is defined

**Integration with Existing Engine:**
- **FR-015**: System MUST support nesting of control flow constructs (conditional inside loop, loop inside conditional, switch inside loop) up to a configurable depth limit (default: 5 levels)
- **FR-016**: System MUST aggregate token usage and execution metrics across all loop iterations and executed branches in the final WorkflowResult
- **FR-017**: System MUST log all control flow decisions (branch taken, iteration count, case matched) in the structured execution log
- **FR-018**: System MUST maintain backward compatibility — existing workflows without control flow constructs MUST execute identically after this change
- **FR-019**: System MUST support control flow constructs in both asynchronous and synchronous execution modes

**Error Handling:**
- **FR-020**: System MUST provide clear, actionable error messages for all control flow errors (undefined variable, unmatched case, max iterations exceeded, nesting depth exceeded, expression evaluation failure)

### Key Entities

- **ConditionalStep**: A workflow construct that evaluates a boolean expression and routes execution to one of two step sequences (true branch, false branch)
- **ForEachStep**: A workflow construct that iterates over a list from the workflow context, executing a body sequence for each item and collecting results
- **SwitchStep**: A workflow construct that dispatches to one of several named case sequences based on a single expression value
- **ConditionExpression**: A boolean or categorical expression that can reference workflow context variables, evaluated at runtime
- **ControlFlowMetrics**: Execution metrics capturing branch decisions, iteration counts, and nested control flow statistics, aggregated into the overall WorkflowResult

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Framework users can define a workflow with a 3-way conditional branch in under 20 lines of code
- **SC-002**: All existing workflows (without control flow) continue to execute identically after the feature is released (zero regressions)
- **SC-003**: Loops process at least 100 iterations without performance degradation beyond 10% compared to equivalent manually-unrolled sequential workflows of the same length
- **SC-004**: Nested control flow up to 5 levels deep executes correctly without errors
- **SC-005**: All control flow errors include actionable messages that allow users to diagnose and fix issues without consulting documentation (self-service resolution rate ≥ 90%)
- **SC-006**: Token usage and execution metrics are captured with 100% completeness across all loop iterations and executed branches

## Assumptions

- Control flow expressions reference workflow context variables by name using the same `{variable}` placeholder syntax already used in prompt templates
- Loop iteration order is always sequential (not parallel) in this release; parallel iteration is deferred to a future enhancement
- The "for loop" in scope is for-each over a collection (not a counter-based numeric loop); numeric ranges can be expressed as pre-built lists
- Boolean expressions support basic comparisons (equality, inequality, contains, startswith) but not arbitrary code execution, to prevent security risks
- Control flow constructs are composable workflow step types, not a separate DSL or configuration file format
- Nesting depth and max iteration limits are configurable per workflow, not globally enforced
