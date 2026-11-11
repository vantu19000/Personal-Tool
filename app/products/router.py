"""FastAPI Router for My Products & Publishing Channels Management (Quản lý Sản phẩm / Kênh phân phối)."""
from __future__ import annotations

import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.database import get_db
from app.core.templates import templates
from app.products import services
from app.products.models import (
    PLATFORM_METADATA,
    PRODUCT_STATUS_METADATA,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Menus used when embedded in AI Content Scanner suite
CONTENT_IDEAS_MENUS = [
    {
        "id": "dashboard",
        "title": "Tổng quan",
        "icon": "layout-dashboard",
        "path": "/tools/content-ideas",
        "badge": "Realtime",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300",
    },
    {
        "id": "products",
        "title": "Sản phẩm của tôi",
        "icon": "layers",
        "path": "/tools/content-ideas/products",
        "badge": "Output",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300",
    },
    {
        "id": "sources",
        "title": "Nguồn cào (Input)",
        "icon": "radio",
        "path": "/tools/content-ideas/sources",
        "badge": "9 loại",
        "badge_color": "bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300",
    },
    {
        "id": "articles",
        "title": "Bài thu thập",
        "icon": "newspaper",
        "path": "/tools/content-ideas/articles",
    },
    {
        "id": "ideas",
        "title": "Ý tưởng AI",
        "icon": "sparkles",
        "path": "/tools/content-ideas/ideas",
        "badge": "Hot",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300",
    },
    {
        "id": "published",
        "title": "Bài đã xuất bản",
        "icon": "check-circle-2",
        "path": "/tools/content-ideas/published",
    },
    {
        "id": "trending",
        "title": "Trending & Radar",
        "icon": "flame",
        "path": "/tools/content-ideas/trending",
        "badge": "Spike",
        "badge_color": "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300",
    },
    {
        "id": "settings",
        "title": "Cấu hình quét",
        "icon": "sliders-horizontal",
        "path": "/tools/content-ideas/settings",
    },
]


@router.get("/products", name="products-main")
@router.get("/channels", name="channels-alias")
async def products_page(
    request: Request,
    search: str = "",
    platform: str = "all",
    status: str = "all",
    niche: str = "all",
    page: int = 1,
    page_size: int = 15,
    sort_by: str = "updated_at",
    db: Any = Depends(get_db),
):
    """Render the My Products / Channels Management screen."""
    data = await services.list_products(
        db=db,
        search=search,
        platform_filter=platform,
        status_filter=status,
        niche_filter=niche,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )

    niches = await services.get_niches_dropdown(db=db)

    return templates.TemplateResponse(
        request,
        "tools/content_ideas/products.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "products",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "products": data["items"],
            "total_count": data["total"],
            "pagination": data.get("pagination"),
            "stats": data["stats"],
            "db_connected": data["db_connected"],
            "search": search,
            "platform_filter": platform,
            "status_filter": status,
            "niche_filter": niche,
            "sort_by": sort_by,
            "platforms": PLATFORM_METADATA,
            "statuses": PRODUCT_STATUS_METADATA,
            "niches": niches,
        },
    )


# ============================================================================
# API Endpoints (CRUD, Toggle Status, Reset Demo)
# ============================================================================

