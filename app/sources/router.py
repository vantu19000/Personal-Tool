"""FastAPI Router for Crawler Source Management (Quản lý Nguồn dữ liệu)."""
from __future__ import annotations

import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.database import get_db
from app.core.templates import templates
from app.sources import services
from app.sources.models import (
    PRIORITY_METADATA,
    SCHEDULE_OPTIONS,
    SOURCE_TYPE_METADATA,
    STATUS_METADATA,
    SourceCreatePayload,
    SourceUpdatePayload,
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


@router.get("/crawler/sources", name="crawler-sources-main")
@router.get("/sources", name="crawler-sources-short")
async def sources_page(
    request: Request,
    search: str = "",
    type: str = "all",
    priority: str = "all",
    status: str = "all",
    province: str = "all",
    page: int = 1,
    page_size: int = 15,
    sort_by: str = "updated_at",
    db: Any = Depends(get_db),
):
    """Render the comprehensive Source Management screen."""
    data = await services.list_sources(
        db=db,
        search=search,
        type_filter=type,
        priority_filter=priority,
        status_filter=status,
        province_filter=province,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )

    provinces_dropdown = services.get_provinces_dropdown()

    return templates.TemplateResponse(
        request,
        "tools/content_ideas/sources.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "sources",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "sources": data["items"],
            "total_count": data["total"],
            "pagination": data.get("pagination"),
            "stats": data["stats"],
            "db_connected": data["db_connected"],
            "search": search,
            "type_filter": type,
            "priority_filter": priority,
            "status_filter": status,
            "province_filter": province,
            "sort_by": sort_by,
            "source_types": SOURCE_TYPE_METADATA,
            "priorities": PRIORITY_METADATA,
            "statuses": STATUS_METADATA,
            "schedules": SCHEDULE_OPTIONS,
            "provinces": provinces_dropdown,
        },
    )


# ============================================================================
# API Endpoints (CRUD, Toggle, Instant Scan, Reset Demo)
# ============================================================================

@router.get("/api/sources", name="api-list-sources")
async def api_list_sources(
    search: str = "",
    type: str = "all",
    priority: str = "all",
    status: str = "all",
    province: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "updated_at",
    db: Any = Depends(get_db),
):
    """Return JSON list of crawler sources."""
    data = await services.list_sources(
        db=db,
        search=search,
        type_filter=type,
        priority_filter=priority,
        status_filter=status,
        province_filter=province,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    if "pagination" in data and hasattr(data["pagination"], "to_dict"):
        data["pagination"] = data["pagination"].to_dict()
    return JSONResponse(data)


@router.get("/api/sources/{source_id}", name="api-get-source")
async def api_get_source(source_id: int, db: Any = Depends(get_db)):
    """Retrieve details for a single source by ID."""
    source = await services.get_source_by_id(source_id, db=db)
    if not source:
        return JSONResponse({"ok": False, "error": f"Nguồn ID {source_id} không tồn tại"}, status_code=404)
    return JSONResponse({"ok": True, "source": source})


@router.post("/api/sources", name="api-create-source")
async def api_create_source(
    request: Request,
    name: str = Form(...),
    type: str = Form("website"),
    url: str = Form(...),
    province: Optional[str] = Form("Toàn quốc"),
    district: Optional[str] = Form(""),
    ward: Optional[str] = Form(""),
    tags: Optional[str] = Form(""),
    schedule: Optional[str] = Form("1_hour"),
    priority: Optional[str] = Form("medium"),
    status: Optional[str] = Form("active"),
    ai_prompt: Optional[str] = Form(""),
    description: Optional[str] = Form(""),
    db: Any = Depends(get_db),
):
    """Create a new crawler source."""
    try:
        new_source = await services.create_source(
            {
                "name": name,
                "type": type,
                "url": url,
                "province": province,
                "district": district,
                "ward": ward,
                "tags": tags,
                "schedule": schedule,
                "priority": priority,
                "status": status,
                "ai_prompt": ai_prompt,
                "description": description,
            },
            db=db,
        )
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "source": new_source})
        return RedirectResponse(url="/tools/content-ideas/sources", status_code=303)
    except Exception as exc:
        logger.error(f"Error creating source: {exc}", exc_info=True)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/sources/{source_id}/edit", name="api-update-source")
