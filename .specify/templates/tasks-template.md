---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Constitution Compliance**: All tasks must align with `.specify/memory/constitution.md` (v1.5.0). Key requirements:
- **Observability** (Principle IV): Token tracking, LLM logging, workflow state tracking
- **Testing** (Principles VI & VII): Fixture-based tests, semantic assertions, cost budgets ($0.10/test, $5/suite)
- **Security** (Principle VIII): Prompt injection defense, PII protection, DoW prevention
- **Backward Compatibility** (Principle X): No breaking changes OR migration guide
- **Extensibility** (Principle XI): Use plugin system for customization
- See Phase 2 (Foundational) for required infrastructure tasks and User Story 1 for implementation patterns

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Standard Infrastructure (adjust based on your project)

- [ ] T004 Setup database schema and migrations framework (if applicable)
- [ ] T005 [P] Implement authentication/authorization framework (if applicable)
- [ ] T006 [P] Setup API routing and middleware structure (if applicable)
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling infrastructure
- [ ] T009 Setup environment configuration management

### Constitution-Required Infrastructure (AI Workflow Framework)

**Observability (Principle IV):**
- [ ] T010 [P] Implement token tracking system in src/observability/token_tracker.py
  - Track prompt_tokens, completion_tokens, total_tokens
  - Emit metrics: llm.tokens.{prompt,completion,total}
  - Provide query API for applications
- [ ] T011 [P] Implement LLM interaction logger in src/observability/llm_logger.py
  - Log model, parameters, latency, rate limits
  - Structured JSON format with correlation IDs
- [ ] T012 [P] Implement workflow state tracker in src/observability/workflow_tracker.py
  - Log state transitions, step execution times

**Testing Infrastructure (Principles VI & VII):**
- [ ] T013 [P] Create fixture recording system in src/testing/fixture_recorder.py
  - VCR pattern for LLM responses
  - Save/load fixtures from tests/fixtures/
- [ ] T014 [P] Create cost tracking test utility in src/testing/cost_tracker.py
  - Track test costs, enforce budgets
  - Pytest plugin for @cost_budget decorator
- [ ] T015 [P] Create semantic assertion helpers in src/testing/semantic_assertions.py
  - Length validation, format validation, similarity checks
  - Helpers for non-deterministic LLM output testing

**Extensibility (Principle XI):**
- [ ] T016 [P] Implement plugin registry in src/plugins/registry.py
  - Declarative plugin registration
  - Plugin discovery and loading
- [ ] T017 [P] Implement middleware system in src/plugins/middleware.py
  - before_llm_call, after_llm_call hooks
  - Middleware chain execution

**Security (Principle VIII):**
- [ ] T018 [P] Implement prompt injection defense utilities in src/security/prompt_defense.py
  - Structured prompt templates with delimiters
  - Input validation for injection patterns
- [ ] T019 [P] Implement PII detection in src/security/pii_detector.py
  - Regex patterns for emails, SSNs, credit cards
  - Redaction utilities
- [ ] T020 [P] Implement rate limiting in src/security/rate_limiter.py
  - Per-user token limits
  - DoW prevention

**Documentation (Principles I, II, X):**
- [ ] T021 Create CHANGELOG.md in project root (semantic versioning format)
- [ ] T022 Create UPGRADING.md in project root (migration guides)
- [ ] T023 [P] Create plugin development guide in .specify/guides/plugin-development.md

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

**Constitution Compliance**: This user story demonstrates all 11 constitutional principles in practice

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

**Unit Tests (Principle VI - AI-Specific):**
- [ ] T024 [P] [US1] Pure logic tests in tests/unit/test_[name]_logic.py
  - Deterministic tests for prompt formatting, parsing, calculations
  - Standard assertions: `assert format_prompt(x) == "Expected"`
- [ ] T025 [P] [US1] Fixture-based tests in tests/unit/test_[name]_llm.py
  - Record LLM responses to tests/fixtures/[name].yaml
  - Mock LLM provider (NO real API calls in unit tests)
- [ ] T026 [P] [US1] Semantic assertion tests in tests/unit/test_[name]_semantic.py
  - Test output characteristics (length, format, content presence)
  - NO exact string matching for LLM outputs

