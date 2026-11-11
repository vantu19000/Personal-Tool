"""Services and repository operations for My Products & Publishing Channels Management."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository
from app.core.pagination import PaginationMeta
from app.products.models import (
    PLATFORM_METADATA,
    PRODUCT_STATUS_METADATA,
    ProductModel,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "my_products"

# Initial seed data showcasing products across key platforms
DEFAULT_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Kênh YouTube BĐS & Quy Hoạch Thủ Đô",
        "platform": "youtube",
        "code": "yt-bds-thudo",
        "url": "https://youtube.com/@bdsthudo",
        "niche": "Bất động sản & Quy hoạch",
        "target_audience": "Nhà đầu tư cá nhân, gia đình mua nhà ở thực (28-48 tuổi)",
        "content_format": "Video dài phân tích (10-15 phút) & YouTube Shorts (<60s)",
        "posting_frequency": "2 video dài/tuần + 5 Shorts/tuần",
        "brand_voice": "Chuyên gia thực chiến, minh bạch số liệu, dẫn chứng bản đồ khách quan",
        "ai_system_prompt": "Cấu trúc kịch bản 3 phần: 1. Hook 5s đầu đánh trúng thắc mắc giá đất/pháp lý, 2. Phân tích thực tế bản đồ phân khu và 3 lưu ý rủi ro cho người mua, 3. Call-to-action kêu gọi bình luận để nhận tài liệu quy hoạch chi tiết.",
        "tags": ["Bất động sản", "YouTube", "Quy hoạch", "Video dài"],
        "status": "active",
        "followers_metric": "38.5K Subs",
        "assigned_ideas_count": 14,
        "published_content_count": 52,
        "last_published_at": "Hôm qua lúc 19:30",
        "description": "Kênh YouTube chủ lực chuyên giải mã các khu vực sốt đất ven đô và tiến độ dự án hạ tầng giao thông lớn.",
        "created_at": "2026-11-01 09:00",
        "updated_at": "2026-11-11 15:20",
    },
    {
        "id": 2,
        "name": "TikTok GenZ Đầu Tư & Tài Chính Cá Nhân",
        "platform": "tiktok",
        "code": "tiktok-genz-finance",
        "url": "https://tiktok.com/@genz_dautu",
        "niche": "Tài chính & Đầu tư trẻ",
        "target_audience": "Sinh viên, người mới đi làm (18-27 tuổi)",
        "content_format": "Video dọc ngắn (30s-45s), nhịp cắt nhanh, phụ đề nổi bật",
        "posting_frequency": "1 video/ngày (khung giờ 11:30 & 20:00)",
        "brand_voice": "Trẻ trung, hài hước, dùng ngôn ngữ bắt trend Gen Z, không dùng thuật ngữ học thuật khô khan",
        "ai_system_prompt": "Viết kịch bản video TikTok tốc độ cao. Dòng mở đầu (hook) phải đánh trúng tâm lý FOMO hoặc sai lầm mất tiền phổ biến. Nội dung cô đọng trong 3 ý chính, kết thúc bằng một câu hỏi bỏ lửng để kích thích người xem comment tranh luận.",
        "tags": ["TikTok", "Tài chính GenZ", "Video ngắn", "Viral"],
        "status": "active",
        "followers_metric": "112.4K Followers",
        "assigned_ideas_count": 22,
        "published_content_count": 94,
        "last_published_at": "3 giờ trước",
        "description": "Kênh sáng tạo video ngắn chia sẻ mẹo tiết kiệm, kinh nghiệm quản lý dòng tiền và bài học đầu tư nhỏ.",
        "created_at": "2026-11-02 10:15",
        "updated_at": "2026-11-11 16:45",
    },
    {
        "id": 3,
        "name": "Web Blog Công Nghệ AI & Tự Động Hóa",
        "platform": "web_blog",
        "code": "blog-ai-automation",
        "url": "https://blog.personaltool.vn",
        "niche": "Công nghệ & AI Agent",
        "target_audience": "Chủ doanh nghiệp vừa & nhỏ (SMBs), Marketer, Lập trình viên",
        "content_format": "Bài viết chuẩn SEO (1500-2500 từ), có mục lục H2/H3, bảng so sánh và FAQ Schema",
        "posting_frequency": "3 bài viết/tuần",
        "brand_voice": "Chuyên sâu, cấu trúc mạch lạc, hướng dẫn từng bước có hình ảnh minh họa",
        "ai_system_prompt": "Soạn thảo bài viết blog chuẩn SEO đạt chuẩn Google E-E-A-T: Tiêu đề thu hút chứa từ khóa chính, cấu trúc heading phân tầng rõ ràng, các khối blockquote điểm nhấn, danh mục 4 câu hỏi thường gặp (FAQ) và meta description tối ưu dưới 160 ký tự.",
        "tags": ["Web Blog", "SEO", "Công nghệ AI", "Hướng dẫn"],
        "status": "active",
        "followers_metric": "45K Views/tháng",
        "assigned_ideas_count": 18,
        "published_content_count": 76,
        "last_published_at": "2 ngày trước",
        "description": "Blog chuyên sâu đóng vai trò phễu thu hút lưu lượng tìm kiếm tự nhiên (Organic Search Traffic) về công nghệ tự động hóa.",
        "created_at": "2026-11-03 14:00",
        "updated_at": "2026-11-10 11:30",
    },
    {
        "id": 4,
        "name": "Fanpage & Nhóm Cộng Đồng Nhà Đất Thực Chiến",
        "platform": "facebook",
        "code": "fb-nhadat-thucchien",
        "url": "https://facebook.com/bds.thucchien.vn",
        "niche": "Bất động sản & Kinh tế",
        "target_audience": "Môi giới BĐS, nhà đầu tư thực địa, người tìm mua căn hộ",
        "content_format": "Bài post hình ảnh / Infographic tóm tắt + Status thảo luận",
        "posting_frequency": "1-2 bài đăng/ngày",
        "brand_voice": "Gần gũi, tính gắn kết cộng đồng cao, khơi gợi chia sẻ góc nhìn thực tế",
        "ai_system_prompt": "Viết bài Facebook theo phong cách Storytelling chia sẻ bài học thực chiến hoặc kinh nghiệm kiểm tra pháp lý sổ đỏ. Sử dụng định dạng gạch đầu dòng thoáng mắt, icon hợp lý và đặt câu hỏi mở ở cuối để kích thích tương tác thảo luận.",
        "tags": ["Facebook", "Fanpage", "Cộng đồng", "BĐS"],
        "status": "active",
        "followers_metric": "28.9K Likes",
        "assigned_ideas_count": 9,
        "published_content_count": 124,
        "last_published_at": "Hôm nay lúc 11:00",
        "description": "Trang truyền thông cộng đồng tương tác cao, nơi bàn luận các chính sách đất đai và review dự án.",
        "created_at": "2026-11-04 15:30",
        "updated_at": "2026-11-11 11:00",
    },
    {
        "id": 5,
        "name": "Instagram Không Gian & Phong Cách Sống Đẹp",
        "platform": "instagram",
        "code": "ig-khonggian-dep",
        "url": "https://instagram.com/khonggian.songdep",
        "niche": "Decor & Phong cách sống",
        "target_audience": "Giới trẻ văn phòng, người yêu decor nhà cửa, gia đình trẻ",
        "content_format": "Carousel 8-10 slide hình ảnh thiết kế + Reels ngắn truyền cảm hứng",
        "posting_frequency": "4 post/tuần (thứ 3, 5, 7, CN)",
        "brand_voice": "Tinh tế, nhẹ nhàng, truyền cảm hứng sống chậm và chữa lành",
        "ai_system_prompt": "Viết caption Instagram ngắn gọn, giàu cảm xúc và hình tượng. Cung cấp gợi ý cách bài trí căn hộ theo chủ đề tối giản (Minimalism) kèm bộ 15 hashtag thịnh hành về decor nhà cửa.",
        "tags": ["Instagram", "Visual", "Decor", "Lifestyle"],
        "status": "active",
        "followers_metric": "19.6K Followers",
        "assigned_ideas_count": 11,
        "published_content_count": 38,
        "last_published_at": "Hôm qua lúc 21:00",
        "description": "Kênh xây dựng thương hiệu hình ảnh thị giác (Visual Brand) tập trung vào phong cách sống và nội thất.",
        "created_at": "2026-11-05 16:45",
        "updated_at": "2026-11-10 21:00",
    },
    {
        "id": 6,
        "name": "Pinterest Moodboard Thiết Kế Xanh & Căn Hộ",
        "platform": "pinterest",
        "code": "pin-greendecor",
        "url": "https://pinterest.com/greendecor_vietnam",
        "niche": "Ý tưởng thiết kế & Kiến trúc",
        "target_audience": "Người chuẩn bị xây sửa nhà, kiến trúc sư, nhà thiết kế nội thất",
        "content_format": "Pin ảnh dọc (2:3, 1000x1500px) & Idea Pins hướng dẫn",
        "posting_frequency": "5 pins/ngày (ghim tự động theo lịch)",
        "brand_voice": "Trực quan, cô đọng, định hướng thẩm mỹ",
        "ai_system_prompt": "Tạo tiêu đề Pin chuẩn SEO Pinterest chứa từ khóa người dùng hay tìm kiếm (ví dụ: 'thiết kế căn hộ 50m2', 'mẫu ban công xanh'). Viết mô tả 70-100 từ kèm lời kêu gọi lưu ghim (Save Pin) về bảng cá nhân.",
        "tags": ["Pinterest", "Moodboard", "Kiến trúc", "Infographic"],
        "status": "active",
        "followers_metric": "8.4K Followers · 120K Views/tháng",
        "assigned_ideas_count": 8,
        "published_content_count": 65,
        "last_published_at": "Hôm nay 08:30",
        "description": "Kho ý tưởng thẩm mỹ trực quan dẫn lưu lượng truy cập dài hạn (Evergreen Traffic) về website.",
        "created_at": "2026-11-06 09:30",
        "updated_at": "2026-11-11 08:30",
    },
]


class ProductRepository(BaseMongoRepository):
    """Repository handling CRUD operations for user products/channels."""

    def __init__(self) -> None:
        super().__init__(collection_name=COLLECTION_NAME, id_field="id")


_repo = ProductRepository()


async def init_products_collection(db: Optional[Any] = None) -> None:
    """Ensure indexes for user_products collection (no auto-seeding on service init)."""
    col = _repo.get_collection(db)
    if col is not None:
        try:
            await _repo.ensure_indexes([
                ("id", True),
                "platform",
                "status",
                "niche",
                "code",
            ], db)
        except Exception as exc:
            logger.warning(f"Failed to ensure indexes for my_products: {exc}")


def format_product_display(product: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich product dictionary with visual tags, platform labels, and badges."""
    p = dict(product)
    plat = p.get("platform", "youtube")
    status_key = p.get("status", "active")

    plat_meta = PLATFORM_METADATA.get(plat, PLATFORM_METADATA["other"])
    status_meta = PRODUCT_STATUS_METADATA.get(status_key, PRODUCT_STATUS_METADATA["active"])

    p["platform_label"] = plat_meta.get("label", plat.title())
    p["platform_sub_label"] = plat_meta.get("sub_label", "")
    p["platform_icon"] = plat_meta.get("icon", "box")
    p["platform_badge_color"] = plat_meta.get("badge_color", "bg-slate-100 text-slate-700")
    p["platform_color_class"] = plat_meta.get("color_class", "text-slate-600")
    p["platform_bg_soft"] = plat_meta.get("bg_soft", "bg-slate-50")
    p["default_format"] = plat_meta.get("default_format", "")

    p["status_label"] = status_meta.get("label", status_key.title())
    p["status_badge_color"] = status_meta.get("badge_color", "bg-slate-100 text-slate-700")
    p["status_dot_color"] = status_meta.get("dot_color", "bg-slate-400")

    # Clean tags
    if isinstance(p.get("tags"), str):
        raw_tags = p["tags"].replace(";", ",").split(",")
        p["tags"] = [t.strip() for t in raw_tags if t.strip()]
    elif not p.get("tags"):
        p["tags"] = []

    return p


