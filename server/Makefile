.PHONY: lock-check format format-check lint typecheck test integration-test migrate run eval-baseline eval-validate

UV_CACHE_DIR ?= /tmp/red-book-editor-uv-cache
UV_RUN = UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run --project .

lock-check:
	UV_CACHE_DIR="$(UV_CACHE_DIR)" uv lock --check

format:
	$(UV_RUN) python -m ruff format src tests

format-check:
	$(UV_RUN) python -m ruff format --check src tests

lint:
	$(UV_RUN) python -m ruff check src tests

typecheck:
	$(UV_RUN) python -m mypy

test:
	$(UV_RUN) python -m pytest -m 'not integration'

integration-test:
	$(UV_RUN) python -m pytest -m integration

migrate:
	$(UV_RUN) python -m alembic upgrade head

run:
	$(UV_RUN) python -m uvicorn red_book_editor_server.main:app --reload

eval-baseline:
	MODEL_PROVIDER=deepseek $(UV_RUN) python -m scripts.run_agent_eval --repetitions 2 --run-id "$${RUN_ID:-baseline-$$(date +%Y%m%d-%H%M%S)}"

eval-validate:
	$(UV_RUN) python scripts/validate_agent_eval.py --cases evals/agent_baseline/cases.json
