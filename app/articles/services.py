"""Services and database operations for Crawled Articles Management (Kho Bài Viết Thu Thập)."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository
from app.core.pagination import PaginationMeta
from app.articles.models import (
    ARTICLE_STATUS_METADATA,
    SENTIMENT_METADATA,
    CrawledArticleModel,
)
from app.sources.models import SOURCE_TYPE_METADATA

logger = logging.getLogger(__name__)

COLLECTION_NAME = "crawled_articles"

# Rich default seed dataset of crawled articles representing various sources and platforms
DEFAULT_ARTICLES: List[Dict[str, Any]] = []


class ArticleRepository(BaseMongoRepository):
    """Repository handling CRUD operations for crawled articles."""

    def __init__(self) -> None:
        super().__init__(collection_name=COLLECTION_NAME, id_field="id")


_repo = ArticleRepository()


async def init_articles_collection(db: Optional[Any] = None) -> None:
    """Ensure indexes for crawled_articles collection (no auto-seeding on page load)."""
    col = _repo.get_collection(db)
    if col is not None:
        try:
            await _repo.ensure_indexes([
                ("id", True),
                "url",
                "source_type",
                "category",
                "location",
                "sentiment",
                "status",
                "has_ai_idea",
                "target_product_id",
            ], db)
        except Exception as exc:
            logger.warning(f"Failed to ensure indexes for crawled_articles: {exc}")


def format_article_display(article: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich article dictionary with visual badges, icons, and sentiment colors."""
    a = dict(article)
    sent_key = a.get("sentiment", "Tích cực")
    st_meta = SENTIMENT_METADATA.get(sent_key, SENTIMENT_METADATA["Tích cực"])

    status_key = a.get("status", "new")
    status_meta = ARTICLE_STATUS_METADATA.get(status_key, ARTICLE_STATUS_METADATA["new"])

    src_type = a.get("source_type", "website")
    src_meta = SOURCE_TYPE_METADATA.get(src_type, SOURCE_TYPE_METADATA["website"])

    a["sentiment_badge"] = st_meta.get("badge_color", "bg-slate-100 text-slate-700")
    a["sentiment_dot"] = st_meta.get("dot_color", "bg-slate-400")
    a["status_label"] = status_meta.get("label", status_key.title())
    a["status_badge_color"] = status_meta.get("badge_color", "bg-slate-100 text-slate-700")
    a["source_type_label"] = src_meta.get("label", src_type.title())
    a["source_type_badge"] = src_meta.get("badge_color", "bg-slate-100 text-slate-700")
    a["source_icon"] = a.get("source_icon") or src_meta.get("icon", "globe")

    # Tags list
    if isinstance(a.get("tags"), str):
        raw_tags = a["tags"].replace(";", ",").split(",")
        a["tags"] = [t.strip() for t in raw_tags if t.strip()]
    elif not a.get("tags"):
        a["tags"] = []

    return a


async def list_articles(
    db: Optional[Any] = None,
    search: str = "",
    category_filter: str = "all",
    location_filter: str = "all",
    source_type_filter: str = "all",
    sentiment_filter: str = "all",
    status_filter: str = "all",
    product_filter: str = "all",
    page: int = 1,
    page_size: int = 12,
    sort_by: str = "updated_at",
) -> Dict[str, Any]:
    """Retrieve filtered, paginated list of crawled articles (default order: updated_at desc)."""
    await init_articles_collection(db)

    query: Dict[str, Any] = {}

    if category_filter and category_filter != "all":
        query["category"] = category_filter

    if location_filter and location_filter != "all":
        query["location"] = location_filter

    if source_type_filter and source_type_filter != "all":
        query["source_type"] = source_type_filter

    if sentiment_filter and sentiment_filter != "all":
        query["sentiment"] = sentiment_filter

    if status_filter and status_filter != "all":
        if status_filter == "has_idea":
            query["has_ai_idea"] = True
        elif status_filter == "no_idea":
            query["has_ai_idea"] = False
        else:
            query["status"] = status_filter

    if product_filter and product_filter != "all":
        try:
            query["target_product_id"] = int(product_filter)
        except ValueError:
            pass

    clean_search = (search or "").strip()
    if clean_search:
        regex_pattern = {"$regex": re.escape(clean_search), "$options": "i"}
        query["$or"] = [
            {"title": regex_pattern},
            {"summary": regex_pattern},
            {"source": regex_pattern},
            {"location": regex_pattern},
            {"category": regex_pattern},
            {"tags": regex_pattern},
        ]

    # Sort logic: default updated_at desc
    sort_field = "updated_at"
    sort_dir = -1
    if sort_by == "viral":
        sort_field = "viral_potential"
        sort_dir = -1
    elif sort_by == "title":
        sort_field = "title"
        sort_dir = 1
    elif sort_by == "created_at":
        sort_field = "created_at"
        sort_dir = -1
    elif sort_by == "id":
        sort_field = "id"
        sort_dir = -1
    else:  # "updated_at", "newest", or default
        sort_field = "updated_at"
        sort_dir = -1

    page = max(1, page)
    page_size = max(1, min(100, page_size))

    items, pagination, is_connected = await _repo.find_paginated(
        query=query,
        sort_field=sort_field,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
        db=db,
    )

    enriched_items = [format_article_display(item) for item in items]
    stats = await get_articles_kpis(db)

    return {
        "items": enriched_items,
        "total": pagination.total_items,
        "pagination": pagination,
        "stats": stats,
        "db_connected": is_connected,
    }


