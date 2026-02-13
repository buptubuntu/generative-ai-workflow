# Tasks: Workflow Control Flow

**Input**: Design documents from `/specs/002-workflow-control-flow/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Unit and integration tests included per constitution requirements (Principles VI & VII)

**Organization**: Tasks grouped by user story to enable independent implementation and testing

**Constitution Compliance**: All tasks align with `.specify/memory/constitution.md` (v1.5.0)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Add simpleeval dependency to pyproject.toml (simpleeval>=1.0.0,<2.0.0)
- [x] T002 Create src/generative_ai_workflow/control_flow.py module structure with imports
- [x] T003 Create tests/unit/test_control_flow.py test file structure
- [x] T004 Create tests/unit/test_expression_evaluator.py test file structure
- [x] T005 Create tests/integration/test_control_flow_integration.py test file structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Expression Evaluator Foundation

- [x] T006 [P] Implement ExpressionError and ExpressionTimeoutError exception classes in src/generative_ai_workflow/control_flow.py
- [x] T007 Implement ExpressionEvaluator.validate_expression() static method in src/generative_ai_workflow/control_flow.py
- [x] T008 Implement ExpressionEvaluator.evaluate() static method with simpleeval integration in src/generative_ai_workflow/control_flow.py
- [x] T009 [P] Add unit tests for ExpressionEvaluator.validate_expression() in tests/unit/test_expression_evaluator.py
- [x] T010 [P] Add unit tests for ExpressionEvaluator.evaluate() with valid expressions in tests/unit/test_expression_evaluator.py
- [x] T011 [P] Add unit tests for ExpressionEvaluator error handling (undefined vars, syntax errors) in tests/unit/test_expression_evaluator.py

### Configuration Extension

- [x] T012 Extend WorkflowConfig with max_iterations field (default=100, ge=1, le=10000) in src/generative_ai_workflow/workflow.py
- [x] T013 Extend WorkflowConfig with max_nesting_depth field (default=5, ge=1, le=20) in src/generative_ai_workflow/workflow.py
- [x] T014 [P] Add unit tests for WorkflowConfig validation (max_iterations, max_nesting_depth) in tests/unit/test_workflow.py

### Public API Exports

- [x] T015 Add ConditionalStep, ForEachStep, SwitchStep exports to src/generative_ai_workflow/__init__.py (ConditionalStep ✓, ForEachStep/SwitchStep deferred to Phase 4-5)
- [x] T016 Add ExpressionError, ExpressionTimeoutError exports to src/generative_ai_workflow/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Conditional Branching (Priority: P1) 🎯 MVP

**Goal**: Enable conditional routing in workflows based on boolean expressions

**Independent Test**: Define a 3-step workflow where step 2 is a conditional that routes to either step 3A or 3B based on step 1's output, execute it, and verify the correct branch ran

### Unit Tests for User Story 1

- [x] T017 [P] [US1] Test ConditionalStep.__init__() validation (empty condition, empty true_steps) in tests/unit/test_control_flow.py
- [x] T018 [P] [US1] Test ConditionalStep with true branch execution (mocked nested steps) in tests/unit/test_control_flow.py
- [x] T019 [P] [US1] Test ConditionalStep with false branch execution (mocked nested steps) in tests/unit/test_control_flow.py
- [x] T020 [P] [US1] Test ConditionalStep with no false_steps (empty else branch) in tests/unit/test_control_flow.py
- [x] T021 [P] [US1] Test ConditionalStep with complex boolean expressions (and, or, not) in tests/unit/test_control_flow.py
- [x] T022 [P] [US1] Test ConditionalStep error handling (condition eval failure, undefined variable) in tests/unit/test_control_flow.py
- [x] T023 [P] [US1] Test ConditionalStep with critical child step failure in tests/unit/test_control_flow.py
- [x] T024 [P] [US1] Test ConditionalStep with non-critical child step failure in tests/unit/test_control_flow.py

### Implementation for User Story 1

- [x] T025 [US1] Implement ConditionalStep.__init__() with validation in src/generative_ai_workflow/control_flow.py (depends on T007, T017-T024)
- [x] T026 [US1] Implement ConditionalStep._validate() method in src/generative_ai_workflow/control_flow.py
- [x] T027 [US1] Implement ConditionalStep.execute_async() with condition evaluation in src/generative_ai_workflow/control_flow.py
- [x] T028 [US1] Implement ConditionalStep branch selection logic in src/generative_ai_workflow/control_flow.py
- [x] T029 [US1] Implement ConditionalStep nested step execution with context threading in src/generative_ai_workflow/control_flow.py
- [x] T030 [US1] Implement ConditionalStep output accumulation from branch steps in src/generative_ai_workflow/control_flow.py
- [x] T031 [US1] Implement ConditionalStep error handling (is_critical check) in src/generative_ai_workflow/control_flow.py
- [x] T032 [US1] Add structured logging for control flow decision (branch taken) in src/generative_ai_workflow/control_flow.py

### Integration Tests for User Story 1

- [X] T033 [US1] Integration test: ConditionalStep with real LLMStep (sentiment routing) in tests/integration/test_control_flow_integration.py
  - **Cost budget**: $0.05 per test
  - Use gpt-4o-mini model
  - Semantic validation (not exact string matching)
- [X] T034 [US1] Integration test: ConditionalStep with no else branch in tests/integration/test_control_flow_integration.py
  - **Cost budget**: $0.05 per test
  - Use gpt-4o-mini model

### Documentation for User Story 1

- [ ] T035 [P] [US1] Add ConditionalStep docstrings with examples in src/generative_ai_workflow/control_flow.py
- [ ] T036 [P] [US1] Verify quickstart.md examples for ConditionalStep (already generated in Phase 1)
- [ ] T037 [US1] Update CHANGELOG.md with ConditionalStep feature (add to project root if not exists)

**Checkpoint**: User Story 1 complete - conditional branching fully functional

---

## Phase 4: User Story 2 - Loop Iteration (Priority: P2)

**Goal**: Enable iteration over collections with step sequences applied to each item

**Independent Test**: Define a workflow that iterates over a list of 3 strings, applying a single LLM step to each, and verify the output contains 3 individual results collected into the final workflow output

### Unit Tests for User Story 2

- [ ] T038 [P] [US2] Test ForEachStep.__init__() validation (empty items_var, loop_var, loop_steps, output_var) in tests/unit/test_control_flow.py
- [ ] T039 [P] [US2] Test ForEachStep with simple loop (3 iterations) in tests/unit/test_control_flow.py
- [ ] T040 [P] [US2] Test ForEachStep with empty list (zero iterations) in tests/unit/test_control_flow.py
- [ ] T041 [P] [US2] Test ForEachStep with max_iterations limit (default 100) in tests/unit/test_control_flow.py
- [ ] T042 [P] [US2] Test ForEachStep exceeding max_iterations (raises error) in tests/unit/test_control_flow.py
- [ ] T043 [P] [US2] Test ForEachStep with custom max_iterations override in tests/unit/test_control_flow.py
- [ ] T044 [P] [US2] Test ForEachStep with loop_var injection into nested context in tests/unit/test_control_flow.py
- [ ] T045 [P] [US2] Test ForEachStep output accumulation under output_var key in tests/unit/test_control_flow.py
- [ ] T046 [P] [US2] Test ForEachStep error handling (items_var not found, items not a list) in tests/unit/test_control_flow.py
- [ ] T047 [P] [US2] Test ForEachStep with critical child step failure (iteration N) in tests/unit/test_control_flow.py
- [ ] T048 [P] [US2] Test ForEachStep with non-critical child step failure (continues to next iteration) in tests/unit/test_control_flow.py
- [ ] T049 [P] [US2] Test ForEachStep with multi-step loop body in tests/unit/test_control_flow.py

### Implementation for User Story 2

- [ ] T050 [US2] Implement ForEachStep.__init__() with validation in src/generative_ai_workflow/control_flow.py (depends on T038-T049)
- [ ] T051 [US2] Implement ForEachStep._validate() method in src/generative_ai_workflow/control_flow.py
- [ ] T052 [US2] Implement ForEachStep.execute_async() with items_var resolution in src/generative_ai_workflow/control_flow.py
- [ ] T053 [US2] Implement ForEachStep list validation and max_iterations check in src/generative_ai_workflow/control_flow.py
- [ ] T054 [US2] Implement ForEachStep loop iteration with loop_var injection in src/generative_ai_workflow/control_flow.py
- [ ] T055 [US2] Implement ForEachStep nested step execution per iteration in src/generative_ai_workflow/control_flow.py
- [ ] T056 [US2] Implement ForEachStep output collection under output_var in src/generative_ai_workflow/control_flow.py
- [ ] T057 [US2] Implement ForEachStep error handling with iteration index attribution in src/generative_ai_workflow/control_flow.py
- [ ] T058 [US2] Implement ForEachStep token usage aggregation across iterations in src/generative_ai_workflow/control_flow.py
- [ ] T059 [US2] Add structured logging for iteration count and errors in src/generative_ai_workflow/control_flow.py

### Integration Tests for User Story 2

- [ ] T060 [US2] Integration test: ForEachStep with real LLMStep (batch summarization) in tests/integration/test_control_flow_integration.py
  - **Cost budget**: $0.05 per test
  - Use gpt-4o-mini model
  - Test 3 iterations
- [ ] T061 [US2] Integration test: ForEachStep with multi-step loop body in tests/integration/test_control_flow_integration.py
  - **Cost budget**: $0.05 per test
  - Use gpt-4o-mini model

### Documentation for User Story 2

- [ ] T062 [P] [US2] Add ForEachStep docstrings with examples in src/generative_ai_workflow/control_flow.py
- [ ] T063 [P] [US2] Verify quickstart.md examples for ForEachStep (already generated in Phase 1)
- [ ] T064 [US2] Update CHANGELOG.md with ForEachStep feature

**Checkpoint**: User Stories 1 AND 2 both work independently

---

## Phase 5: User Story 3 - Multi-Way Dispatch (Priority: P3)

**Goal**: Enable N-way dispatch based on categorical values without nested conditionals

**Independent Test**: Define a workflow with a switch on a "type" variable with 3 cases, execute it 3 times with different type values, and verify each execution follows the correct branch

### Unit Tests for User Story 3

- [ ] T065 [P] [US3] Test SwitchStep.__init__() validation (empty switch_on, empty cases, empty case steps) in tests/unit/test_control_flow.py
- [ ] T066 [P] [US3] Test SwitchStep with exact case match in tests/unit/test_control_flow.py
- [ ] T067 [P] [US3] Test SwitchStep with default_steps (no case match) in tests/unit/test_control_flow.py
- [ ] T068 [P] [US3] Test SwitchStep with no default and no match (raises error) in tests/unit/test_control_flow.py
- [ ] T069 [P] [US3] Test SwitchStep with expression evaluation (not just variable reference) in tests/unit/test_control_flow.py
- [ ] T070 [P] [US3] Test SwitchStep with string conversion for case matching in tests/unit/test_control_flow.py
- [ ] T071 [P] [US3] Test SwitchStep error handling (switch_on eval failure) in tests/unit/test_control_flow.py
- [ ] T072 [P] [US3] Test SwitchStep with critical child step failure in tests/unit/test_control_flow.py
- [ ] T073 [P] [US3] Test SwitchStep with non-critical child step failure in tests/unit/test_control_flow.py

### Implementation for User Story 3

- [ ] T074 [US3] Implement SwitchStep.__init__() with validation in src/generative_ai_workflow/control_flow.py (depends on T065-T073)
- [ ] T075 [US3] Implement SwitchStep._validate() method in src/generative_ai_workflow/control_flow.py
- [ ] T076 [US3] Implement SwitchStep.execute_async() with switch_on evaluation in src/generative_ai_workflow/control_flow.py
- [ ] T077 [US3] Implement SwitchStep string conversion and case matching in src/generative_ai_workflow/control_flow.py
- [ ] T078 [US3] Implement SwitchStep case/default branch execution in src/generative_ai_workflow/control_flow.py
- [ ] T079 [US3] Implement SwitchStep output accumulation from case steps in src/generative_ai_workflow/control_flow.py
- [ ] T080 [US3] Implement SwitchStep error handling (no match, no default) in src/generative_ai_workflow/control_flow.py
- [ ] T081 [US3] Add structured logging for case match decisions in src/generative_ai_workflow/control_flow.py

### Integration Tests for User Story 3

- [ ] T082 [US3] Integration test: SwitchStep with real LLMStep (document type routing) in tests/integration/test_control_flow_integration.py
  - **Cost budget**: $0.05 per test
  - Use gpt-4o-mini model
  - Test 3 different cases
- [ ] T083 [US3] Integration test: SwitchStep with default branch in tests/integration/test_control_flow_integration.py
  - **Cost budget**: $0.05 per test
  - Use gpt-4o-mini model

### Documentation for User Story 3

- [ ] T084 [P] [US3] Add SwitchStep docstrings with examples in src/generative_ai_workflow/control_flow.py
- [ ] T085 [P] [US3] Verify quickstart.md examples for SwitchStep (already generated in Phase 1)
- [ ] T086 [US3] Update CHANGELOG.md with SwitchStep feature

**Checkpoint**: All 3 user stories independently functional

---

## Phase 6: Nested Control Flow & Edge Cases

**Purpose**: Support nesting and handle edge cases across all control flow constructs

### Nesting Support

- [ ] T087 [P] Implement nesting depth tracking in ConditionalStep.execute_async() in src/generative_ai_workflow/control_flow.py
- [ ] T088 [P] Implement nesting depth tracking in ForEachStep.execute_async() in src/generative_ai_workflow/control_flow.py
- [ ] T089 [P] Implement nesting depth tracking in SwitchStep.execute_async() in src/generative_ai_workflow/control_flow.py
- [ ] T090 [P] Add max_nesting_depth validation (raises error if exceeded) in src/generative_ai_workflow/control_flow.py

### Nested Control Flow Tests

- [ ] T091 [P] Test ConditionalStep nested inside ForEachStep in tests/unit/test_control_flow.py
- [ ] T092 [P] Test ForEachStep nested inside ConditionalStep in tests/unit/test_control_flow.py
- [ ] T093 [P] Test SwitchStep nested inside ForEachStep in tests/unit/test_control_flow.py
- [ ] T094 [P] Test 5-level nesting depth (max default) in tests/unit/test_control_flow.py
- [ ] T095 [P] Test exceeding max_nesting_depth (raises error) in tests/unit/test_control_flow.py

### Edge Case Tests

- [ ] T096 [P] Test forward reference detection (variable not yet produced) in tests/unit/test_control_flow.py
- [ ] T097 [P] Test timeout interaction with mid-loop execution (partial results) in tests/unit/test_control_flow.py
- [ ] T098 [P] Test cancellation interaction with mid-loop execution (partial results) in tests/unit/test_control_flow.py

### Integration Test for Nested Control Flow

- [ ] T099 Integration test: Complex nested control flow (loop with conditional inside) in tests/integration/test_control_flow_integration.py
  - **Cost budget**: $0.05 per test
  - Use gpt-4o-mini model

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories and final compliance verification

### Performance Optimization

- [ ] T100 [P] Add performance benchmarks for expression evaluation (<0.1ms) in tests/unit/test_expression_evaluator.py
- [ ] T101 [P] Add performance benchmarks for conditional dispatch (<0.2ms) in tests/unit/test_control_flow.py
- [ ] T102 [P] Add performance benchmarks for loop iteration overhead (<0.1ms per iteration) in tests/unit/test_control_flow.py
- [ ] T103 [P] Add performance benchmark for 100-iteration loop (≤10% degradation) in tests/unit/test_control_flow.py
- [ ] T104 Profile control flow hot paths with cProfile and optimize if needed

### Documentation & Examples

- [ ] T105 [P] Verify all quickstart.md examples execute correctly
- [ ] T106 [P] Add type annotations verification (mypy check on control_flow.py)
- [ ] T107 Create examples/control_flow/ directory with advanced usage patterns
- [ ] T108 Update README.md with control flow feature overview (if exists in project root)

### Constitution Compliance (Final Verification)

- [ ] T109 [P] **Principle VI**: Verify unit test coverage ≥80% for control_flow.py
- [ ] T110 [P] **Principle VII**: Verify integration test costs ≤$0.30 total (6 tests @ $0.05 each)
- [ ] T111 [P] **Principle II**: Documentation review - all public APIs have docstrings with examples
- [ ] T112 [P] **Principle VIII**: Security audit
  - Expression injection defense tested (no eval(), no __builtins__)
  - DoW prevention tested (max_iterations, max_nesting_depth)
  - PII protection verified (no new PII exposure)
- [ ] T113 [P] **Principle X**: Backward compatibility check
  - Run all existing v0.1.0 tests (should pass unchanged)
  - Verify no breaking changes to WorkflowStep interface
  - CHANGELOG.md complete with semantic versioning
- [ ] T114 [P] **Principle XI**: Extensibility validation
  - ExpressionEvaluator custom functions tested (advanced feature)
  - Control flow steps work as standard WorkflowStep plugins
- [ ] T115 [P] **Principle IV**: Observability verification
  - Token aggregation tested across nested steps
  - Structured logging tested (control flow decisions logged)
  - Correlation IDs propagated through nested steps
- [ ] T116 Constitution compliance report
  - Verify all 12 principles satisfied
  - Document compliance status in plan.md Complexity Tracking (currently "No violations")

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion (can run parallel with US1)
- **User Story 3 (Phase 5)**: Depends on Foundational completion (can run parallel with US1, US2)
- **Nested Control Flow (Phase 6)**: Depends on US1, US2, US3 completion
- **Polish (Phase 7)**: Depends on all previous phases completion

### User Story Dependencies

- **User Story 1 (P1 - MVP)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation tasks execute sequentially (build on each other)
- Integration tests run after implementation complete
- Documentation tasks can run in parallel with implementation

### Parallel Opportunities

- **Setup (Phase 1)**: T003, T004, T005 can run in parallel
- **Foundational (Phase 2)**: T006-T011 can run in parallel, T012-T014 can run in parallel
- **User Story 1 Tests**: T017-T024 can all run in parallel (test writing)
- **User Story 2 Tests**: T038-T049 can all run in parallel (test writing)
- **User Story 3 Tests**: T065-T073 can all run in parallel (test writing)
- **All 3 user stories (Phases 3-5)** can be worked on in parallel after Foundational complete
- **Nesting Support**: T087-T089 can run in parallel
- **Nested Tests**: T091-T098 can run in parallel
- **Performance**: T100-T103 can run in parallel
- **Final verification**: T109-T115 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Write all unit tests together (run in parallel):
Task: "Test ConditionalStep.__init__() validation in tests/unit/test_control_flow.py"
Task: "Test ConditionalStep with true branch execution in tests/unit/test_control_flow.py"
Task: "Test ConditionalStep with false branch execution in tests/unit/test_control_flow.py"
Task: "Test ConditionalStep with no false_steps in tests/unit/test_control_flow.py"
# ... (all T017-T024 in parallel)

# Then implement sequentially (dependencies on each other):
Task: "Implement ConditionalStep.__init__() with validation"
Task: "Implement ConditionalStep._validate() method"
Task: "Implement ConditionalStep.execute_async() with condition evaluation"
# ... (T025-T032 sequentially)

# Finally run integration tests and docs in parallel:
Task: "Integration test: ConditionalStep with real LLMStep"
Task: "Add ConditionalStep docstrings with examples"
Task: "Verify quickstart.md examples"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T016) - **CRITICAL BLOCKER**
3. Complete Phase 3: User Story 1 (T017-T037)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo conditional branching feature

**MVP Scope**: 37 tasks (T001-T037), estimated ConditionalStep only

### Incremental Delivery

1. Setup + Foundational → Foundation ready (T001-T016)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP: ConditionalStep)
3. Add User Story 2 → Test independently → Deploy/Demo (ForEachStep)
4. Add User Story 3 → Test independently → Deploy/Demo (SwitchStep)
5. Add Nested Control Flow → Test → Deploy/Demo (Phase 6)
6. Polish and final verification → Full v0.2.0 release (Phase 7)

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

- **Developer A**: User Story 1 (T017-T037)
- **Developer B**: User Story 2 (T038-T064)
- **Developer C**: User Story 3 (T065-T086)
- **All together**: Nested control flow (Phase 6) and Polish (Phase 7)

---

## Summary Statistics

- **Total Tasks**: 116
- **Setup Phase**: 5 tasks
- **Foundational Phase**: 11 tasks (BLOCKING)
- **User Story 1**: 21 tasks (MVP)
- **User Story 2**: 27 tasks
- **User Story 3**: 22 tasks
- **Nested Control Flow**: 13 tasks
- **Polish & Compliance**: 17 tasks

**Test Distribution**:
- Unit tests: ~60 tasks
- Integration tests: 6 tasks ($0.30 total budget)
- Performance tests: 5 tasks

**Parallel Opportunities**: ~70 tasks marked [P] can run in parallel within their phase

**MVP Delivery**: 37 tasks (Setup + Foundational + US1)

**Full Feature**: 116 tasks

---

## Notes

- [P] tasks = different files or independent work, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- **Principle XII — Branch-Per-Task**: Each task worked on in its own branch (`002-T###-<description>`)
- Merge to main only after unit AND integration tests pass
- Stop at any checkpoint to validate story independently
- All tasks follow existing codebase patterns (WorkflowStep ABC, StepContext, StepResult)
