"""Services and repository operations for Crawler Source Management."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository
from app.core.pagination import PaginationMeta
from app.sources.models import (
    PRIORITY_METADATA,
    SCHEDULE_OPTIONS,
    SOURCE_TYPE_METADATA,
    STATUS_METADATA,
    SourceModel,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "crawler_sources"

# Initial seed data showcasing all 9 required types and fields
DEFAULT_SOURCES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "VnExpress - Chuyên mục Bất động sản",
        "type": "website",
        "url": "https://vnexpress.net/bat-dong-san",
        "province": "Hà Nội",
        "district": "Hoàn Kiếm",
        "ward": "Phường Hàng Trống",
        "tags": ["Bất động sản", "Thị trường", "Quy hoạch 2026", "Chính sách"],
        "schedule": "15_min",
        "priority": "high",
        "status": "active",
        "ai_prompt": "Trích xuất tiêu đề, phân tích 3 biến động giá đất chính, nhận diện địa bàn bị ảnh hưởng và đề xuất 2 góc tiếp cận nội dung cho nhà đầu tư cá nhân.",
        "description": "Cổng thông tin báo điện tử có lượng truy cập lớn nhất, cập nhật liên tục giá nhà đất và thị trường.",
        "last_scanned_at": "5 phút trước",
        "articles_count": 142,
        "success_rate": 99.4,
        "created_at": "2026-11-10 08:30",
        "updated_at": "2026-11-11 14:15",
    },
    {
        "id": 2,
        "name": "Báo Tuổi Trẻ - Tin tức Kinh doanh RSS",
        "type": "rss",
        "url": "https://tuoitre.vn/rss/kinh-doanh.rss",
        "province": "TP. Hồ Chí Minh",
        "district": "Quận 1",
        "ward": "Phường Bến Nghé",
        "tags": ["Kinh tế", "Tài chính", "Doanh nghiệp", "Đầu tư"],
        "schedule": "30_min",
        "priority": "high",
        "status": "active",
        "ai_prompt": "Bóc tách các chỉ số kinh tế vĩ mô, lãi suất ngân hàng và các doanh nghiệp niêm yết có động thái tái cấu trúc vốn.",
        "description": "Kênh RSS chuẩn định dạng XML cập nhật tức thời các bài phân tích tài chính.",
        "last_scanned_at": "12 phút trước",
        "articles_count": 98,
        "success_rate": 100.0,
        "created_at": "2026-11-10 09:00",
        "updated_at": "2026-11-11 14:00",
    },
    {
        "id": 3,
        "name": "Cộng đồng Quy hoạch & BĐS Hà Nội",
        "type": "facebook",
        "url": "https://facebook.com/groups/bds.quyhoach.hanoi",
        "province": "Hà Nội",
        "district": "Cầu Giấy",
        "ward": "Phường Dịch Vọng Hậu",
        "tags": ["Facebook Group", "Quy hoạch Vành Đai 4", "Cộng đồng", "Hỏi đáp"],
        "schedule": "1_hour",
        "priority": "medium",
        "status": "active",
        "ai_prompt": "Lọc thảo luận thực tế của thành viên, loại bỏ tin rao vặt spam, trích xuất nhu cầu tìm kiếm đất nền vùng ven và câu hỏi pháp lý nổi bật.",
        "description": "Nhóm thảo luận hơn 180.000 thành viên chuyên chia sẻ bản đồ phân khu và quy hoạch thực tế.",
        "last_scanned_at": "25 phút trước",
        "articles_count": 67,
        "success_rate": 95.8,
        "created_at": "2026-11-10 10:15",
        "updated_at": "2026-11-11 13:45",
    },
    {
        "id": 4,
        "name": "Kênh VTV24 - Tiêu điểm Kinh tế & Đô thị",
        "type": "youtube",
        "url": "https://youtube.com/@vtv24",
        "province": "Hà Nội",
        "district": "Ba Đình",
        "ward": "Phường Giảng Võ",
        "tags": ["Video", "Truyền hình", "Phóng sự", "Xu hướng tiêu dùng"],
        "schedule": "3_hours",
        "priority": "high",
        "status": "active",
        "ai_prompt": "Lấy transcript video mới nhất, tóm tắt tin tức trong 60 giây và gợi ý 3 hook câu mở đầu hấp dẫn cho video ngắn TikTok/Shorts.",
        "description": "Kênh video chính luận & phóng sự điều tra kinh tế xã hội uy tín nhất.",
        "last_scanned_at": "1 giờ trước",
        "articles_count": 45,
        "success_rate": 98.2,
        "created_at": "2026-11-10 11:00",
        "updated_at": "2026-11-11 13:10",
    },
    {
        "id": 5,
        "name": "TikTok Marketing & E-Commerce Trends VN",
        "type": "tiktok",
        "url": "https://tiktok.com/@marketingtrends_vn",
        "province": "TP. Hồ Chí Minh",
        "district": "Quận 3",
        "ward": "Phường Võ Thị Sáu",
        "tags": ["TikTok", "Shoppertainment", "Gen Z", "KOL Livestream"],
        "schedule": "1_hour",
        "priority": "medium",
        "status": "active",
        "ai_prompt": "Bóc tách hashtag xu hướng, phát hiện âm thanh nền viral và phân tích định dạng nội dung đạt tỷ lệ giữ chân người xem cao nhất.",
        "description": "Kênh theo dõi các trào lưu short-form video và thương mại điện tử mới nổi.",
        "last_scanned_at": "38 phút trước",
        "articles_count": 89,
        "success_rate": 97.0,
        "created_at": "2026-11-10 12:00",
        "updated_at": "2026-11-11 14:10",
    },
    {
        "id": 6,
        "name": "Sở Xây Dựng Đà Nẵng - Báo cáo & Quyết định PDF",
        "type": "pdf",
        "url": "https://soxaydung.danang.gov.vn/van-ban/bao-cao-quy-hoach-2026.pdf",
        "province": "Đà Nẵng",
        "district": "Hải Châu",
        "ward": "Phường Thạch Thang",
        "tags": ["PDF", "Văn bản hành chính", "Quy hoạch", "Pháp lý"],
        "schedule": "daily",
        "priority": "urgent",
        "status": "active",
        "ai_prompt": "Trích xuất OCR bảng số liệu diện tích, chỉ tiêu tầng cao quy hoạch, tên chủ đầu tư và điều kiện mở bán dự án theo luật mới.",
        "description": "Nguồn văn bản PDF chính thức từ cơ quan quản lý nhà nước về cấp phép và quy hoạch.",
        "last_scanned_at": "Hôm nay 06:15",
        "articles_count": 18,
        "success_rate": 100.0,
        "created_at": "2026-11-10 14:00",
        "updated_at": "2026-11-11 06:15",
    },
    {
        "id": 7,
        "name": "Google Drive - Thư viện Hồ sơ Nghiên cứu Thị trường",
        "type": "gdrive",
        "url": "https://drive.google.com/drive/folders/1z_sample_research_drives_2026",
        "province": "Bình Dương",
        "district": "Thủ Dầu Một",
        "ward": "Phường Phú Cường",
        "tags": ["Google Drive", "Nội bộ", "Khảo sát thực địa", "Dữ liệu thô"],
        "schedule": "6_hours",
        "priority": "medium",
        "status": "active",
        "ai_prompt": "Phân tích tài liệu mới upload vào folder, tổng hợp các bảng khảo sát giá thực tế tại địa bàn và lập bảng so sánh theo quý.",
        "description": "Thư mục đám mây chia sẻ báo cáo phân tích và hình ảnh thực địa của đội ngũ khảo sát.",
        "last_scanned_at": "3 giờ trước",
        "articles_count": 31,
        "success_rate": 96.5,
        "created_at": "2026-11-10 15:30",
        "updated_at": "2026-11-11 11:20",
    },
    {
        "id": 8,
        "name": "Nguồn Bài viết Chuyên gia Tuyển chọn",
        "type": "manual",
        "url": "manual://curated-expert-articles",
        "province": "Toàn quốc",
        "district": "Toàn quốc",
        "ward": "Toàn quốc",
        "tags": ["Thủ công", "Chuyên sâu", "Nhận định chuyên gia", "Độc quyền"],
        "schedule": "manual",
        "priority": "low",
        "status": "active",
        "ai_prompt": "Tái cấu trúc bài viết theo phong cách chuyên sâu, kiểm chứng các số liệu trích dẫn và sinh danh mục 5 câu hỏi phỏng vấn tiếp theo.",
        "description": "Kho tài liệu thu thập thủ công từ các hội thảo, ấn phẩm in và chia sẻ kín của chuyên gia.",
        "last_scanned_at": "Hôm qua",
        "articles_count": 14,
        "success_rate": 100.0,
        "created_at": "2026-11-10 16:45",
        "updated_at": "2026-11-11 09:30",
    },
    {
        "id": 9,
        "name": "Cổng Dữ liệu Mở Quốc gia - Open Data API",
        "type": "api",
        "url": "https://data.gov.vn/api/v1/indicators/economics-trade",
        "province": "Hà Nội",
        "district": "Hoàn Kiếm",
        "ward": "Phường Tràng Tiền",
        "tags": ["API", "JSON", "Dữ liệu mở", "Chỉ số kinh tế"],
        "schedule": "12_hours",
        "priority": "high",
        "status": "active",
        "ai_prompt": "Chuyển payload JSON thành bản tóm lược xu hướng kinh tế, phát hiện các điểm dị biệt (anomalies) và vẽ biểu đồ biến động theo ngành.",
        "description": "Endpoint REST API trả về dữ liệu định dạng JSON cấu trúc cao từ cổng chính phủ.",
        "last_scanned_at": "4 giờ trước",
        "articles_count": 112,
        "success_rate": 99.8,
        "created_at": "2026-11-10 17:00",
        "updated_at": "2026-11-11 10:15",
    },
]


class SourceRepository(BaseMongoRepository):
    """Repository handling CRUD operations for crawler sources."""

    def __init__(self) -> None:
        super().__init__(collection_name=COLLECTION_NAME, id_field="id")


_repo = SourceRepository()


async def init_sources_collection(db: Optional[Any] = None) -> None:
    """Ensure indexes and seed initial sources if empty."""
    col = _repo.get_collection(db)
    if col is not None:
        try:
            await _repo.ensure_indexes([
                ("id", True),
                "type",
                "status",
                "priority",
                "province",
                "schedule",
            ], db)
        except Exception as exc:
            logger.warning(f"Failed to ensure indexes for crawler_sources: {exc}")

    # Seed initial 9 sources if empty
    count = await _repo.count({}, db)
    if count == 0:
        logger.info(f"Seeding {len(DEFAULT_SOURCES)} initial crawler sources...")
        await _repo.seed_if_empty(DEFAULT_SOURCES, db)


def format_source_display(source: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich source dictionary with visual tags, labels, and badges."""
    s = dict(source)
    stype = s.get("type", "website")
    sprio = s.get("priority", "medium")
    sstatus = s.get("status", "active")
    ssched = s.get("schedule", "1_hour")

    # Meta
    type_meta = SOURCE_TYPE_METADATA.get(stype, SOURCE_TYPE_METADATA["website"])
    prio_meta = PRIORITY_METADATA.get(sprio, PRIORITY_METADATA["medium"])
    status_meta = STATUS_METADATA.get(sstatus, STATUS_METADATA["active"])

    s["type_label"] = type_meta.get("label", stype.title())
    s["type_sub_label"] = type_meta.get("sub_label", "")
    s["type_icon"] = type_meta.get("icon", "globe")
    s["type_badge_color"] = type_meta.get("badge_color", "bg-slate-100 text-slate-700")
    s["type_color_class"] = type_meta.get("color_class", "text-slate-600")
    s["type_bg_soft"] = type_meta.get("bg_soft", "bg-slate-50")

    s["priority_label"] = prio_meta.get("label", sprio.title())
    s["priority_badge_color"] = prio_meta.get("badge_color", "bg-slate-100 text-slate-700")
    s["priority_icon"] = prio_meta.get("icon", "minus")

    s["status_label"] = status_meta.get("label", sstatus.title())
    s["status_badge_color"] = status_meta.get("badge_color", "bg-slate-100 text-slate-700")
    s["status_dot_color"] = status_meta.get("dot_color", "bg-slate-400")

    s["schedule_label"] = SCHEDULE_OPTIONS.get(ssched, ssched)

    # Ensure tags is list
    if isinstance(s.get("tags"), str):
        raw_tags = s["tags"].replace(";", ",").split(",")
        s["tags"] = [t.strip() for t in raw_tags if t.strip()]
    elif not s.get("tags"):
        s["tags"] = []

    # Geographic summary
    loc_parts = []
    if s.get("ward"):
        loc_parts.append(s["ward"])
    if s.get("district"):
        loc_parts.append(s["district"])
    if s.get("province") and s.get("province") != "Toàn quốc":
        loc_parts.append(s["province"])
    s["location_summary"] = ", ".join(loc_parts) if loc_parts else (s.get("province") or "Toàn quốc")

    return s


