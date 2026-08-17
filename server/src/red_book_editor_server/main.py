from __future__ import annotations

import uvicorn

from red_book_editor_server.app.config import get_settings
from red_book_editor_server.app.factory import create_app

app = create_app()


def main() -> None:
    uvicorn.run(
        "red_book_editor_server.main:app",
        host=get_settings().server_host,
        port=get_settings().server_port,
    )