async def list_products(
    db: Optional[Any] = None,
    search: str = "",
    platform_filter: str = "all",
    status_filter: str = "all",
    niche_filter: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "id",
) -> Dict[str, Any]:
    """Retrieve filtered, paginated list of user products / channels."""
    await init_products_collection(db)

    query: Dict[str, Any] = {}

    if platform_filter and platform_filter != "all":
        query["platform"] = platform_filter

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    if niche_filter and niche_filter != "all":
        query["niche"] = niche_filter

    clean_search = (search or "").strip()
    if clean_search:
        regex_pattern = {"$regex": re.escape(clean_search), "$options": "i"}
        query["$or"] = [
            {"name": regex_pattern},
            {"url": regex_pattern},
            {"code": regex_pattern},
            {"niche": regex_pattern},
            {"target_audience": regex_pattern},
            {"brand_voice": regex_pattern},
            {"ai_system_prompt": regex_pattern},
            {"tags": regex_pattern},
        ]

    sort_field = "id"
    sort_dir = 1
    if sort_by == "name":
        sort_field = "name"
        sort_dir = 1
    elif sort_by == "published":
        sort_field = "published_content_count"
        sort_dir = -1
    elif sort_by == "ideas":
        sort_field = "assigned_ideas_count"
        sort_dir = -1
    elif sort_by == "created_at":
        sort_field = "created_at"
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

    enriched_items = [format_product_display(item) for item in items]
    stats = await get_product_kpi_stats(db)

    return {
        "items": enriched_items,
        "total": pagination.total_items,
        "pagination": pagination,
        "stats": stats,
        "db_connected": is_connected,
    }