**Integration Tests (Principle VII - AI-Specific):**
- [ ] T027 [US1] Integration test with cost budget in tests/integration/test_[name].py
  - **Cost budget**: $0.10 per test (document in test docstring)
  - Use cheap model (e.g., gpt-3.5-turbo, claude-haiku)
  - Semantic validation (assert length, format, not exact strings)
  - Model version pinned (e.g., `@pytest.mark.model_version("gpt-4-0613")`)

**Security Tests (Principle VIII - AI-Specific):**
- [ ] T028 [P] [US1] Prompt injection test in tests/security/test_[name]_injection.py
  - Test defense against common injection patterns
  - Verify system prompts not leaked
- [ ] T029 [P] [US1] PII protection test in tests/security/test_[name]_pii.py
  - Verify PII detection before LLM calls
  - Test redaction functionality

### Implementation for User Story 1

**Data Models (Principles I, II):**
- [ ] T030 [P] [US1] Create [Entity1] model in src/models/[entity1].py
  - Define interface with abstract base class
  - Add docstrings with purpose, attributes, examples
  - Include type annotations
- [ ] T031 [P] [US1] Create [Entity2] model in src/models/[entity2].py
  - Define interface first
  - Document all public methods

**Business Logic (Principles III, IV):**
- [ ] T032 [US1] Implement [Service] in src/services/[service].py (depends on T030, T031)
  - Follow SOLID principles (dependency injection via interfaces)
  - **Add token tracking** (use token_tracker from foundational phase)
  - **Add LLM logging** (model, latency, parameters)
  - Structured logging with correlation IDs
  - Docstrings for all public methods with examples

**Feature Implementation (Principles V, XI):**
- [ ] T033 [US1] Implement [endpoint/feature] in src/[location]/[file].py
  - **Use plugin system** (register via PluginRegistry if extending LLM providers)
  - Provide sensible defaults (convention over configuration)
  - Configuration validation at startup
- [ ] T034 [US1] Add validation and error handling
  - Input validation (anti-prompt injection)
  - PII detection before LLM calls
  - Rate limiting enforcement

**Documentation & Compliance (Principles II, X):**
- [ ] T035 [US1] Document public APIs with usage examples
  - At least one example per non-trivial interface
  - Document performance characteristics
- [ ] T036 [US1] Update CHANGELOG.md
  - Document changes per semantic versioning
  - Note any deprecations or breaking changes
- [ ] T037 [US1] Verify backward compatibility
  - No breaking changes to public APIs OR migration guide in UPGRADING.md

**Checkpoint**: At this point, User Story 1 should be fully functional, testable independently, and constitution-compliant

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T019 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T020 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T021 [US2] Implement [Service] in src/services/[service].py
- [ ] T022 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T023 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T024 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T025 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T027 [US3] Implement [Service] in src/services/[service].py
- [ ] T028 [US3] Implement [endpoint/feature] in src/[location]/[file].py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

**Standard Polish:**
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX Run quickstart.md validation

**Constitution Compliance (Final Verification):**
- [ ] TXXX [P] **Principle VI**: Add additional unit tests if coverage below 80%
- [ ] TXXX [P] **Principle VII**: Verify all integration tests under cost budget ($5 total)
- [ ] TXXX [P] **Principle II**: Documentation review - all public APIs documented
- [ ] TXXX [P] **Principle VIII**: Security audit - verify all AI threats addressed
  - Prompt injection defense tested
  - PII protection verified
  - DoW prevention (rate limits, input limits) tested
  - Output sanitization verified
- [ ] TXXX [P] **Principle X**: Backward compatibility check
  - Verify no breaking changes OR UPGRADING.md updated
  - CHANGELOG.md complete with all changes
  - Deprecation warnings implemented for removed features
- [ ] TXXX [P] **Principle XI**: Plugin system validation
  - Example plugins tested
  - Plugin documentation complete (.specify/guides/plugin-development.md)
  - Plugin isolation verified (failure doesn't crash framework)
- [ ] TXXX [P] **Principle IV**: Observability verification
  - Token tracking tested across all LLM calls
  - Metrics emitted correctly
  - Logs structured and include correlation IDs
- [ ] TXXX Constitution compliance report
  - Generate report of all principles and compliance status
  - Document any justified violations in plan.md Complexity Tracking

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- **Principle XII — Branch-Per-Task**: Each task MUST be worked on in its own branch
  (`<task-id>-<short-description>`). Merge to main only after unit AND integration tests pass.
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
