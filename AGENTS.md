# Repository Guidelines

## Project Structure & Module Organization
- Root: this guide. Main code lives in `TradingAgents-CN/`.
- `TradingAgents-CN/tradingagents/`: core Python package (agents, api, dataflows, services, utils).
- `TradingAgents-CN/web/`: Streamlit UI components and pages.
- `TradingAgents-CN/config/` and `.env*`: environment and templates; copy `.env.example` to `.env`.
- `TradingAgents-CN/scripts/`: developer, setup, and ops scripts.
- `TradingAgents-CN/docker*/`, `k8s/`, `terraform/`: deployment assets.
- `TradingAgents-CN/examples/`, `data/`, `logs/`, `reports/`: usage samples and runtime artifacts.

## Build, Test, and Development Commands
- Setup (editable): `cd TradingAgents-CN && python -m pip install -U pip && pip install -e .`.
- Run Web UI: `python start_web.py` then open `http://localhost:8501`.
- Run API (local): `uvicorn tradingagents.api.main:app --host 0.0.0.0 --port 8000`.
- Docker (recommended): `docker-compose up -d --build`.
- Lint/Format: `ruff check . && black . && isort .`.
- Type check (optional): `mypy tradingagents`.
- Tests (if present): `pytest -v`.

## Coding Style & Naming Conventions
- Python 3.10+. Format with Black (line length 88); imports via isort (profile=black); lint with Ruff.
- Prefer type hints; run mypy locally if available.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep functions focused; log via project utilities where available.

## Testing Guidelines
- Framework: `pytest` (markers: `slow`, `network`, `api`, `integration`).
- Layout: place tests under `TradingAgents-CN/tests/` using `test_*.py` files and `Test*` classes.
- Run locally with `pytest -v`; mock external services; avoid real API keys.
- Coverage: no strict gate enforced; add tests for new logic and critical paths.

## Commit & Pull Request Guidelines
- Commit style mirrors history: concise, imperative, often Chinese verbs (e.g., `修复: Web启动递归错误`, `优化: 日志配置`).
- Small, focused commits; reference issues (e.g., `#123`).
- PRs: clear description, rationale, screenshots for UI, steps to reproduce/verify, and impact notes. Ensure `ruff/black/isort` pass and tests run.

## Security & Configuration Tips
- Never commit secrets. Use `.env` (copy from `.env.example`) and `secrets/` vault patterns.
- For ChartingArtist/API, set `CHARTING_ARTIST_ENABLED=true` and `CHARTING_ARTIST_API_URL` as needed.
- Validate local changes with `docker-compose ps` and `docker-compose logs` when debugging services.

