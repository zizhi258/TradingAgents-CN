# Repository Guidelines

## Project Structure & Module Organization
- Root: this guide. Main code in `TradingAgents-CN/`.
- `tradingagents/`: core package (agents, api, dataflows, services, utils).
- `web/`: Streamlit app (`app.py`, components, modules, utils).
- `config/` + `.env*`: environment templates and configs.
- `scripts/`: developer, setup, and ops scripts.
- `docker*/`, `k8s/`, `terraform/`: deployment assets.
- `examples/`, `data/`, `logs/`, `reports/`: samples and runtime artifacts.

## Build, Test, and Development Commands
- Setup (editable): `cd TradingAgents-CN && python -m pip install -U pip && pip install -e .`
- Run Web UI: `python start_web.py` → open `http://localhost:8501`
- Run API (local): `uvicorn tradingagents.api.main:app --host 0.0.0.0 --port 8000`
- Docker (recommended): `docker-compose up -d --build`
- Lint/Format: `ruff check . && black . && isort .`
- Type check: `mypy tradingagents`
- Tests: `pytest -v`

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indent. Black line length 88; isort profile=black; lint with Ruff.
- Prefer type hints and dataclasses; keep functions small and focused.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Centralize logging via project utilities; avoid ad‑hoc prints and UI-specific hacks.

## Testing Guidelines
- Framework: Pytest. Place tests under `TradingAgents-CN/tests/` as `test_*.py`.
- Markers (if used): `slow`, `network`, `api`, `integration`.
- Run locally with `pytest -v`; mock external services; avoid real API keys.
- No strict coverage gate; add tests for new logic and critical paths.

## Commit & Pull Request Guidelines
- Commits: concise, imperative; Chinese verbs common (e.g., `修复: Web启动递归错误`, `优化: 日志配置`).
- Reference issues (e.g., `#123`); keep changes small and focused.
- Before PR: ensure `ruff/black/isort` pass and tests run.
- PRs include description, rationale, linked issues, UI screenshots (if relevant), and verify steps.

## Security & Configuration Tips
- Never commit secrets. Copy `.env.example` → `.env` and set required keys.
- For ChartingArtist/API, set `CHARTING_ARTIST_ENABLED=true` and `CHARTING_ARTIST_API_URL` as needed.
- Use `docker-compose ps` / `docker-compose logs` to validate service status during local debugging.

