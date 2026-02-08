# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md` (current version: v1.5.0). Each principle must be addressed - either compliant (✓) or violation justified in Complexity Tracking section below.

### ✅ Principle I: Interface-First Design
- [ ] Public APIs designed with clear interfaces (abstract base classes, protocols)
- [ ] Implementation details hidden behind contracts
- [ ] Interface contracts documented before implementation begins
- [ ] Breaking interface changes require major version increment

### ✅ Principle II: Documented Public Interfaces
- [ ] All public APIs have docstrings/comments with: purpose, parameters, returns, exceptions
- [ ] At least one usage example per non-trivial interface
- [ ] Type annotations included where language supports
- [ ] Performance characteristics documented for critical paths

### ✅ Principle III: SOLID Principles
- [ ] Single Responsibility: Each class/module has one reason to change
- [ ] Open/Closed: Extend via composition/inheritance, not modification
- [ ] Dependencies injected via interfaces (not concrete implementations)
- [ ] Violations justified in Complexity Tracking section

### ✅ Principle IV: Observability (AI-Specific)
**Traditional Observability:**
- [ ] Structured logging (JSON/key-value format) implemented
- [ ] Metrics for critical operations (latency, throughput, error rates)
- [ ] Correlation IDs for distributed tracing

**AI-Specific Observability (REQUIRED):**
- [ ] **Token tracking implemented** for all LLM operations:
  - Capture prompt_tokens, completion_tokens, total_tokens
  - Emit metrics: `llm.tokens.prompt`, `llm.tokens.completion`, `llm.tokens.total`
  - Token counts in log messages for LLM calls
  - API provided for applications to query token usage
- [ ] **LLM interaction logging**:
  - Model name/version, request parameters (temperature, max_tokens)
  - Latency breakdown, success/failure status
  - Rate limit headers captured
- [ ] **Cost estimation support**: Token usage in machine-readable format
- [ ] **Workflow state tracking**: State transitions, step execution times logged

### ✅ Principle V: Configurable But Convention First
- [ ] Sensible defaults provided for all optional configuration
- [ ] All config options documented with examples and default values
- [ ] Configuration validated at startup with clear error messages
- [ ] Configuration kept minimal (prefer convention over configuration)
- [ ] Environment variables used for deployment config (secrets, URLs)

### ✅ Principle VI: Unit Tests (AI-Specific)
**Traditional Requirements:**
- [ ] ≥80% code coverage on business logic
- [ ] Fast tests (<100ms typical)
- [ ] External dependencies mocked/stubbed

**AI-Specific Testing Strategy (REQUIRED):**
- [ ] **Pure logic** (prompt formatting, parsing, calculations):
  - Traditional deterministic tests with exact assertions
  - 100% reliable, no mocking needed
- [ ] **LLM integration code**:
  - Fixture-based testing (VCR pattern) implemented
  - Fixtures stored in `tests/fixtures/` and version controlled
  - Regeneration strategy defined (prompt changes, model upgrades)
- [ ] **Non-deterministic outputs**:
  - Semantic assertions (length, format, content presence)
  - NO exact string matching for LLM outputs
  - Semantic similarity checks if needed
- [ ] **Mock LLM providers** in unit tests (NEVER call real APIs in unit tests)

### ✅ Principle VII: Integration Tests (AI-Specific)
**Cost Management (CRITICAL):**
- [ ] **Cost budget documented**: $____ per test, $____ per suite (max $5.00)
- [ ] **Tiered execution strategy**:
  - Commit hooks: No LLM calls (mocks only)
  - PR checks: Smoke tests with cheap models
  - Nightly: Full suite with production models
- [ ] Cost optimization strategy (use cheaper models, cache responses)

**AI-Specific Requirements:**
- [ ] Semantic validation (not exact string matching)
- [ ] Model version pinned for reproducibility (e.g., `gpt-4-0613`)
- [ ] Provider health checks implemented
- [ ] PII sanitization verified in test data

### ✅ Principle VIII: Security (AI-Specific)
**Traditional Security:**
- [ ] Input validation, authentication, authorization implemented
- [ ] Secrets in environment variables/secret managers (NEVER hardcoded)
- [ ] Encryption (TLS in transit, encryption at rest for sensitive data)
- [ ] OWASP Top 10 vulnerabilities addressed

**AI-Specific Security (10 threat categories - address all CRITICAL):**
- [ ] **1. Prompt Injection Defense** (CRITICAL):
  - Structured prompts with clear delimiters (XML tags, triple quotes)
  - Input validation to detect injection patterns
  - System prompts NEVER exposed to users
- [ ] **2. PII Protection** (CRITICAL):
  - PII detection before sending to LLM providers
  - Redaction/tokenization implemented
  - Sanitized logging (no unredacted PII in logs)
- [ ] **3. Denial of Wallet Prevention** (CRITICAL):
  - Input length limits enforced (e.g., max 10K tokens)
  - Per-user rate limiting (tokens per minute/hour/day)
  - Timeout limits on LLM calls
- [ ] **4. Data Isolation** (CRITICAL):
  - Multi-tenancy boundaries enforced
  - User data segregation verified
- [ ] **5-10. Other Security Measures**:
  - Output sanitization, API key security, rate limiting, monitoring

### ✅ Principle IX: Use LTS Dependencies
- [ ] LTS versions used for runtime platforms (Node.js LTS, Python stable, etc.)
- [ ] Dependencies pinned with version ranges in manifest
- [ ] Security scanning configured (Dependabot, Snyk, or equivalent)
- [ ] Regular update schedule defined (monthly/quarterly)

### ✅ Principle X: Backward Compatibility (Framework-Critical)
- [ ] **No breaking changes** to public APIs within major version OR:
- [ ] Migration guide provided in `UPGRADING.md` for breaking changes
- [ ] Semantic versioning followed (MAJOR.MINOR.PATCH)
- [ ] Deprecated features have warnings (minimum 1 minor version notice)
- [ ] `CHANGELOG.md` updated with all changes

### ✅ Principle XI: Extensibility & Plugin Architecture
- [ ] **Uses plugin system** for extensibility (NOT hardcoded)
- [ ] Extension points documented (which interfaces can be extended)
- [ ] Plugin registration is declarative and simple
- [ ] Plugin lifecycle defined (init, execute, cleanup)
- [ ] Plugin isolation implemented (failures don't cascade to framework)
- [ ] Example plugin provided for guidance

### ✅ Principle XII: Branch-Per-Task Development Workflow
- [ ] Each task has its own dedicated feature branch before work begins
- [ ] Branch naming follows convention: `<task-id>-<short-description>`
- [ ] Unit tests pass before opening PR/MR
- [ ] Integration tests pass before merging to main
- [ ] No direct commits to main branch

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
