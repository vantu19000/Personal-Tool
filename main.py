"""Application entrypoint.

Run with:
    uvicorn main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.core import settings_store
from app.core.config import settings
from app.core.templates import templates
from app.settings import router as settings_router
from app.tools.srt_translator import router as srt_translator_router
from app.tools.slufy import router as slufy_router
from app.tools.guid_generator import router as guid_generator_router
from app.tools.hash_calculator import router as hash_calculator_router


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

    # Register Slufy's router.
    app.include_router(slufy_router, prefix="/tools", tags=["slufy"])

    # Register GUID Generator's router.
    app.include_router(guid_generator_router, prefix="/tools", tags=["guid-generator"])

    # Register Hash Calculator's router.
    app.include_router(hash_calculator_router, prefix="/tools", tags=["hash-calculator"])

    # Global settings screen (homepage text + per-tool options, e.g. SRT prompt).
    app.include_router(settings_router, tags=["settings"])

    # Dashboard (home)
    @app.get("/", name="dashboard")
    async def dashboard(request: Request):
        system = settings_store.get_block("system")
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "active_tool": "dashboard",
                "home_title": system.get("home_title")
                or "Chào mừng bạn đến với Personal Multi-Tool!",
                "home_description": system.get("home_description")
                or "Bộ công cụ web đa năng chạy hoàn toàn trên máy của bạn. "
                   "Dịch phụ đề SRT, tạo GUID, tính hash và nhiều hơn nữa — "
                   "không cần tài khoản, không cần cloud.",
            },
        )

    return app


app = create_app()
