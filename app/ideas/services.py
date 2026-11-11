"""Services and database operations for AI Ideas Management (Kho Ý Tưởng AI)."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository
from app.core.pagination import PaginationMeta
from app.ideas.models import (
    IDEA_STATUS_METADATA,
    RECOMMENDED_FORMATS,
    AIIdeaModel,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ai_ideas"

# Rich default seed dataset for AI Ideas
DEFAULT_IDEAS: List[Dict[str, Any]] = []

# Singleton repository instance
_repo = BaseMongoRepository(COLLECTION_NAME, id_field="id")


def format_idea_display(item: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich an AI Idea document with display badges, formats, and tags."""
    doc = dict(item)

    status_key = doc.get("status", "ready")
    status_meta = IDEA_STATUS_METADATA.get(
        status_key,
        {
            "label": "Sẵn sàng",
            "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
            "dot_color": "bg-slate-400",
        },
    )
    doc["status_label"] = status_meta["label"]
    doc["status_color"] = status_meta["badge_color"]
    doc["status_badge"] = status_meta["badge_color"]
    doc["dot_color"] = status_meta.get("dot_color", "bg-emerald-500")

    # Keywords array check
    kw = doc.get("keywords", [])
    if isinstance(kw, str):
        kw_list = [k.strip() for k in re.split(r"[,;\n]+", kw) if k.strip()]
        doc["keywords"] = kw_list
    elif not isinstance(kw, list):
        doc["keywords"] = []

    # Viral score normalization
    try:
        doc["viral_score"] = int(doc.get("viral_score", 80))
    except (ValueError, TypeError):
        doc["viral_score"] = 80

    return doc


async def init_ideas_collection(db: Optional[Any] = None) -> bool:
    """Ensure indexes for ai_ideas collection (no auto-seeding on page load)."""
    col = _repo.get_collection(db)
    if col is not None:
        try:
            await _repo.ensure_indexes([("id", True), "status", "viral_score", "target_product_id"], db=db)
        except Exception as exc:
            logger.warning(f"Failed to ensure indexes for ai_ideas: {exc}")
    return True


async def list_ideas(
    db: Optional[Any] = None,
    search: str = "",
    status_filter: str = "all",
    format_filter: str = "all",
    product_filter: str = "all",
    page: int = 1,
    page_size: int = 6,
    sort_by: str = "updated_at",
) -> Dict[str, Any]:
    """Query, filter, and paginate AI ideas from MongoDB with in-memory fallback (default order: updated_at desc).

    Returns:
        dict with keys: items, total, pagination, stats, db_connected
    """
    await init_ideas_collection(db=db)

    query: Dict[str, Any] = {}

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    if format_filter and format_filter != "all":
        query["recommended_format"] = format_filter

    if product_filter and product_filter != "all":
        try:
            prod_id = int(product_filter)
            query["target_product_id"] = prod_id
        except ValueError:
            pass

    if search and search.strip():
        term = search.strip()
        regex_pattern = {"$regex": term, "$options": "i"}
        query["$or"] = [
            {"title": regex_pattern},
            {"angle": regex_pattern},
            {"target_audience": regex_pattern},
            {"keywords": regex_pattern},
            {"source_article": regex_pattern},
            {"outline": regex_pattern},
            {"target_product_name": regex_pattern},
        ]

    # Sort direction: default updated_at desc
    sort_field = "updated_at"
    sort_dir = -1
    if sort_by == "viral":
        sort_field = "viral_score"
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

    enriched_items = [format_idea_display(item) for item in items]
    stats = await get_ideas_kpis(db)

    return {
        "items": enriched_items,
        "total": pagination.total_items,
        "pagination": pagination,
        "stats": stats,
        "db_connected": is_connected,
    }


async def get_ideas_kpis(db: Optional[Any] = None) -> Dict[str, Any]:
    """Calculate KPI summary metrics for the AI Ideas library."""
    all_ideas, _ = await _repo.find_all(db=db)

    total = len(all_ideas)
    ready_count = sum(1 for i in all_ideas if i.get("status") == "ready")
    drafting_count = sum(1 for i in all_ideas if i.get("status") == "drafting")
    published_count = sum(1 for i in all_ideas if i.get("status") == "published")
    high_viral_count = sum(1 for i in all_ideas if int(i.get("viral_score", 0)) >= 90)

    # Format breakdown
    formats: Dict[str, int] = {}
    for i in all_ideas:
        fmt = i.get("recommended_format", "Bài viết dài")
        formats[fmt] = formats.get(fmt, 0) + 1

    return {
        "total_ideas": total,
        "ready_count": ready_count,
        "drafting_count": drafting_count,
        "published_count": published_count,
        "high_viral_count": high_viral_count,
        "formats": formats,
    }


