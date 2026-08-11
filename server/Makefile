.PHONY: lock-check format format-check lint typecheck test integration-test migrate run eval-baseline eval-validate

lock-check:
	uv lock --check

format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy

test:
	uv run pytest -m 'not integration'

integration-test:
	uv run pytest -m integration

migrate:
	uv run alembic upgrade head

run:
	uv run uvicorn red_book_editor_server.main:app --reload

eval-baseline:
	MODEL_PROVIDER=deepseek uv run python scripts/run_agent_eval.py --repetitions 2 --run-id "$${RUN_ID:-baseline-$$(date +%Y%m%d-%H%M%S)}"

eval-validate:
	uv run python scripts/validate_agent_eval.py --cases evals/agent_baseline/cases.json
