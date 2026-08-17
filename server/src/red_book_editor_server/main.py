from __future__ import annotations

import uvicorn

from red_book_editor_server.app.config import get_settings
from red_book_editor_server.app.factory import create_app

app = create_app()


def main() -> None:
    uvicorn.run(
        "red_book_editor_server.main:app",
        host="127.0.0.1",
        port=get_settings().server_port,
    )