async def list_sources(
    db: Optional[Any] = None,
    search: str = "",
    type_filter: str = "all",
    priority_filter: str = "all",
    status_filter: str = "all",
    province_filter: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "priority",
) -> Dict[str, Any]:
    """Retrieve filtered, paginated list of crawler sources."""
    await init_sources_collection(db)

    query: Dict[str, Any] = {}

    if type_filter and type_filter != "all":
        query["type"] = type_filter

    if priority_filter and priority_filter != "all":
        query["priority"] = priority_filter

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    if province_filter and province_filter != "all":
        query["province"] = province_filter

    # Text search across name, url, tags, ai_prompt, province
    clean_search = (search or "").strip()
    if clean_search:
        regex_pattern = {"$regex": re.escape(clean_search), "$options": "i"}
        query["$or"] = [
            {"name": regex_pattern},
            {"url": regex_pattern},
            {"tags": regex_pattern},
            {"province": regex_pattern},
            {"district": regex_pattern},
            {"ward": regex_pattern},
            {"ai_prompt": regex_pattern},
        ]

    # Sort logic
    sort_field = "id"
    sort_dir = 1
    if sort_by == "name":
        sort_field = "name"
        sort_dir = 1
    elif sort_by == "articles":
        sort_field = "articles_count"
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

    enriched_items = [format_source_display(item) for item in items]

    # Compute quick stats
    stats = await get_kpi_stats(db)

    return {
        "items": enriched_items,
        "total": pagination.total_items,
        "pagination": pagination,
        "stats": stats,
        "db_connected": is_connected,
    }


