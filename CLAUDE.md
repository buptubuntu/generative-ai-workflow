# generative-ai-workflow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-08

## Active Technologies
- Python 3.11+ (existing codebase uses Python 3.11+ with type annotations) (002-workflow-control-flow)
- N/A (in-memory workflow execution state) (002-workflow-control-flow)
- Python 3.11+ + pydantic>=2.0, openai>=1.0, structlog>=24.0, tenacity>=8.0, simpleeval>=1.0.0 (003-rename-step-node)
- Python 3.11+ + Pydantic v2 (`BaseModel`, `Field`), pytest, pytest-asyncio (004-remove-dead-fields)
- N/A (in-memory workflow execution) (004-remove-dead-fields)
- Local filesystem — UUID-named PNG files written to a configurable output directory (default: `./generated_images/`); model weights pre-downloaded by user (001-stable-diffusion-node)

- Python 3.11+ (001-framework-foundation)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 001-stable-diffusion-node: Added Python 3.11+
- 004-remove-dead-fields: Added Python 3.11+ + Pydantic v2 (`BaseModel`, `Field`), pytest, pytest-asyncio
- 003-rename-step-node: Added Python 3.11+ + pydantic>=2.0, openai>=1.0, structlog>=24.0, tenacity>=8.0, simpleeval>=1.0.0


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
