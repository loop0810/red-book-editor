from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

# API tests deliberately use the deterministic local gateway; production defaults
# to DeepSeek and must never silently degrade to this provider.
os.environ.setdefault("MODEL_PROVIDER", "stub")

from red_book_editor_server.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