@router.get("/api/products", name="api-list-products")
async def api_list_products(
    search: str = "",
    platform: str = "all",
    status: str = "all",
    niche: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "updated_at",
    db: Any = Depends(get_db),
):
    """Return JSON list of user products / channels with pagination."""
    data = await services.list_products(
        db=db,
        search=search,
        platform_filter=platform,
        status_filter=status,
        niche_filter=niche,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    if "pagination" in data and hasattr(data["pagination"], "to_dict"):
        data["pagination"] = data["pagination"].to_dict()
    return JSONResponse(data)


@router.get("/api/products/{product_id}", name="api-get-product")
async def api_get_product(product_id: int, db: Any = Depends(get_db)):
    """Retrieve details for a single product by ID."""
    product = await services.get_product_by_id(product_id, db=db)
    if not product:
        return JSONResponse({"ok": False, "error": f"Sản phẩm ID {product_id} không tồn tại"}, status_code=404)
    return JSONResponse({"ok": True, "product": product})


@router.post("/api/products", name="api-create-product")
async def api_create_product(
    request: Request,
    name: str = Form(...),
    platform: str = Form("youtube"),
    code: Optional[str] = Form(""),
    url: Optional[str] = Form(""),
    niche: Optional[str] = Form("Chung"),
    target_audience: Optional[str] = Form(""),
    content_format: Optional[str] = Form(""),
    posting_frequency: Optional[str] = Form("Hàng tuần"),
    brand_voice: Optional[str] = Form(""),
    ai_system_prompt: Optional[str] = Form(""),
    tags: Optional[str] = Form(""),
    status: Optional[str] = Form("active"),
    followers_metric: Optional[str] = Form(""),
    description: Optional[str] = Form(""),
    db: Any = Depends(get_db),
):
    """Create a new product / publishing channel."""
    try:
        new_prod = await services.create_product(
            {
                "name": name,
                "platform": platform,
                "code": code,
                "url": url,
                "niche": niche,
                "target_audience": target_audience,
                "content_format": content_format,
                "posting_frequency": posting_frequency,
                "brand_voice": brand_voice,
                "ai_system_prompt": ai_system_prompt,
                "tags": tags,
                "status": status,
                "followers_metric": followers_metric,
                "description": description,
            },
            db=db,
        )
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "product": new_prod})
        return RedirectResponse(url="/products", status_code=303)
    except Exception as exc:
        logger.error(f"Error creating product: {exc}", exc_info=True)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/products/{product_id}/edit", name="api-update-product")
async def api_update_product(
    product_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    niche: Optional[str] = Form(None),
    target_audience: Optional[str] = Form(None),
    content_format: Optional[str] = Form(None),
    posting_frequency: Optional[str] = Form(None),
    brand_voice: Optional[str] = Form(None),
    ai_system_prompt: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    followers_metric: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Update an existing product / channel."""
    update_data: dict = {}
    fields = [
        ("name", name), ("platform", platform), ("code", code), ("url", url),
        ("niche", niche), ("target_audience", target_audience),
        ("content_format", content_format), ("posting_frequency", posting_frequency),
        ("brand_voice", brand_voice), ("ai_system_prompt", ai_system_prompt),
        ("tags", tags), ("status", status), ("followers_metric", followers_metric),
        ("description", description),
    ]
    for key, val in fields:
        if val is not None:
            update_data[key] = val

    try:
        updated = await services.update_product(product_id, update_data, db=db)
        if not updated:
            return JSONResponse({"ok": False, "error": f"Sản phẩm ID {product_id} không tồn tại"}, status_code=404)
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "product": updated})
        return RedirectResponse(url="/products", status_code=303)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/products/{product_id}/delete", name="api-delete-product")
async def api_delete_product(
    product_id: int,
    request: Request,
    db: Any = Depends(get_db),
):
    """Delete a product."""
    success = await services.delete_product(product_id, db=db)
    if not success:
        return JSONResponse({"ok": False, "error": f"Không thể xóa sản phẩm ID {product_id}"}, status_code=404)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": True, "id": product_id})
    return RedirectResponse(url="/products", status_code=303)


@router.post("/api/products/{product_id}/toggle-status", name="api-toggle-product-status")
async def api_toggle_status(product_id: int, db: Any = Depends(get_db)):
    """Toggle product status between 'active' and 'paused'."""
    updated = await services.toggle_product_status(product_id, db=db)
    if not updated:
        return JSONResponse({"ok": False, "error": "Sản phẩm không tồn tại"}, status_code=404)
    return JSONResponse({"ok": True, "product": updated})


@router.post("/api/products/reset-demo", name="api-reset-demo-products")
async def api_reset_demo(db: Any = Depends(get_db)):
    """Reset products collection to the default seed products."""
    count = await services.reset_demo_products(db=db)
    return JSONResponse({"ok": True, "count": count, "message": f"Đã khôi phục thành công {count} sản phẩm/kênh mẫu tiêu chuẩn!"})
