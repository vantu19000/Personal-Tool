"""Router for the SRT Translator tool.

Currently a UI skeleton — the actual translation logic will be added later.
"""
from fastapi import APIRouter, Request

from app.core.templates import templates

router = APIRouter()


@router.get("/srt-translator", name="srt-translator")
async def srt_translator(request: Request):
    return templates.TemplateResponse(
        request,
        "tools/srt_translator.html",
        {"active_tool": "srt-translator"},
    )
