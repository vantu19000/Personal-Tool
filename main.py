"""Application entrypoint.

Run with:
    uvicorn main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.templates import templates
from app.tools.srt_translator import router as srt_translator_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.DESCRIPTION,
        version=settings.APP_VERSION,
    )

    # Static assets (css / js / images)
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

    # Register each tool's router under the shared /tools prefix.
    app.include_router(srt_translator_router, prefix="/tools", tags=["srt-translator"])

    # Dashboard (home)
    @app.get("/", name="dashboard")
    async def dashboard(request: Request):
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"active_tool": "dashboard"},
        )

    return app


app = create_app()
