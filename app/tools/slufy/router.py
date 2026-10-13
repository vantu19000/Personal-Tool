"""Router for the Slufy tool.

GET  /tools/slufy        — form page (input text to slugify)
POST /tools/slufy/slug   — convert the input text to a slug
"""
from fastapi import APIRouter, Form, Request

from app.core.templates import templates

router = APIRouter()


@router.get("/slufy", name="slufy")
async def slufy(request: Request):
    return templates.TemplateResponse(
        request,
        "tools/slufy.html",
        {"active_tool": "slufy"},
    )


@router.post("/slufy/slug", name="slufy-slug")
async def slufy_slug(text: str = Form(..., description="Chuỗi văn bản cần chuyển thành slug")):
    """Convert arbitrary text (including Vietnamese) to a URL-friendly slug."""
    if not text or not text.strip():
        return {"ok": False, "error": "Vui lòng nhập chuỗi văn bản."}

    slug = _slugify(text)
    return {"ok": True, "slug": slug}


def _slugify(text: str) -> str:
    """Convert *text* into a URL-safe, link-friendly slug.

    Vietnamese-aware. Most accented Latin letters (``à é ơ ư ệ …``) turn
    into their plain base letter via ``unicodedata.normalize('NFD')`` plus
    stripping combining marks. ``đ``/``Đ`` (d-with-stroke) has *no* NFD
    decomposition, so it is mapped explicitly — otherwise it would leak
    into the slug as a non-ASCII character (e.g. ``"Đà Nẵng" -> "đa-nang"``).

    The result contains only ``a-z 0-9`` and single hyphens, matching the
    Django ``slugify`` convention (lowercased, ASCII, hyphen-separated).
    """
    import re
    import unicodedata

    # 0. ``đ`` / ``Đ`` do not decompose under NFD — normalise them first.
    text = text.replace("đ", "d").replace("Đ", "D")

    # 1. NFD decomposition: à -> a + combining grave, ơ -> o + combining horn, …
    normalized = unicodedata.normalize("NFD", text)

    # 2. Drop every combining mark (Unicode general category M*).
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch)[0] != "M")

    # 3. Lowercase, then keep ASCII letters/digits only (anything else -> hyphen).
    slug = "".join(
        ch if ("a" <= ch <= "z" or "0" <= ch <= "9") else "-"
        for ch in stripped.lower()
    )

    # 4. Collapse runs of hyphens and trim the edges.
    slug = re.sub(r"-{2,}", "-", slug).strip("-")

    return slug or "chuo-khong-hop-le"