async def api_update_source(
    source_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    province: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    ward: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    schedule: Optional[str] = Form(None),
    priority: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    ai_prompt: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Update an existing source."""
    update_data: dict = {}
    if name is not None:
        update_data["name"] = name
    if type is not None:
        update_data["type"] = type
    if url is not None:
        update_data["url"] = url
    if province is not None:
        update_data["province"] = province
    if district is not None:
        update_data["district"] = district
    if ward is not None:
        update_data["ward"] = ward
    if tags is not None:
        update_data["tags"] = tags
    if schedule is not None:
        update_data["schedule"] = schedule
    if priority is not None:
        update_data["priority"] = priority
    if status is not None:
        update_data["status"] = status
    if ai_prompt is not None:
        update_data["ai_prompt"] = ai_prompt
    if description is not None:
        update_data["description"] = description

    try:
        updated = await services.update_source(source_id, update_data, db=db)
        if not updated:
            return JSONResponse({"ok": False, "error": f"Nguồn ID {source_id} không tồn tại"}, status_code=404)
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "source": updated})
        return RedirectResponse(url="/tools/content-ideas/sources", status_code=303)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/sources/{source_id}/delete", name="api-delete-source")
async def api_delete_source(
    source_id: int,
    request: Request,
    db: Any = Depends(get_db),
):
    """Delete a crawler source."""
    success = await services.delete_source(source_id, db=db)
    if not success:
        return JSONResponse({"ok": False, "error": f"Không thể xóa nguồn ID {source_id}"}, status_code=404)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": True, "id": source_id})
    return RedirectResponse(url="/tools/content-ideas/sources", status_code=303)


@router.post("/api/sources/{source_id}/toggle-status", name="api-toggle-source-status")
async def api_toggle_status(source_id: int, db: Any = Depends(get_db)):
    """Toggle source active / paused state."""
    updated = await services.toggle_status(source_id, db=db)
    if not updated:
        return JSONResponse({"ok": False, "error": "Nguồn không tồn tại"}, status_code=404)
    return JSONResponse({"ok": True, "source": updated})


@router.post("/api/sources/{source_id}/scan", name="api-scan-source")
async def api_scan_source(source_id: int, db: Any = Depends(get_db)):
    """Trigger an instant crawl on this source, deduplicate, and persist to crawled_articles."""
    from app.sources.crawler import crawl_source_and_save
    result = await crawl_source_and_save(source_id, db=db)
    if not result.get("ok"):
        return JSONResponse({"ok": False, "error": result.get("error", "Nguồn không tồn tại")}, status_code=404)

    updated_source = await services.get_source_by_id(source_id, db=db)
    return JSONResponse({
        "ok": True,
        "source": updated_source,
        "scanned_count": result.get("scanned_count", 0),
        "new_count": result.get("new_count", 0),
        "duplicate_count": result.get("duplicate_count", 0),
        "message": result.get("message"),
    })


@router.post("/api/sources/scan-all", name="api-scan-all-sources")
async def api_scan_all_sources(db: Any = Depends(get_db)):
    """Trigger crawl on all active sources, deduplicate, and persist to crawled_articles."""
    from app.sources.crawler import crawl_all_active_sources
    result = await crawl_all_active_sources(db=db)
    return JSONResponse(result)


@router.post("/api/sources/reset-demo", name="api-reset-demo-sources")
async def api_reset_demo(db: Any = Depends(get_db)):
    """Reset sources collection to the 9 default seed sources."""
    count = await services.reset_demo_sources(db=db)
    return JSONResponse({"ok": True, "count": count, "message": f"Đã khôi phục thành công {count} nguồn mẫu đầy đủ 9 định dạng!"})
