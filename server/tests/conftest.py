from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from red_book_editor_server.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