async def get_product_kpi_stats(db: Optional[Any] = None) -> Dict[str, Any]:
    """Compute KPI metrics and breakdown counts by platform and status."""
    all_products, _ = await _repo.find_all(db=db)

    total = len(all_products)
    active_count = sum(1 for p in all_products if p.get("status") == "active")
    paused_count = sum(1 for p in all_products if p.get("status") == "paused")
    planning_count = sum(1 for p in all_products if p.get("status") == "planning")
    total_published = sum(int(p.get("published_content_count", 0)) for p in all_products)
    total_assigned_ideas = sum(int(p.get("assigned_ideas_count", 0)) for p in all_products)

    # Counts by platform
    platform_counts: Dict[str, int] = {k: 0 for k in PLATFORM_METADATA.keys()}
    for p in all_products:
        plat = p.get("platform", "other")
        if plat in platform_counts:
            platform_counts[plat] += 1
        else:
            platform_counts[plat] = 1

    return {
        "total_products": total,
        "active_count": active_count,
        "paused_count": paused_count,
        "planning_count": planning_count,
        "total_published": total_published,
        "total_assigned_ideas": total_assigned_ideas,
        "platform_counts": platform_counts,
    }


async def get_product_by_id(product_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieve single product by integer ID."""
    doc = await _repo.find_by_id(product_id, db=db)
    if doc:
        return format_product_display(doc)
    return None


async def create_product(data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Create a new product / channel."""
    await init_products_collection(db)

    highest_id = await _repo.get_next_id(db=db)

    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
    elif not isinstance(tags, list):
        tags = []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = {
        "id": highest_id,
        "name": (data.get("name") or "").strip(),
        "platform": (data.get("platform") or "youtube").strip().lower(),
        "code": (data.get("code") or "").strip().lower(),
        "url": (data.get("url") or "").strip(),
        "niche": (data.get("niche") or "Chung").strip(),
        "target_audience": (data.get("target_audience") or "").strip(),
        "content_format": (data.get("content_format") or "").strip(),
        "posting_frequency": (data.get("posting_frequency") or "Hàng tuần").strip(),
        "brand_voice": (data.get("brand_voice") or "").strip(),
        "ai_system_prompt": (data.get("ai_system_prompt") or "").strip(),
        "tags": tags,
        "status": data.get("status") or "active",
        "followers_metric": (data.get("followers_metric") or "").strip(),
        "assigned_ideas_count": 0,
        "published_content_count": 0,
        "last_published_at": "Chưa xuất bản",
        "description": (data.get("description") or "").strip(),
        "created_at": now_str,
        "updated_at": now_str,
    }

    inserted = await _repo.insert(doc, auto_id=False, db=db)
    return format_product_display(inserted)


async def update_product(product_id: int, data: Dict[str, Any], db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Update fields of an existing product / channel."""
    current = await _repo.find_by_id(product_id, db=db)
    if not current:
        return None

    update_payload: Dict[str, Any] = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    allowed_fields = [
        "name", "platform", "code", "url", "niche", "target_audience",
        "content_format", "posting_frequency", "brand_voice",
        "ai_system_prompt", "status", "followers_metric", "description",
    ]

    for field in allowed_fields:
        if field in data and data[field] is not None:
            val = data[field]
            if isinstance(val, str):
                val = val.strip()
            update_payload[field] = val

    if "tags" in data and data["tags"] is not None:
        tags = data["tags"]
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
        elif not isinstance(tags, list):
            tags = []
        update_payload["tags"] = tags

    updated = await _repo.update(product_id, update_payload, db=db)
    if updated:
        return format_product_display(updated)
    return None


async def delete_product(product_id: int, db: Optional[Any] = None) -> bool:
    """Delete a product by integer ID."""
    return await _repo.delete(product_id, db=db)


async def toggle_product_status(product_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Toggle product status between 'active' and 'paused'."""
    prod = await _repo.find_by_id(product_id, db=db)
    if not prod:
        return None
    new_status = "paused" if prod.get("status") == "active" else "active"
    return await update_product(product_id, {"status": new_status}, db=db)


async def reset_demo_products(db: Optional[Any] = None) -> int:
    """Reset the products collection back to the default seed products."""
    await init_products_collection(db)
    all_current, _ = await _repo.find_all(db=db)
    for c in all_current:
        await _repo.delete(c["id"], db=db)
    for p in DEFAULT_PRODUCTS:
        await _repo.insert(dict(p), auto_id=False, db=db)
    return len(DEFAULT_PRODUCTS)


async def get_niches_dropdown(db: Optional[Any] = None) -> List[str]:
    """Retrieve distinct list of content niches used across all products."""
    all_products, _ = await _repo.find_all(db=db)
    niches = set()
    for p in all_products:
        n = (p.get("niche") or "").strip()
        if n:
            niches.add(n)
    return sorted(list(niches))