async def get_kpi_stats(db: Optional[Any] = None) -> Dict[str, Any]:
    """Compute KPI metrics and breakdown counts by type/priority/status."""
    all_sources, _ = await _repo.find_all(db=db)

    total = len(all_sources)
    active_count = sum(1 for s in all_sources if s.get("status") == "active")
    paused_count = sum(1 for s in all_sources if s.get("status") == "paused")
    error_count = sum(1 for s in all_sources if s.get("status") == "error")
    total_articles = sum(int(s.get("articles_count", 0)) for s in all_sources)

    # Type counts
    type_counts: Dict[str, int] = {k: 0 for k in SOURCE_TYPE_METADATA.keys()}
    for s in all_sources:
        t = s.get("type", "website")
        if t in type_counts:
            type_counts[t] += 1
        else:
            type_counts[t] = 1

    # Priority counts
    priority_counts: Dict[str, int] = {k: 0 for k in PRIORITY_METADATA.keys()}
    for s in all_sources:
        p = s.get("priority", "medium")
        if p in priority_counts:
            priority_counts[p] += 1

    return {
        "total_sources": total,
        "active_count": active_count,
        "paused_count": paused_count,
        "error_count": error_count,
        "total_articles": total_articles,
        "type_counts": type_counts,
        "priority_counts": priority_counts,
    }


