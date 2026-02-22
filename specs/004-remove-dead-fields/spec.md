# Feature Specification: Remove Dead Fields from NodeContext

**Feature Branch**: `004-remove-dead-fields`
**Created**: 2026-02-21
**Status**: Draft
**Input**: User description: "remove dead field like variable in NodeContext to make the code clean"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove `variables` Field from NodeContext (Priority: P1)

As a developer using the framework, the `NodeContext` object passed to every node's `execute` method should contain only fields that are meaningful and populated. Currently the `variables` field is always an empty dict — it is never written to by the engine and the one code path that reads it is unreachable. Removing it eliminates confusion about what the field is for and shrinks the public contract of `NodeContext`.

**Why this priority**: `variables` is provably dead today: the engine hardcodes `variables={}` and no caller or test ever sets it. Leaving it in the public API implies it does something useful, misleading future developers.

**Independent Test**: Remove the `variables` field and verify that all existing tests pass without modification — confirming no production code path depended on the field.

**Acceptance Scenarios**:

1. **Given** a workflow with any combination of `LLMNode`, `TransformNode`, and `ConditionalNode`, **When** the workflow executes, **Then** every node receives a `NodeContext` that does not include a `variables` attribute, and execution completes successfully.

2. **Given** a developer reads the `NodeContext` definition, **When** they inspect its fields, **Then** they see only fields that are actively used: `step_id`, `correlation_id`, `input_data`, `previous_outputs`, and `config`.

3. **Given** the existing test suite, **When** the field is removed, **Then** all tests pass with zero failures.

---

### User Story 2 - Audit and Remove Any Other Dead Fields (Priority: P2)

After removing `variables`, perform a systematic audit of all fields across the framework's core data-model types (`NodeContext`, `NodeResult`, `NodeStatus`, `WorkflowConfig`, etc.) to identify any additional fields that are declared but never meaningfully read or written during normal workflow execution. Remove confirmed dead fields.

**Why this priority**: A targeted audit prevents dead fields from accumulating. It depends on the P1 work establishing the pattern, and is skippable if no additional dead fields are found.

**Independent Test**: Run the full test suite; confirm zero failures. Confirm no references to removed fields remain in `src/` or `tests/`.

**Acceptance Scenarios**:

1. **Given** a completed audit of all public data-model fields, **When** a field has zero meaningful write sites and zero meaningful read sites in `src/`, **Then** that field is removed from the type definition and all related code.

2. **Given** a field that is written somewhere but never read (or vice versa), **When** that asymmetry is confirmed, **Then** the field is either removed or the missing read/write is added — the decision is documented.

---

### Edge Cases

- A field may appear unused in `src/` but be accessed by user code through the public API. Only fields that are both (a) not part of the documented public contract and (b) not referenced in any test or example should be removed.
- The `config` field on `NodeContext` is set by the engine and read by `LLMNode` — it must not be treated as dead even though it is typed loosely.
- If the `variables`-based `_framework_config` lookup in `LLMNode` was intended as the long-term mechanism for propagating framework config, that entire approach should be evaluated before removal — but for now it is unreachable dead code and the hardcoded default is the correct fallback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `variables` field MUST be removed from `NodeContext`.
- **FR-002**: All code that references `context.variables` MUST be updated or removed so no reference to the deleted field remains in `src/`.
- **FR-003**: The model-name fallback logic in `LLMNode` MUST continue to resolve the default model correctly after the `variables` lookup is removed — the hardcoded `"gpt-4o-mini"` default is the correct fallback.
- **FR-004**: No existing public behaviour MUST change as a result of removing the field — all existing tests MUST continue to pass.
- **FR-005**: A systematic audit MUST be performed on all fields of `NodeContext` and other core data-model types to identify any additional dead fields; confirmed dead fields MUST be removed.

### Key Entities

- **NodeContext**: The execution context object passed to each node. After this change it will have fields: `step_id`, `correlation_id`, `input_data`, `previous_outputs`, `config`. The `variables` field will be absent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero references to `context.variables` or `NodeContext.variables` remain anywhere in `src/` after the change.
- **SC-002**: All existing tests pass with zero failures after the field is removed.
- **SC-003**: The `NodeContext` public field count decreases by at least 1, making the API surface smaller and more accurate.
- **SC-004**: The audit of other data-model fields is completed — either additional dead fields are removed, or the audit explicitly concludes no further dead fields exist.

## Assumptions

- `variables` was intended as a future extension point for template-variable injection but was never wired up. No migration path is needed because the package is pre-alpha (v0.x) with no backward-compatibility guarantees.
- The hardcoded `"gpt-4o-mini"` default model in `LLMNode` is acceptable as the sole fallback once the unreachable `_framework_config` lookup via `variables` is removed.
- No external consumer of the library is using `NodeContext.variables` directly, given the package is pre-alpha and the field was never documented or tested.
