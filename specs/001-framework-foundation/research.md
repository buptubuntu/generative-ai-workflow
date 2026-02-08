# Research: Framework Foundation

**Date**: 2026-02-08
**Feature**: 001-framework-foundation

## Decisions

### 1. Language & Runtime

**Decision**: Python 3.11+

**Rationale**: Dominant language for AI/ML tooling; asyncio is mature; excellent OpenAI SDK and LLM ecosystem; pytest is the standard test runner referenced in the constitution.

**Alternatives Considered**:
- TypeScript/Node.js: Strong async, but Python ecosystem is better for LLM integrations
- Rust: High performance, but development friction is too high for a framework prototype

---

### 2. Structured JSON Logging

**Decision**: `structlog` with orjson renderer

**Rationale**: Actively maintained (unlike `python-json-logger`); superior performance via orjson (bytes output); native bound logger pattern automatically includes context (correlation IDs, workflow IDs) in all messages; library-friendly since it doesn't require stdlib logging configuration by consumers.

**Alternatives Considered**:
- `python-json-logger`: Less maintained, bolts JSON onto stdlib logging
- Standard `logging` with JSON formatter: Manual configuration required, no context binding

---

### 3. LLM API Testing / Fixture Pattern

**Decision**: `respx` for unit test HTTP mocking + `vcrpy` for integration test record/replay

**Rationale**: OpenAI Python SDK v1 uses `httpx` internally; `respx` is purpose-built for httpx mocking with native async/pytest support. A dedicated `openai-responses` pytest plugin also exists. For integration tests needing true record/replay, `vcrpy` complements respx.

**Alternatives Considered**:
- `pytest-recording`: Less ecosystem adoption for httpx-based testing
- Manual mocking: Error-prone and brittle

---

### 4. Retry / Backoff

**Decision**: `tenacity`

**Rationale**: Industry-standard Python retry library; `AsyncRetrying` supports asyncio natively (async sleeps); decorator-based API works identically on sync and async functions; configurable stop/wait/retry strategies; actively maintained.

**Alternatives Considered**:
- `backoff`: Smaller ecosystem, less maintained
- Custom implementation: Reinventing a well-solved problem

---

### 5. OpenAI Python SDK Pattern

**Decision**: `AsyncOpenAI()` client with async context manager for lifecycle management

**Rationale**: OpenAI SDK v1 uses httpx internally; `AsyncOpenAI` provides the async client with identical feature parity to sync client; context manager ensures proper connection cleanup; custom `http_client` parameter supports injection for testing (respx).

---

### 6. Python Packaging

**Decision**: `pyproject.toml` with `hatchling` build backend

**Rationale**: PEP 621 standard; hatchling is recommended by Python Packaging User Guide as the modern default; no `setup.py` needed; clean dependency management for library distribution.

**Alternatives Considered**:
- Setuptools: Legacy, more complex
- Flit: Less feature-rich than hatchling
- Poetry: Opinionated lock file approach; adds complexity for a library

---

### 7. Data Validation

**Decision**: `pydantic` v2 with `pydantic-settings` for configuration

**Rationale**: Industry standard for Python data validation; excellent performance in v2; `BaseSettings` supports env var loading natively; full type annotation support aligns with Principle II.

---

### 8. Package Name

**Decision**: `generative_ai_workflow` (import name), `generative-ai-workflow` (PyPI/package name)

**Rationale**: Matches repository name; descriptive; avoids naming conflicts with `langchain`, `aiworkflow`, etc.
