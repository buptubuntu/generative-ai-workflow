# Feature Specification: Rename Step Concept to Node

**Feature Branch**: `003-rename-step-node`
**Created**: 2026-02-21
**Status**: Draft
**Input**: User description: "change step concept to node"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build Workflows Using Node Terminology (Priority: P1)

A developer building a workflow uses `LLMNode`, `TransformNode`, and `ConditionalNode` as the primary building blocks, replacing the former "step" vocabulary. The public API and all documentation consistently refer to these as nodes, so the developer never encounters the old terminology.

**Why this priority**: The core building block concept affects every interaction with the framework. Consistent naming is the foundation for all other user stories.

**Independent Test**: Can be fully tested by constructing a workflow using only the new node classes and verifying the workflow executes correctly, delivering a usable multi-node pipeline.

**Acceptance Scenarios**:

1. **Given** a developer imports the framework, **When** they reference `LLMNode`, `TransformNode`, `ConditionalNode`, and `WorkflowNode`, **Then** all types are available and fully functional.
2. **Given** a developer attempts to use the old step names (e.g., `LLMStep`), **When** they run their code, **Then** they receive an import error indicating the names no longer exist.
3. **Given** a developer reads any error message or log output produced by the framework, **When** the message refers to a workflow building block, **Then** it uses the term "node" not "step".

---

### User Story 2 - Extend the Framework with Custom Nodes (Priority: P2)

A developer creating a custom building block subclasses `WorkflowNode` (formerly `WorkflowStep`) to add domain-specific behaviour. The base class name, its methods, and all related type names use "node" terminology.

**Why this priority**: Extensibility is a stated design goal of the framework. Consistent base class naming ensures custom nodes feel natural alongside built-in ones.

**Independent Test**: Can be fully tested by implementing a custom class that inherits from `WorkflowNode` and registering it in a workflow.

**Acceptance Scenarios**:

1. **Given** a developer subclasses `WorkflowNode`, **When** they register and execute the custom node in a workflow, **Then** it behaves identically to built-in nodes.
2. **Given** a developer reads the base class interface, **When** they inspect method signatures and docstrings, **Then** all references use "node" terminology.

---

### User Story 3 - Read Updated Documentation and Examples (Priority: P3)

A developer learning the framework reads quickstart guides, examples, and API reference material that consistently uses "node" as the conceptual term for workflow building blocks.

**Why this priority**: Documentation consistency reinforces the conceptual model; mismatched terminology creates confusion even if the code works correctly.

**Independent Test**: Can be verified by auditing all documentation files and example code to confirm zero remaining occurrences of the old "step" terminology in user-facing contexts.

**Acceptance Scenarios**:

1. **Given** a developer reads the quickstart guide, **When** they follow the code examples, **Then** all examples use node names and the word "node" throughout.
2. **Given** a developer searches the documentation for "step" as a concept name, **When** they review results, **Then** no user-facing content uses "step" as the primary building block term.

---

### Edge Cases

- What happens when third-party code already depends on the old step names? The framework must communicate the rename clearly via a migration note in the changelog.
- How does the system handle workflow definitions or logs that reference "step" under the old terminology? A clear migration path or descriptive error must be provided.
- If a user names their own custom subclass with "step" in its identifier, do internal framework messages still use "node"? Yes — the framework controls only its own output terminology.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The public API MUST expose all workflow building block types under "node" names (`LLMNode`, `TransformNode`, `ConditionalNode`, `WorkflowNode`).
- **FR-002**: The old "step" names (`LLMStep`, `TransformStep`, `WorkflowStep`, `ConditionalStep`) MUST be permanently removed from the public API with no backwards-compatible aliases or deprecation shims retained.
- **FR-003**: All framework-generated messages (errors, warnings, log output) MUST use the term "node" when referring to workflow building blocks.
- **FR-004**: All bundled documentation, quickstart guides, and code examples MUST be updated to use "node" terminology exclusively.
- **FR-005**: The `WorkflowNode` base class MUST provide the same interface and extension points as the former `WorkflowStep` base class, with no functional regression.
- **FR-006**: Existing workflow behaviour (execution, result collection, metrics, observability) MUST be fully preserved after the rename.
- **FR-007**: The source module previously named for "step" MUST be renamed so that its import path uses "node"; the old import path MUST NOT remain accessible.

### Key Entities

- **WorkflowNode**: The abstract base type representing a single unit of work within a workflow (formerly WorkflowStep).
- **LLMNode**: A node that issues a prompt to a language model and returns its response (formerly LLMStep).
- **TransformNode**: A node that applies a data transformation without calling a language model (formerly TransformStep).
- **ConditionalNode**: A node that evaluates an expression and routes execution to one of two branches (formerly ConditionalStep).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of public API symbols that previously contained "Step" are renamed to "Node" with no aliases remaining.
- **SC-002**: Zero occurrences of the old step terminology appear in user-facing documentation, quickstart guides, or bundled examples.
- **SC-003**: All existing tests are updated to use node terminology and continue to pass; at least one test explicitly verifies that importing the old step names raises an import error.
- **SC-004**: A developer migrating from the old API can identify every required change within 5 minutes by reading the migration or changelog notes.

## Clarifications

### Session 2026-02-21

- Q: Should the old step names be hard removed, kept as deprecated aliases, or removed after one deprecation cycle? → A: Hard remove — old names deleted entirely, no aliases kept.
- Q: Should the source module file `step.py` (importable as `generative_ai_workflow.step`) be renamed? → A: Yes — rename to `node.py`; old module path removed entirely.
- Q: For test coverage, should existing tests be renamed, new tests added, or both? → A: Both — rename existing tests to use node names AND add a test verifying old names raise an import error.

## Assumptions

- The project is pre-alpha (v0.x), so a hard rename without a long deprecation window is acceptable.
- "Node" is intended as a permanent conceptual replacement; the old "step" names will not be maintained long-term.
- The source module file currently named for "step" is in scope and must be renamed to reflect "node"; the old module import path will no longer be available. Purely private implementation details (local variables, internal helpers not importable from outside the package) are not required to change.
- Configuration file or serialisation format changes are out of scope unless they expose user-visible "step" labels.
