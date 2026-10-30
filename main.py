"""Application entrypoint.

Run with:
    uvicorn main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core import settings_store
from app.core.config import settings
from app.core.i18n import (
    COOKIE_NAME,
    DEFAULT_LOCALE,
    is_locale_supported,
    set_current_locale,
)
from app.core.templates import templates
from app.settings import router as settings_router
from app.tools.guid_generator import router as guid_generator_router
from app.tools.hash_calculator import router as hash_calculator_router
from app.tools.image_compressor import router as image_compressor_router
from app.tools.image_to_prompt import router as image_to_prompt_router
from app.tools.pdf_to_md import router as pdf_to_md_router
from app.tools.slufy import router as slufy_router
from app.tools.srt_translator import router as srt_translator_router
from app.tools.text_counter import router as text_counter_router


class I18nMiddleware(BaseHTTPMiddleware):
    """Detect and propagate display locale from query, cookie, or defaults."""

    async def dispatch(self, request: Request, call_next):
        lang_param = request.query_params.get("lang")
        cookie_lang = request.cookies.get(COOKIE_NAME)

        chosen_lang = DEFAULT_LOCALE
        should_set_cookie = False

        if lang_param and is_locale_supported(lang_param):
            chosen_lang = lang_param.lower()
            should_set_cookie = True
        elif cookie_lang and is_locale_supported(cookie_lang):
            chosen_lang = cookie_lang.lower()

        set_current_locale(chosen_lang)
        request.state.lang = chosen_lang

        response = await call_next(request)

        if should_set_cookie:
            response.set_cookie(
                key=COOKIE_NAME,
                value=chosen_lang,
                max_age=31536000,
                path="/",
                samesite="lax",
            )

        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.DESCRIPTION,
        version=settings.APP_VERSION,
    )

    # I18n Middleware
    app.add_middleware(I18nMiddleware)

    # Static assets (css / js / images)
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

    # Fast language switcher endpoint
    @app.get("/api/set-language/{lang}", name="set-language")
    @app.post("/api/set-language/{lang}", name="set-language-post")
    async def set_language(request: Request, lang: str):
        valid_lang = lang.lower() if is_locale_supported(lang) else DEFAULT_LOCALE

        accept = request.headers.get("accept", "")
        if "application/json" in accept:
            response = JSONResponse({"status": "ok", "lang": valid_lang})
        else:
            referer = request.query_params.get("next") or request.headers.get("referer") or "/"
            response = RedirectResponse(url=referer, status_code=303)

        response.set_cookie(
            key=COOKIE_NAME,
            value=valid_lang,
            max_age=31536000,
            path="/",
            samesite="lax",
        )
        return response

    # Register each tool's router under the shared /tools prefix.
    app.include_router(image_compressor_router, prefix="/tools", tags=["image-compressor"])
    app.include_router(image_to_prompt_router, prefix="/tools", tags=["image-to-prompt"])
    app.include_router(srt_translator_router, prefix="/tools", tags=["srt-translator"])

    # Register Slufy's router.
    app.include_router(slufy_router, prefix="/tools", tags=["slufy"])

    # Register GUID Generator's router.
    app.include_router(guid_generator_router, prefix="/tools", tags=["guid-generator"])

    # Register Hash Calculator's router.
    app.include_router(hash_calculator_router, prefix="/tools", tags=["hash-calculator"])

    # Register Text Counter's router.
    app.include_router(text_counter_router, prefix="/tools", tags=["text-counter"])

    # Register PDF to Markdown's router.
    app.include_router(pdf_to_md_router, prefix="/tools", tags=["pdf-to-md"])

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
                "custom_home_title": system.get("home_title"),
                "custom_home_description": system.get("home_description"),
            },
        )

    return app


app = create_app()
