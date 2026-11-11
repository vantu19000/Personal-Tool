"""FastAPI Router for AI Ideas Management (Kho Ý Tưởng AI từ Database)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.database import get_mongo_database
from app.core.templates import templates
from app.ideas import services
from app.ideas.models import IDEA_STATUS_METADATA, RECOMMENDED_FORMATS
from app.products import services as product_services
from app.articles import services as article_services

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    return get_mongo_database()


# Menus of AI Content Ideas suite
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
        "badge": "Database",
        "badge_color": "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300",
    },
    {
        "id": "ideas",
        "title": "Ý tưởng AI",
        "icon": "sparkles",
        "path": "/tools/content-ideas/ideas",
        "badge": "Database",
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
    },
    {
        "id": "settings",
        "title": "Cấu hình Quét & AI",
        "icon": "settings",
        "path": "/tools/content-ideas/settings",
    },
]


# ==============================================================================
# WEB PAGES
# ==============================================================================

@router.get("/ideas", response_class=HTMLResponse, name="ideas-page")
@router.get("/tools/content-ideas/ideas", response_class=HTMLResponse, name="content-ideas-ideas-page")
async def ideas_page(
    request: Request,
    search: str = "",
    status: str = "all",
    format: str = "all",
    product: str = "all",
    view_mode: str = "grid",
    page: int = 1,
    page_size: int = 6,
    sort_by: str = "newest",
    db: Any = Depends(get_db),
):
    """Render the AI Content Ideas screen backed by database with full filters and pagination."""
    data = await services.list_ideas(
        db=db,
        search=search,
        status_filter=status,
        format_filter=format,
        product_filter=product,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )

    # Fetch user products and articles for dropdown selections
    products_data = await product_services.list_products(db=db, page_size=100)
    products_list = products_data.get("items", [])

    articles_data = await article_services.list_articles(db=db, page_size=50)
    articles_list = articles_data.get("items", [])

    return templates.TemplateResponse(
        request,
        "tools/content_ideas/ideas.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "ideas",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "ideas": data["items"],
            "total_count": data["total"],
            "pagination": data.get("pagination"),
            "stats": data["stats"],
            "db_connected": data["db_connected"],
            "search": search,
            "status_filter": status,
            "format_filter": format,
            "product_filter": product,
            "view_mode": view_mode,
            "sort_by": sort_by,
            "products_list": products_list,
            "articles_list": articles_list,
            "formats_list": RECOMMENDED_FORMATS,
            "status_metadata": IDEA_STATUS_METADATA,
        },
    )


# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================

@router.get("/api/ideas", tags=["ai-ideas"])
async def api_list_ideas(
    search: str = "",
    status: str = "all",
    format: str = "all",
    product: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "newest",
    db: Any = Depends(get_db),
):
    """Return JSON list of AI ideas matching filters and pagination."""
    return await services.list_ideas(
        db=db,
        search=search,
        status_filter=status,
        format_filter=format,
        product_filter=product,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )


@router.get("/api/ideas/kpis", tags=["ai-ideas"])
async def api_ideas_kpis(db: Any = Depends(get_db)):
    """Return KPI statistics for AI ideas."""
    return await services.get_ideas_kpis(db=db)


@router.get("/api/ideas/{idea_id}", tags=["ai-ideas"])
async def api_get_idea(idea_id: int, db: Any = Depends(get_db)):
    """Return single AI idea JSON."""
    idea = await services.get_idea_by_id(idea_id, db=db)
    if not idea:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại.")
    return {"ok": True, "idea": idea}


@router.post("/api/ideas", tags=["ai-ideas"])
async def api_create_idea(
    request: Request,
    title: str = Form(...),
    angle: str = Form(""),
    target_audience: str = Form(""),
    recommended_format: str = Form("Bài viết dài (Blog / Website)"),
    viral_score: int = Form(85),
    status: str = Form("ready"),
    keywords: str = Form(""),
    outline: str = Form(""),
    source_article_id: Optional[str] = Form(None),
    source_article: str = Form(""),
    target_product_id: Optional[str] = Form(None),
    target_product_name: str = Form(""),
    target_platform: str = Form(""),
    ai_prompt_used: str = Form(""),
    notes: str = Form(""),
    db: Any = Depends(get_db),
    accept: Optional[str] = Header(None),
):
    """Create a new AI Idea via Form or JSON."""
    idea_data = {
        "title": title,
        "angle": angle,
        "target_audience": target_audience,
        "recommended_format": recommended_format,
        "viral_score": viral_score,
        "status": status,
        "keywords": keywords,
        "outline": outline,
        "source_article_id": int(source_article_id) if source_article_id and source_article_id.strip().isdigit() else None,
        "source_article": source_article,
        "target_product_id": int(target_product_id) if target_product_id and target_product_id.strip().isdigit() else None,
        "target_product_name": target_product_name,
        "target_platform": target_platform,
        "ai_prompt_used": ai_prompt_used,
        "notes": notes,
    }

    created = await services.create_idea(idea_data, db=db)

    if accept and "application/json" in accept:
        return JSONResponse({"ok": True, "idea": created})

    return RedirectResponse(url="/tools/content-ideas/ideas", status_code=303)


@router.post("/api/ideas/{idea_id}/edit", tags=["ai-ideas"])
async def api_edit_idea(
    idea_id: int,
    request: Request,
    title: Optional[str] = Form(None),
    angle: Optional[str] = Form(None),
    target_audience: Optional[str] = Form(None),
    recommended_format: Optional[str] = Form(None),
    viral_score: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    outline: Optional[str] = Form(None),
    source_article_id: Optional[str] = Form(None),
    source_article: Optional[str] = Form(None),
    target_product_id: Optional[str] = Form(None),
    target_product_name: Optional[str] = Form(None),
    target_platform: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Any = Depends(get_db),
    accept: Optional[str] = Header(None),
):
    """Edit fields of an existing AI Idea."""
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if angle is not None:
        update_data["angle"] = angle
    if target_audience is not None:
        update_data["target_audience"] = target_audience
    if recommended_format is not None:
        update_data["recommended_format"] = recommended_format
    if viral_score is not None:
        update_data["viral_score"] = viral_score
    if status is not None:
        update_data["status"] = status
    if keywords is not None:
        update_data["keywords"] = keywords
    if outline is not None:
        update_data["outline"] = outline
    if source_article_id is not None:
        update_data["source_article_id"] = int(source_article_id) if source_article_id.strip().isdigit() else None
    if source_article is not None:
        update_data["source_article"] = source_article
    if target_product_id is not None:
        update_data["target_product_id"] = int(target_product_id) if target_product_id.strip().isdigit() else None
    if target_product_name is not None:
        update_data["target_product_name"] = target_product_name
    if target_platform is not None:
        update_data["target_platform"] = target_platform
    if notes is not None:
        update_data["notes"] = notes

    updated = await services.update_idea(idea_id, update_data, db=db)
    if not updated:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại.")

    if accept and "application/json" in accept:
        return JSONResponse({"ok": True, "idea": updated})

    return RedirectResponse(url="/tools/content-ideas/ideas", status_code=303)


@router.post("/api/ideas/{idea_id}/status", tags=["ai-ideas"])
async def api_update_idea_status(
    idea_id: int,
    status: str = Form(...),
    db: Any = Depends(get_db),
):
    """Update workflow status of an AI idea (ready, drafting, reviewing, published, archived)."""
    updated = await services.update_idea_status(idea_id, status, db=db)
    if not updated:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại.")
    return {"ok": True, "status": updated["status"], "status_label": updated["status_label"]}


@router.post("/api/ideas/{idea_id}/assign-product", tags=["ai-ideas"])
async def api_assign_product(
    idea_id: int,
    product_id: int = Form(...),
    product_name: str = Form(...),
    platform: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Assign target product/channel to an AI idea."""
    assigned = await services.assign_product_to_idea(
        idea_id=idea_id,
        product_id=product_id,
        product_name=product_name,
        platform=platform,
        db=db,
    )
    if not assigned:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại.")
    return {"ok": True, "idea": assigned}


