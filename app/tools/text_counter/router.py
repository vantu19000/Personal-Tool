"""Router for the Text Counter tool.

GET /tools/text-counter — form page (large textarea + live word/sentence/character stats).

Đếm được tính ngay phía client (JavaScript) để phản hồi tức thì khi gõ/dán;
server chỉ cần render trang.
"""
from fastapi import APIRouter, Request

from app.core.templates import templates

router = APIRouter()


@router.get("/text-counter", name="text-counter")
async def text_counter(request: Request):
    return templates.TemplateResponse(
        request,
        "tools/text_counter.html",
        {"active_tool": "text-counter"},
    )