async def get_idea_by_id(idea_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single AI Idea by its integer ID."""
    await init_ideas_collection(db=db)
    raw = await _repo.find_by_id(idea_id, db=db)
    if raw:
        return format_idea_display(raw)
    return None


async def create_idea(idea_data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Create a new AI Idea in the database."""
    await init_ideas_collection(db=db)

    # Generate next integer ID
    all_ideas, _ = await _repo.find_all(db=db)
    max_id = max([int(item.get("id", 0)) for item in all_ideas], default=0)
    new_id = max_id + 1

    # Keywords normalize
    keywords = idea_data.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in re.split(r"[,;\n]+", keywords) if k.strip()]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    doc = {
        "id": new_id,
        "title": idea_data.get("title", "").strip(),
        "angle": idea_data.get("angle", "").strip(),
        "target_audience": idea_data.get("target_audience", "").strip(),
        "recommended_format": idea_data.get("recommended_format", "Bài viết dài (Blog / Website)"),
        "viral_score": int(idea_data.get("viral_score", 85)),
        "status": idea_data.get("status", "ready"),
        "keywords": keywords,
        "outline": idea_data.get("outline", ""),
        "source_article_id": int(idea_data["source_article_id"]) if idea_data.get("source_article_id") else None,
        "source_article": idea_data.get("source_article", "").strip(),
        "target_product_id": int(idea_data["target_product_id"]) if idea_data.get("target_product_id") else None,
        "target_product_name": idea_data.get("target_product_name", "").strip(),
        "target_platform": idea_data.get("target_platform", "").strip(),
        "ai_prompt_used": idea_data.get("ai_prompt_used", ""),
        "notes": idea_data.get("notes", ""),
        "created_at": now_str,
        "updated_at": now_str,
    }

    # Validate with model
    model = AIIdeaModel(**doc)
    doc_dict = model.to_mongo_doc()

    created = await _repo.insert(doc_dict, auto_id=False, db=db)
    return format_idea_display(created)


async def update_idea(idea_id: int, update_data: Dict[str, Any], db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Update fields of an existing AI Idea."""
    await init_ideas_collection(db=db)

    clean_data = dict(update_data)
    clean_data.pop("id", None)
    clean_data.pop("_id", None)

    if "keywords" in clean_data and isinstance(clean_data["keywords"], str):
        clean_data["keywords"] = [k.strip() for k in re.split(r"[,;\n]+", clean_data["keywords"]) if k.strip()]

    if "viral_score" in clean_data and clean_data["viral_score"] is not None:
        try:
            clean_data["viral_score"] = int(clean_data["viral_score"])
        except ValueError:
            pass

    if "target_product_id" in clean_data and clean_data["target_product_id"]:
        try:
            clean_data["target_product_id"] = int(clean_data["target_product_id"])
        except ValueError:
            pass

    if "source_article_id" in clean_data and clean_data["source_article_id"]:
        try:
            clean_data["source_article_id"] = int(clean_data["source_article_id"])
        except ValueError:
            pass

    clean_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    updated = await _repo.update(idea_id, clean_data, db=db)
    if updated:
        return format_idea_display(updated)
    return None


async def delete_idea(idea_id: int, db: Optional[Any] = None) -> bool:
    """Delete an AI Idea by its ID."""
    await init_ideas_collection(db=db)
    return await _repo.delete(idea_id, db=db)


async def update_idea_status(idea_id: int, new_status: str, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Quickly update the workflow status of an AI Idea (ready -> drafting -> reviewing -> published)."""
    return await update_idea(idea_id, {"status": new_status}, db=db)


async def assign_product_to_idea(
    idea_id: int,
    product_id: int,
    product_name: str,
    platform: Optional[str] = None,
    db: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Assign an AI Idea to a target user product / channel."""
    update_fields = {
        "target_product_id": product_id,
        "target_product_name": product_name,
    }
    if platform:
        update_fields["target_platform"] = platform
    return await update_idea(idea_id, update_fields, db=db)


async def generate_idea_from_article(article: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Simulate AI generation of a creative angle & outline from a crawled article."""
    art_title = article.get("title", "")
    art_id = article.get("id")
    category = article.get("category", "Tổng hợp")
    viral_pot = int(article.get("viral_potential", 85))

    new_idea_data = {
        "title": f"Phân tích chuyên sâu: {art_title}",
        "angle": f"Góc nhìn đa chiều về {category}, phân tích ảnh hưởng trực tiếp tới người tiêu dùng Việt Nam",
        "target_audience": "Độc giả trẻ, Nhà đầu tư cá nhân, Cộng đồng trực tuyến",
        "recommended_format": "Bài viết dài (Blog / Website)",
        "viral_score": min(98, max(75, viral_pot + 2)),
        "status": "ready",
        "keywords": article.get("tags", [category, "AI", "Xu hướng"]),
        "outline": f"""1. Tổng quan vấn đề được nêu trong bài viết '{art_title}'.
2. 3 phát hiện quan trọng nhất và số liệu thực tế cần lưu tâm.
3. Dự báo xu hướng phát triển trong 6-12 tháng tới.
4. Lời khuyên hành động cụ thể cho người đọc.""",
        "source_article_id": art_id,
        "source_article": art_title,
        "target_product_id": article.get("target_product_id"),
        "target_product_name": article.get("target_product_name", ""),
        "ai_prompt_used": "Trích xuất ý tưởng và phác thảo dàn ý nội dung từ tin tức thu thập thời gian thực",
        "notes": f"Sinh tự động từ bài thu thập #{art_id}",
    }
    return await create_idea(new_idea_data, db=db)


async def reset_demo_ideas(db: Optional[Any] = None) -> int:
    """Reset the AI Ideas collection back to DEFAULT_IDEAS seed data."""
    all_ideas, _ = await _repo.find_all(db=db)
    for item in all_ideas:
        await _repo.delete(item["id"], db=db)
    for seed in DEFAULT_IDEAS:
        await _repo.insert(dict(seed), auto_id=False, db=db)
    return len(DEFAULT_IDEAS)
