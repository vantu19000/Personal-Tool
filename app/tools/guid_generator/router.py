"""Router for the GUID Generator tool.

GET  /tools/guid-generator          — form page (quantity input, default 1, max 100)
POST /tools/guid-generator/generate — generate N random GUID (v4) strings
"""
import uuid

from fastapi import APIRouter, Form, Request

from app.core.templates import templates

router = APIRouter()

MAX_QUANTITY = 100
DEFAULT_QUANTITY = 1


@router.get("/guid-generator", name="guid-generator")
async def guid_generator(request: Request):
    return templates.TemplateResponse(
        request,
        "tools/guid_generator.html",
        {
            "active_tool": "guid-generator",
            "max_quantity": MAX_QUANTITY,
            "default_quantity": DEFAULT_QUANTITY,
        },
    )


@router.post("/guid-generator/generate", name="guid-generator-generate")
async def generate_guids(
    quantity: int = Form(DEFAULT_QUANTITY, ge=1, le=MAX_QUANTITY, description="Số lượng chuỗi GUID cần tạo (1..100)"),
):
    """Generate *quantity* random GUID (v4) strings.

    Quantity is clamped to ``1..100`` (default 1).
    """
    guids = [str(uuid.uuid4()) for _ in range(quantity)]
    return {"ok": True, "guids": guids, "count": len(guids)}