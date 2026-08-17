.PHONY: lock-check format format-check lint typecheck test integration-test migrate run eval-baseline eval-validate eval-quality-gate

UV_CACHE_DIR ?= /tmp/red-book-editor-uv-cache
UV_RUN = UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run --project .
SERVER_HOST ?= 127.0.0.1
SERVER_PORT ?= 8100
export SERVER_HOST
export SERVER_PORT
SCORE_ID ?= $(RUN_ID)
BASELINE_SCORE_ID ?= $(BASELINE_RUN_ID)

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
	$(UV_RUN) python -m uvicorn red_book_editor_server.main:app --reload --host "$(SERVER_HOST)" --port "$(SERVER_PORT)"

eval-baseline:
	MODEL_PROVIDER=deepseek $(UV_RUN) python -m scripts.run_agent_eval --repetitions 2 --run-id "$${RUN_ID:-baseline-$$(date +%Y%m%d-%H%M%S)}"

eval-validate:
	$(UV_RUN) python scripts/validate_agent_eval.py --cases evals/agent_baseline/cases.json

eval-quality-gate:
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required" >&2; exit 2)
	@test -n "$(SCORE_ID)" || (echo "SCORE_ID is required" >&2; exit 2)
	$(UV_RUN) python -m scripts.quality_gate \
		--run "evals/agent_baseline/runs/$(RUN_ID).json" \
		--scores "evals/agent_baseline/scores/$(SCORE_ID).json" \
		$(if $(BASELINE_RUN_ID),--baseline-run "evals/agent_baseline/runs/$(BASELINE_RUN_ID).json" --baseline-scores "evals/agent_baseline/scores/$(BASELINE_SCORE_ID).json",)
