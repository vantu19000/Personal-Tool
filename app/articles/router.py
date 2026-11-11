"""FastAPI Router for Crawled Articles Management (Kho Bài Viết Thu Thập)."""
from __future__ import annotations

import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.database import get_db
from app.core.templates import templates
from app.articles import services
from app.articles.models import (
    ARTICLE_STATUS_METADATA,
    SENTIMENT_METADATA,
)
from app.products import services as product_services
from app.sources import services as source_services
from app.sources.models import SOURCE_TYPE_METADATA

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
        "badge": "Database",
        "badge_color": "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300",
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


@router.get("/articles", name="articles-main")
@router.get("/crawled-articles", name="crawled-articles-alias")
async def articles_page(
    request: Request,
    search: str = "",
    category: str = "all",
    location: str = "all",
    source_type: str = "all",
    sentiment: str = "all",
    status: str = "all",
    product: str = "all",
    view_mode: str = "grid",
    page: int = 1,
    page_size: int = 6,
    sort_by: str = "newest",
    db: Any = Depends(get_db),
):
    """Render the Crawled Articles Explorer screen backed by database."""
    data = await services.list_articles(
        db=db,
        search=search,
        category_filter=category,
        location_filter=location,
        source_type_filter=source_type,
        sentiment_filter=sentiment,
        status_filter=status,
        product_filter=product,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )

    categories = await services.get_categories_dropdown(db=db)
    locations = await services.get_locations_dropdown(db=db)

    # Fetch user products and crawler sources for filter and assignment dropdowns
    products_data = await product_services.list_products(db=db, page_size=100)
    products_list = products_data.get("items", [])

    sources_data = await source_services.list_sources(db=db, page_size=100)
    sources_list = sources_data.get("items", [])

    return templates.TemplateResponse(
        request,
        "tools/content_ideas/articles.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "articles",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "articles": data["items"],
            "total_count": data["total"],
            "pagination": data.get("pagination"),
            "stats": data["stats"],
            "db_connected": data["db_connected"],
            "search": search,
            "category_filter": category,
            "location_filter": location,
            "source_type_filter": source_type,
            "sentiment_filter": sentiment,
            "status_filter": status,
            "product_filter": product,
            "view_mode": view_mode,
            "sort_by": sort_by,
            "categories": categories,
            "locations": locations,
            "products_list": products_list,
            "sources_list": sources_list,
            "source_types": SOURCE_TYPE_METADATA,
            "sentiments": SENTIMENT_METADATA,
            "statuses": ARTICLE_STATUS_METADATA,
        },
    )


# ============================================================================
# API Endpoints (CRUD, Assign Product, Mark as Idea, Reset Demo)
# ============================================================================

@router.get("/api/articles", name="api-list-articles")
async def api_list_articles(
    search: str = "",
    category: str = "all",
    location: str = "all",
    source_type: str = "all",
    sentiment: str = "all",
    status: str = "all",
    product: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "newest",
    db: Any = Depends(get_db),
):
    """Return JSON list of crawled articles with pagination."""
    data = await services.list_articles(
        db=db,
        search=search,
        category_filter=category,
        location_filter=location,
        source_type_filter=source_type,
        sentiment_filter=sentiment,
        status_filter=status,
        product_filter=product,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    if "pagination" in data and hasattr(data["pagination"], "to_dict"):
        data["pagination"] = data["pagination"].to_dict()
    return JSONResponse(data)


@router.get("/api/articles/{article_id}", name="api-get-article")
async def api_get_article(article_id: int, db: Any = Depends(get_db)):
    """Retrieve details for a single crawled article."""
    art = await services.get_article_by_id(article_id, db=db)
    if not art:
        return JSONResponse({"ok": False, "error": f"Bài viết ID {article_id} không tồn tại"}, status_code=404)
    return JSONResponse({"ok": True, "article": art})


@router.post("/api/articles", name="api-create-article")
async def api_create_article(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    content: Optional[str] = Form(""),
    url: Optional[str] = Form(""),
    source: Optional[str] = Form("Website"),
    source_type: Optional[str] = Form("website"),
    location: Optional[str] = Form("Toàn quốc"),
    category: Optional[str] = Form("Tổng hợp"),
    tags: Optional[str] = Form(""),
    sentiment: Optional[str] = Form("Tích cực"),
    viral_potential: Optional[int] = Form(80),
    target_product_id: Optional[str] = Form(None),
    target_product_name: Optional[str] = Form(None),
    status: Optional[str] = Form("new"),
    db: Any = Depends(get_db),
):
    """Manually add or crawl a new article into database."""
    try:
        new_art = await services.create_article(
            {
                "title": title,
                "summary": summary,
                "content": content,
                "url": url,
                "source": source,
                "source_type": source_type,
                "location": location,
                "category": category,
                "tags": tags,
                "sentiment": sentiment,
                "viral_potential": viral_potential,
                "target_product_id": target_product_id,
                "target_product_name": target_product_name,
                "status": status,
            },
            db=db,
        )
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "article": new_art})
        return RedirectResponse(url="/tools/content-ideas/articles", status_code=303)
    except Exception as exc:
        logger.error(f"Error creating article: {exc}", exc_info=True)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/articles/{article_id}/edit", name="api-update-article")
