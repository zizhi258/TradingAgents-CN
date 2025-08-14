# Repository Guidelines

## Project Structure & Module Organization
- `tradingagents/`: Core Python package
  - `agents/`: Analyst, trader, risk, specialized agents (e.g., `specialized/charting_artist.py`)
  - `graph/`: Orchestration (e.g., `trading_graph.py`)
  - `core/`: Multi‑model manager, routing, orchestration
  - `api/`: FastAPI endpoints and API clients
- `web/`: Streamlit app (components, modules, utils, `app.py`)
- `config/`: YAML/JSON configs (roles, pricing, logging)
- `docker*/`: Compose files and Dockerfiles
- `examples/`, `scripts/`, `logs/`, `data/` (mounted in Docker)
- `tests/`: Pytest tests (add here when contributing)

## Build, Test, and Development Commands
- Install (editable):
  - `pip install -e .`
- Run Web UI (dev):
  - `python start_web.py` (opens Streamlit at http://localhost:8501)
- Run API (dev):
  - `uvicorn tradingagents.api.main:app --reload --port 8000`
- Docker (recommended):
  - `docker-compose up -d` (web, api, mongodb, redis)
- Tests:
  - `pytest -v` (uses `pytest.ini` markers and options)
- Lint/Format/Types:
  - `ruff check .` · `black .` · `isort .` · `mypy tradingagents`

## Coding Style & Naming Conventions
- Python 3.10+, 4‑space indent, 88‑char lines (Black).
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_CASE`.
- Tools: Black, Isort, Ruff (pycodestyle/pyflakes/bugbear), Mypy (selective strictness).
- Keep changes minimal and consistent with existing modules.

## Testing Guidelines
- Framework: Pytest; test paths under `tests/` with `test_*.py` files.
- Use markers from `pytest.ini` (e.g., `@pytest.mark.integration`, `@pytest.mark.api`).
- Prefer unit tests near changed logic; add integration tests for API routes and web utilities when feasible.
- Run: `pytest -m "not slow"` locally; avoid network in default test runs.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise subject (≤72 chars), body for rationale and scope.
- Reference issues (e.g., `Fixes #123`) and mention modules touched.
- PRs: include description, screenshots of UI changes, reproduction steps, and risk/rollback notes.
- Ensure CI passes (lint, type checks, tests). Keep PRs focused and reviewable.

## Security & Configuration Tips
- Do not commit secrets. Copy `.env.example` → `.env` and fill `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, etc.
- Prefer Docker for parity; persistent dirs are mounted (`data/`, `logs/`, `config/`).
- When adding providers/models, use human‑friendly labels in UI and normalized IDs in backend.