async def get_source_by_id(source_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieve single source by integer ID."""
    doc = await _repo.find_by_id(source_id, db=db)
    if doc:
        return format_source_display(doc)
    return None


async def create_source(data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Create a new crawler source document."""
    await init_sources_collection(db)

    # Generate new incremental ID
    highest_id = await _repo.get_next_id(db=db)

    # Clean tags
    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
    elif not isinstance(tags, list):
        tags = []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = {
        "id": highest_id,
        "name": (data.get("name") or "").strip(),
        "type": (data.get("type") or "website").strip().lower(),
        "url": (data.get("url") or "").strip(),
        "province": (data.get("province") or "Toàn quốc").strip(),
        "district": (data.get("district") or "").strip(),
        "ward": (data.get("ward") or "").strip(),
        "tags": tags,
        "schedule": data.get("schedule") or "1_hour",
        "priority": data.get("priority") or "medium",
        "status": data.get("status") or "active",
        "ai_prompt": (data.get("ai_prompt") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "last_scanned_at": "Chưa quét",
        "articles_count": 0,
        "success_rate": 100.0,
        "created_at": now_str,
        "updated_at": now_str,
    }

    inserted = await _repo.insert(doc, db=db)
    return format_source_display(inserted)


async def update_source(source_id: int, data: Dict[str, Any], db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Update fields of an existing crawler source."""
    current = await _repo.find_by_id(source_id, db=db)
    if not current:
        return None

    update_payload: Dict[str, Any] = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    allowed_fields = [
        "name", "type", "url", "province", "district", "ward",
        "schedule", "priority", "status", "ai_prompt", "description",
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

    updated = await _repo.update(source_id, update_payload, db=db)
    if updated:
        return format_source_display(updated)
    return None


async def delete_source(source_id: int, db: Optional[Any] = None) -> bool:
    """Delete a source by integer ID."""
    return await _repo.delete(source_id, db=db)


async def toggle_status(source_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Toggle source status between 'active' and 'paused'."""
    src = await _repo.find_by_id(source_id, db=db)
    if not src:
        return None
    new_status = "paused" if src.get("status") == "active" else "active"
    return await update_source(source_id, {"status": new_status}, db=db)


async def trigger_scan(source_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Simulate triggering an instant crawl on this source."""
    src = await _repo.find_by_id(source_id, db=db)
    if not src:
        return None
    new_articles = int(src.get("articles_count", 0)) + 3
    updated_payload = {
        "last_scanned_at": "Vừa xong",
        "articles_count": new_articles,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    updated = await _repo.update(source_id, updated_payload, db=db)
    if updated:
        return format_source_display(updated)
    return None


async def reset_demo_sources(db: Optional[Any] = None) -> int:
    """Reset the sources collection back to the 9 default seed sources."""
    await init_sources_collection(db)
    all_current, _ = await _repo.find_all(db=db)
    for c in all_current:
        await _repo.delete(c["id"], db=db)
    for s in DEFAULT_SOURCES:
        await _repo.insert(dict(s), auto_id=False, db=db)
    return len(DEFAULT_SOURCES)


def get_provinces_dropdown() -> List[Dict[str, Any]]:
    """Load province options from metadata data files or fallback list."""
    provinces_path = Path(__file__).resolve().parent.parent / "metadata" / "data" / "vn_provinces.json"
    if provinces_path.exists():
        try:
            with open(provinces_path, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
                return [
                    {
                        "code": item.get("code", ""),
                        "name": item.get("name", ""),
                        "full_name": item.get("full_name", item.get("name", "")),
                        "type": item.get("type", "Tỉnh"),
                    }
                    for item in raw_list
                ]
        except Exception as exc:
            logger.warning(f"Could not read vn_provinces.json: {exc}")

    # Fallback standard provinces
    return [
        {"code": "01", "name": "Hà Nội", "full_name": "Thành phố Hà Nội", "type": "Thành phố trực thuộc TW"},
        {"code": "79", "name": "Hồ Chí Minh", "full_name": "Thành phố Hồ Chí Minh", "type": "Thành phố trực thuộc TW"},
        {"code": "48", "name": "Đà Nẵng", "full_name": "Thành phố Đà Nẵng", "type": "Thành phố trực thuộc TW"},
        {"code": "31", "name": "Hải Phòng", "full_name": "Thành phố Hải Phòng", "type": "Thành phố trực thuộc TW"},
        {"code": "92", "name": "Cần Thơ", "full_name": "Thành phố Cần Thơ", "type": "Thành phố trực thuộc TW"},
        {"code": "74", "name": "Bình Dương", "full_name": "Tỉnh Bình Dương", "type": "Tỉnh"},
        {"code": "75", "name": "Đồng Nai", "full_name": "Tỉnh Đồng Nai", "type": "Tỉnh"},
        {"code": "56", "name": "Khánh Hòa", "full_name": "Tỉnh Khánh Hòa", "type": "Tỉnh"},
    ]
