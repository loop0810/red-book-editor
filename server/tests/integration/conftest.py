from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

SERVER_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set; start PostgreSQL with docker compose up -d postgres")
    return url


@pytest.fixture(scope="session", autouse=True)
def prepare_database(database_url: str) -> Generator[None, None, None]:
    os.environ["DATABASE_URL"] = database_url
    storage_root = Path(tempfile.mkdtemp(prefix="red_book_editor_storage_"))
    os.environ["STORAGE_ROOT"] = str(storage_root)
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")
    shutil.rmtree(storage_root, ignore_errors=True)


@pytest.fixture
def client(database_url: str) -> Generator[TestClient, None, None]:
    os.environ["DATABASE_URL"] = database_url
    from red_book_editor_server.main import app

    with TestClient(app) as test_client:
        yield test_client