@router.post("/api/ideas/{idea_id}/delete", tags=["ai-ideas"])
async def api_delete_idea(
    idea_id: int,
    db: Any = Depends(get_db),
    accept: Optional[str] = Header(None),
):
    """Delete an AI Idea."""
    success = await services.delete_idea(idea_id, db=db)
    if not success:
        raise HTTPException(status_code=404, detail="Ý tưởng không tồn tại.")

    if accept and "application/json" in accept:
        return JSONResponse({"ok": True, "deleted_id": idea_id})

    return RedirectResponse(url="/tools/content-ideas/ideas", status_code=303)


@router.post("/api/ideas/generate-from-article/{article_id}", tags=["ai-ideas"])
async def api_generate_from_article(article_id: int, db: Any = Depends(get_db)):
    """Generate an AI idea automatically from a crawled article."""
    art = await article_services.get_article_by_id(article_id, db=db)
    if not art:
        raise HTTPException(status_code=404, detail="Bài viết thu thập không tồn tại.")

    new_idea = await services.generate_idea_from_article(art, db=db)
    # Also mark article as has_idea
    await article_services.mark_as_has_idea(article_id, db=db)
    return {"ok": True, "idea": new_idea}


@router.post("/api/ideas/reset-demo", tags=["ai-ideas"])
async def api_reset_demo_ideas(db: Any = Depends(get_db)):
    """Reset the collection back to DEFAULT_IDEAS."""
    count = await services.reset_demo_ideas(db=db)
    return {"ok": True, "count": count}
