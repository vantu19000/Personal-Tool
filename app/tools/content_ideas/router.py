"""Router for the AI Content Ideas tool suite.

Endpoints:
- GET  /content-ideas                -> Dashboard (Tổng quan)
- GET  /content-ideas/dashboard      -> Dashboard (Tổng quan)
- GET  /content-ideas/sources        -> Nguồn theo dõi (Sources)
- GET  /content-ideas/articles       -> Bài thu thập (Crawled Articles)
- GET  /content-ideas/ideas          -> Ý tưởng AI (AI Ideas)
- GET  /content-ideas/published      -> Bài đã xuất bản (Published Posts)
- GET  /content-ideas/trending       -> Trending & Xu hướng (Trending Radar)
- GET  /content-ideas/settings       -> Cấu hình Quét & AI (Settings)
- POST /content-ideas/api/scan       -> API Kích hoạt quét tức thì
- POST /content-ideas/api/generate   -> API Sinh ý tưởng từ bài viết
"""
import time
from typing import Optional
from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse

from app.core.templates import templates
from app.tools.content_ideas.mock_data import (
    AI_IDEAS_LIST,
    MONITORED_SOURCES,
    OVERVIEW_METRICS,
    PUBLISHED_POSTS,
    RECENT_ARTICLES,
    TOP_LOCATIONS,
    TOP_TOPICS,
    TRENDING_ITEMS,
)

router = APIRouter()


# Define the navigation tabs of AI Content Ideas suite
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
        "id": "sources",
        "title": "Nguồn theo dõi",
        "icon": "radio",
        "path": "/tools/content-ideas/sources",
        "count": len(MONITORED_SOURCES),
    },
    {
        "id": "articles",
        "title": "Bài thu thập",
        "icon": "newspaper",
        "path": "/tools/content-ideas/articles",
        "count": OVERVIEW_METRICS["articles_crawled_today"],
    },
    {
        "id": "ideas",
        "title": "Ý tưởng AI",
        "icon": "sparkles",
        "path": "/tools/content-ideas/ideas",
        "count": OVERVIEW_METRICS["ai_ideas_count"],
        "badge": "Hot",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300",
    },
    {
        "id": "published",
        "title": "Bài đã xuất bản",
        "icon": "check-circle-2",
        "path": "/tools/content-ideas/published",
        "count": OVERVIEW_METRICS["published_articles_count"],
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


@router.get("/content-ideas", name="content-ideas-home")
@router.get("/content-ideas/dashboard", name="content-ideas-dashboard")
async def content_ideas_dashboard(request: Request):
    """Main Dashboard for AI Content Ideas."""
    return templates.TemplateResponse(
        request,
        "tools/content_ideas/dashboard.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "dashboard",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "metrics": OVERVIEW_METRICS,
            "top_locations": TOP_LOCATIONS,
            "top_topics": TOP_TOPICS,
            "trending_items": TRENDING_ITEMS,
            "recent_articles": RECENT_ARTICLES,
            "recent_sources": MONITORED_SOURCES,
            "recent_ideas": AI_IDEAS_LIST,
        },
    )


@router.get("/content-ideas/sources", name="content-ideas-sources")
async def content_ideas_sources(
    request: Request,
    search: str = "",
    type: str = "all",
    priority: str = "all",
    status: str = "all",
    province: str = "all",
    page: int = 1,
    page_size: int = 15,
    sort_by: str = "priority",
):
    """Monitored Sources management screen."""
    from app.core.database import get_mongo_database
    from app.sources.router import sources_page
    return await sources_page(
        request=request,
        search=search,
        type=type,
        priority=priority,
        status=status,
        province=province,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        db=get_mongo_database(),
    )


@router.get("/content-ideas/articles", name="content-ideas-articles")
async def content_ideas_articles(request: Request):
    """Crawled Articles feed and explorer."""
    return templates.TemplateResponse(
        request,
        "tools/content_ideas/articles.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "articles",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "articles": RECENT_ARTICLES,
            "metrics": OVERVIEW_METRICS,
        },
    )


@router.get("/content-ideas/ideas", name="content-ideas-ideas")
async def content_ideas_ideas(request: Request):
    """AI Generated Content Ideas list."""
    return templates.TemplateResponse(
        request,
        "tools/content_ideas/ideas.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "ideas",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "ideas": AI_IDEAS_LIST,
            "metrics": OVERVIEW_METRICS,
        },
    )


@router.get("/content-ideas/published", name="content-ideas-published")
async def content_ideas_published(request: Request):
    """Published articles and posts tracking."""
    return templates.TemplateResponse(
        request,
        "tools/content_ideas/published.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "published",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "posts": PUBLISHED_POSTS,
            "metrics": OVERVIEW_METRICS,
        },
    )


@router.get("/content-ideas/trending", name="content-ideas-trending")
async def content_ideas_trending(request: Request):
    """Trending topics and radar explorer."""
    return templates.TemplateResponse(
        request,
        "tools/content_ideas/trending.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "trending",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "trending_items": TRENDING_ITEMS,
            "top_topics": TOP_TOPICS,
            "top_locations": TOP_LOCATIONS,
        },
    )


@router.get("/content-ideas/settings", name="content-ideas-settings")
async def content_ideas_settings(request: Request):
    """Crawler and AI settings."""
    return templates.TemplateResponse(
        request,
        "tools/content_ideas/settings.html",
        {
            "active_tool": "content-ideas",
            "active_sub_menu": "settings",
            "sub_menus": CONTENT_IDEAS_MENUS,
            "metrics": OVERVIEW_METRICS,
        },
    )


# Interactive API Endpoints for dynamic frontend UX
@router.post("/content-ideas/api/scan", name="content-ideas-api-scan")
async def trigger_instant_scan():
    """Trigger an instant scan across all active sources."""
    # Simulate scanning process
    time.sleep(0.4)
    return JSONResponse(
        {
            "ok": True,
            "message": "Quét thành công! Thu thập thêm 18 bài viết mới từ 44 nguồn.",
            "crawled_new": 18,
            "active_sources": 44,
            "timestamp": "Vừa xong",
        }
    )


@router.post("/content-ideas/api/generate-idea", name="content-ideas-api-generate")
async def generate_idea_on_demand(
    article_title: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
):
    """Generate an AI angle and content idea on demand."""
    time.sleep(0.3)
    generated = {
        "id": f"idea-dynamic-{int(time.time())}",
        "title": f"Góc nhìn mới: Cách ứng dụng thực tiễn về {topic or article_title or 'chủ đề mới'}",
        "angle": "Phân tích số liệu và giải pháp hành động cho độc giả trẻ",
        "viral_score": 93,
        "format": "Bài viết dài (Blog) + 1 Video ngắn 60s",
        "status": "ready",
    }
    return JSONResponse(
        {
            "ok": True,
            "message": "Đã tạo ý tưởng AI mới thành công!",
            "idea": generated,
        }
    )