async def get_articles_kpis(db: Optional[Any] = None) -> Dict[str, Any]:
    """Calculate KPI metrics for crawled articles."""
    all_articles, _ = await _repo.find_all(db=db)

    total = len(all_articles)
    crawled_today = total  # Default/demo value
    has_idea_count = sum(1 for a in all_articles if a.get("has_ai_idea") is True)
    high_viral_count = sum(1 for a in all_articles if int(a.get("viral_potential", 0)) >= 85)

    # Categories breakdown
    categories: Dict[str, int] = {}
    for a in all_articles:
        cat = a.get("category", "Tổng hợp")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_articles": total,
        "crawled_today": crawled_today,
        "has_idea_count": has_idea_count,
        "high_viral_count": high_viral_count,
        "categories": categories,
    }


async def get_article_by_id(article_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieve single article by integer ID."""
    doc = await _repo.find_by_id(article_id, db=db)
    if doc:
        return format_article_display(doc)
    return None


async def create_article(data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Create a new crawled article document."""
    await init_articles_collection(db)

    highest_id = await _repo.get_next_id(db=db)

    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
    elif not isinstance(tags, list):
        tags = []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    viral_score = 80
    if data.get("viral_potential") is not None:
        try:
            viral_score = int(data["viral_potential"])
        except (ValueError, TypeError):
            pass

    target_prod_id = None
    if data.get("target_product_id") is not None and str(data["target_product_id"]).strip():
        try:
            target_prod_id = int(data["target_product_id"])
        except (ValueError, TypeError):
            pass

    doc = {
        "id": highest_id,
        "title": (data.get("title") or "").strip(),
        "summary": (data.get("summary") or "").strip(),
        "content": (data.get("content") or "").strip(),
        "url": (data.get("url") or "").strip(),
        "source": (data.get("source") or "Website").strip(),
        "source_id": data.get("source_id"),
        "source_type": (data.get("source_type") or "website").strip().lower(),
        "source_icon": data.get("source_icon") or "globe",
        "author": (data.get("author") or "").strip(),
        "location": (data.get("location") or "Toàn quốc").strip(),
        "category": (data.get("category") or "Tổng hợp").strip(),
        "tags": tags,
        "sentiment": (data.get("sentiment") or "Tích cực").strip(),
        "viral_potential": viral_score,
        "has_ai_idea": bool(data.get("has_ai_idea", False)),
        "target_product_id": target_prod_id,
        "target_product_name": data.get("target_product_name"),
        "status": data.get("status") or "new",
        "crawled_at": "Vừa xong",
        "created_at": now_str,
        "updated_at": now_str,
    }

    inserted = await _repo.insert(doc, auto_id=False, db=db)
    return format_article_display(inserted)


async def update_article(article_id: int, data: Dict[str, Any], db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Update fields of an existing crawled article."""
    current = await _repo.find_by_id(article_id, db=db)
    if not current:
        return None

    update_payload: Dict[str, Any] = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    allowed_fields = [
        "title", "summary", "content", "url", "source", "source_type",
        "location", "category", "sentiment", "viral_potential",
        "has_ai_idea", "target_product_id", "target_product_name", "status",
    ]

    for field in allowed_fields:
        if field in data and data[field] is not None:
            val = data[field]
            if isinstance(val, str):
                val = val.strip()
            if field == "viral_potential":
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    val = current.get("viral_potential", 80)
            if field == "target_product_id":
                try:
                    val = int(val) if val else None
                except (ValueError, TypeError):
                    val = None
            update_payload[field] = val

    if "tags" in data and data["tags"] is not None:
        tags = data["tags"]
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
        elif not isinstance(tags, list):
            tags = []
        update_payload["tags"] = tags

    updated = await _repo.update(article_id, update_payload, db=db)
    if updated:
        return format_article_display(updated)
    return None


async def delete_article(article_id: int, db: Optional[Any] = None) -> bool:
    """Delete an article by integer ID."""
    return await _repo.delete(article_id, db=db)


async def assign_product_to_article(
    article_id: int,
    product_id: int,
    product_name: str,
    db: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Assign article to a target product / publishing channel."""
    return await update_article(
        article_id=article_id,
        data={
            "target_product_id": product_id,
            "target_product_name": product_name,
        },
        db=db,
    )


async def mark_as_has_idea(article_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Mark article as having generated AI ideas."""
    return await update_article(
        article_id=article_id,
        data={
            "has_ai_idea": True,
            "status": "has_idea",
        },
        db=db,
    )


async def reset_demo_articles(db: Optional[Any] = None) -> int:
    """Reset crawled articles collection to default rich seed data."""
    await init_articles_collection(db)
    all_current, _ = await _repo.find_all(db=db)
    for a in all_current:
        await _repo.delete(a["id"], db=db)
    for item in DEFAULT_ARTICLES:
        await _repo.insert(dict(item), auto_id=False, db=db)
    return len(DEFAULT_ARTICLES)


async def get_categories_dropdown(db: Optional[Any] = None) -> List[str]:
    """Retrieve distinct list of categories from articles in DB."""
    all_art, _ = await _repo.find_all(db=db)
    cats = {a.get("category", "Tổng hợp") for a in all_art if a.get("category")}
    return sorted(list(cats))


async def get_locations_dropdown(db: Optional[Any] = None) -> List[str]:
    """Retrieve distinct list of locations/provinces from articles in DB."""
    all_art, _ = await _repo.find_all(db=db)
    locs = {a.get("location", "Toàn quốc") for a in all_art if a.get("location")}
    return sorted(list(locs))
