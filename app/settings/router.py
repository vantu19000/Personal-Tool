"""Router for the settings screen.

Routes
------
GET  /settings — render the settings page (one block per tool, from the registry).
POST /settings — validate + persist submitted values (form fields are named
                 ``<block>.<field>``), then re-render with a status message.
"""
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core import settings_store
from app.core.templates import templates

router = APIRouter()


def _page_context(request: Request, data: Dict[str, Dict[str, Any]],
                  saved: bool = False, error: str | None = None) -> Dict[str, Any]:
    return {
        "active_tool": "settings",
        "blocks": list(settings_store.BLOCKS.values()),
        "data": data,
        "saved": saved,
        "error": error,
    }


def _group_form_fields(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Group flat ``<block>.<field>`` form keys into ``{block: {field: value}}``.

    Non-matching keys (e.g. stray fields) are ignored.
    """
    grouped: Dict[str, Dict[str, Any]] = {}
    for key, value in (raw or {}).items():
        if not isinstance(key, str) or "." not in key:
            continue
        block_id, field_key = key.split(".", 1)
        grouped.setdefault(block_id, {})[field_key] = value
    return grouped


@router.get("/settings", name="settings")
async def settings_page(request: Request):
    data = settings_store.get_all()
    return templates.TemplateResponse(request, "settings.html", _page_context(request, data))


@router.post("/settings", name="settings-save")
async def settings_save(request: Request):
    raw = dict(await request.form())
    blocks = _group_form_fields(raw)

    try:
        saved = settings_store.save_blocks(blocks)
    except settings_store.SettingsValidationError as exc:
        return templates.TemplateResponse(
            request,
            "settings.html",
            _page_context(request, settings_store.get_all(), error=str(exc)),
            status_code=400,
        )

    return templates.TemplateResponse(
        request, "settings.html", _page_context(request, saved, saved=True)
    )


# Convenience JSON view (handy for debugging / future API consumers).
@router.get("/settings.json", name="settings-json")
async def settings_json() -> JSONResponse:
    return JSONResponse(settings_store.get_all())
