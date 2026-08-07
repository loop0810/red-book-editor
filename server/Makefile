.PHONY: lock-check format format-check lint typecheck test integration-test migrate run

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