async def api_update_article(
    article_id: int,
    request: Request,
    title: Optional[str] = Form(None),
    summary: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    source_type: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    sentiment: Optional[str] = Form(None),
    viral_potential: Optional[int] = Form(None),
    target_product_id: Optional[str] = Form(None),
    target_product_name: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Update fields of an existing crawled article."""
    update_data: dict = {}
    fields = [
        ("title", title), ("summary", summary), ("content", content),
        ("url", url), ("source", source), ("source_type", source_type),
        ("location", location), ("category", category), ("tags", tags),
        ("sentiment", sentiment), ("viral_potential", viral_potential),
        ("target_product_id", target_product_id),
        ("target_product_name", target_product_name), ("status", status),
    ]
    for key, val in fields:
        if val is not None:
            update_data[key] = val

    try:
        updated = await services.update_article(article_id, update_data, db=db)
        if not updated:
            return JSONResponse({"ok": False, "error": f"Bài viết ID {article_id} không tồn tại"}, status_code=404)
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "article": updated})
        return RedirectResponse(url="/tools/content-ideas/articles", status_code=303)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/articles/{article_id}/delete", name="api-delete-article")
async def api_delete_article(
    article_id: int,
    request: Request,
    db: Any = Depends(get_db),
):
    """Delete an article from database."""
    success = await services.delete_article(article_id, db=db)
    if not success:
        return JSONResponse({"ok": False, "error": f"Không thể xóa bài viết ID {article_id}"}, status_code=404)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": True, "id": article_id})
    return RedirectResponse(url="/tools/content-ideas/articles", status_code=303)


@router.post("/api/articles/{article_id}/assign-product", name="api-assign-product-article")
async def api_assign_product(
    article_id: int,
    product_id: int = Form(...),
    product_name: str = Form(...),
    db: Any = Depends(get_db),
):
    """Assign article to a target product / channel."""
    updated = await services.assign_product_to_article(
        article_id=article_id,
        product_id=product_id,
        product_name=product_name,
        db=db,
    )
    if not updated:
        return JSONResponse({"ok": False, "error": "Bài viết không tồn tại"}, status_code=404)
    return JSONResponse({
        "ok": True,
        "article": updated,
        "message": f"Đã gán bài viết cho sản phẩm '{product_name}' thành công!",
    })


@router.post("/api/articles/{article_id}/generate-idea", name="api-generate-idea-from-article")
async def api_generate_idea(article_id: int, db: Any = Depends(get_db)):
    """Simulate triggering AI idea generation from this article and mark as processed."""
    updated = await services.mark_as_has_idea(article_id, db=db)
    if not updated:
        return JSONResponse({"ok": False, "error": "Bài viết không tồn tại"}, status_code=404)
    return JSONResponse({
        "ok": True,
        "article": updated,
        "message": f"AI đã trích xuất thành công 3 ý tưởng nội dung từ bài '{updated['title'][:35]}...'!",
    })


@router.post("/api/articles/reset-demo", name="api-reset-demo-articles")
async def api_reset_demo(db: Any = Depends(get_db)):
    """Reset crawled articles to the default seed dataset."""
    count = await services.reset_demo_articles(db=db)
    return JSONResponse({
        "ok": True,
        "count": count,
        "message": f"Đã khôi phục thành công {count} bài viết thu thập mẫu từ Database!",
    })
