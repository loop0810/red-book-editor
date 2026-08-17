from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from red_book_editor_server.app.config import get_settings
from red_book_editor_server.app.database import (
    create_database_engine,
    create_session_factory,
    get_database_session,
)
from red_book_editor_server.app.logging import configure_logging
from red_book_editor_server.app.middleware import RequestIdMiddleware
from red_book_editor_server.modules.accounts.router import router as accounts_router
from red_book_editor_server.modules.agent_runs.service import AgentRunCoordinator
from red_book_editor_server.modules.content_workflow.router import router as content_workflow_router
from red_book_editor_server.modules.content_workflow.styling.profiles import load_all_profiles
from red_book_editor_server.modules.notes.router import router as notes_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_database_engine(settings)
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.database_session_provider = get_database_session
    coordinator = AgentRunCoordinator(application.state.session_factory, settings)
    application.state.agent_run_coordinator = coordinator
    await coordinator.recover_orphans()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    load_all_profiles()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title="Red Book Editor Server", lifespan=lifespan)
    application.add_middleware(RequestIdMiddleware)
    application.include_router(content_workflow_router)
    from red_book_editor_server.modules.agent_runs.router import router as agent_runs_router

    application.include_router(agent_runs_router)
    application.include_router(accounts_router)
    application.include_router(notes_router)

    @application.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @application.get("/health/ready", response_model=None, tags=["health"])
    async def ready() -> dict[str, str] | JSONResponse:
        if not hasattr(application.state, "settings"):
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        settings = application.state.settings
        return {
            "status": "ready",
            "model_provider": settings.model_provider,
            "model": settings.deepseek_model if settings.model_provider == "deepseek" else "none",
            "model_configured": str(
                settings.model_provider != "deepseek" or bool(settings.model_api_key)
            ).lower(),
        }

    return application
