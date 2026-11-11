"""Data models and schemas for Crawler Source Management."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceTypeEnum(str, Enum):
    """Standard 9 supported crawler source types."""
    WEBSITE = "website"
    RSS = "rss"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    PDF = "pdf"
    GDRIVE = "gdrive"
    MANUAL = "manual"
    API = "api"


SOURCE_TYPE_METADATA: Dict[str, Dict[str, str]] = {
    "website": {
        "key": "website",
        "label": "Website",
        "sub_label": "Báo điện tử & Cổng tin",
        "icon": "globe",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900",
        "color_class": "text-blue-600 dark:text-blue-400",
        "bg_soft": "bg-blue-50 dark:bg-blue-950/40",
    },
    "rss": {
        "key": "rss",
        "label": "RSS",
        "sub_label": "RSS / Atom Feeds",
        "icon": "rss",
        "badge_color": "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-900",
        "color_class": "text-amber-600 dark:text-amber-400",
        "bg_soft": "bg-amber-50 dark:bg-amber-950/40",
    },
    "facebook": {
        "key": "facebook",
        "label": "Facebook",
        "sub_label": "Fanpage & Group",
        "icon": "facebook",
        "badge_color": "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-900",
        "color_class": "text-indigo-600 dark:text-indigo-400",
        "bg_soft": "bg-indigo-50 dark:bg-indigo-950/40",
    },
    "youtube": {
        "key": "youtube",
        "label": "Youtube",
        "sub_label": "Kênh & Playlist Video",
        "icon": "youtube",
        "badge_color": "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-900",
        "color_class": "text-rose-600 dark:text-rose-400",
        "bg_soft": "bg-rose-50 dark:bg-rose-950/40",
    },
    "tiktok": {
        "key": "tiktok",
        "label": "TikTok",
        "sub_label": "Kênh & Hashtag xu hướng",
        "icon": "video",
        "badge_color": "bg-pink-100 text-pink-700 dark:bg-pink-950/60 dark:text-pink-300 border-pink-200 dark:border-pink-900",
        "color_class": "text-pink-600 dark:text-pink-400",
        "bg_soft": "bg-pink-50 dark:bg-pink-950/40",
    },
    "pdf": {
        "key": "pdf",
        "label": "PDF",
        "sub_label": "Tài liệu & Văn bản pháp quy",
        "icon": "file-text",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900",
        "color_class": "text-emerald-600 dark:text-emerald-400",
        "bg_soft": "bg-emerald-50 dark:bg-emerald-950/40",
    },
    "gdrive": {
        "key": "gdrive",
        "label": "Google Drive",
        "sub_label": "Thư mục chia sẻ Cloud",
        "icon": "hard-drive",
        "badge_color": "bg-yellow-100 text-yellow-800 dark:bg-yellow-950/60 dark:text-yellow-300 border-yellow-200 dark:border-yellow-900",
        "color_class": "text-yellow-600 dark:text-yellow-400",
        "bg_soft": "bg-yellow-50 dark:bg-yellow-950/40",
    },
    "manual": {
        "key": "manual",
        "label": "Manual",
        "sub_label": "Nhập tay & Bài chọn lọc",
        "icon": "pen-tool",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-900",
        "color_class": "text-purple-600 dark:text-purple-400",
        "bg_soft": "bg-purple-50 dark:bg-purple-950/40",
    },
    "api": {
        "key": "api",
        "label": "API",
        "sub_label": "REST API / Webhook JSON",
        "icon": "code-2",
        "badge_color": "bg-cyan-100 text-cyan-700 dark:bg-cyan-950/60 dark:text-cyan-300 border-cyan-200 dark:border-cyan-900",
        "color_class": "text-cyan-600 dark:text-cyan-400",
        "bg_soft": "bg-cyan-50 dark:bg-cyan-950/40",
    },
}

PRIORITY_METADATA: Dict[str, Dict[str, str]] = {
    "urgent": {
        "key": "urgent",
        "label": "Khẩn cấp",
        "badge_color": "bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300 border-red-200 dark:border-red-900",
        "icon": "alert-triangle",
        "rank": 1,
    },
    "high": {
        "key": "high",
        "label": "Cao",
        "badge_color": "bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300 border-orange-200 dark:border-orange-900",
        "icon": "arrow-up",
        "rank": 2,
    },
    "medium": {
        "key": "medium",
        "label": "Trung bình",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900",
        "icon": "minus",
        "rank": 3,
    },
    "low": {
        "key": "low",
        "label": "Thấp",
        "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700",
        "icon": "arrow-down",
        "rank": 4,
    },
}

STATUS_METADATA: Dict[str, Dict[str, str]] = {
    "active": {
        "key": "active",
        "label": "Đang hoạt động",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800",
        "dot_color": "bg-emerald-500",
    },
    "paused": {
        "key": "paused",
        "label": "Tạm dừng",
        "badge_color": "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800",
        "dot_color": "bg-amber-500",
    },
    "error": {
        "key": "error",
        "label": "Lỗi quét",
        "badge_color": "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800",
        "dot_color": "bg-rose-500",
    },
    "pending": {
        "key": "pending",
        "label": "Chờ cấu hình",
        "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700",
        "dot_color": "bg-slate-400",
    },
}

SCHEDULE_OPTIONS: Dict[str, str] = {
    "15_min": "15 phút/lần",
    "30_min": "30 phút/lần",
    "1_hour": "1 giờ/lần",
    "3_hours": "3 giờ/lần",
    "6_hours": "6 giờ/lần",
    "12_hours": "12 giờ/lần",
    "daily": "Hàng ngày (06:00)",
    "weekly": "Hàng tuần",
    "manual": "Quét thủ công",
}


class SourceModel(BaseModel):
    """MongoDB Source Document Model for collection 'crawler_sources'.

    Fields:
        id: Integer ID
        name: Tên nguồn
        type: Loại (website, rss, facebook, youtube, tiktok, pdf, gdrive, manual, api)
        url: Đường dẫn URL / Endpoint / File path
        province: Tỉnh / Thành phố
        district: Huyện / Quận / Thị xã
        ward: Xã / Phường / Thị trấn
        tags: Danh sách nhãn phân loại (tags)
        schedule: Lịch quét định kỳ
        priority: Độ ưu tiên (urgent, high, medium, low)
        status: Trạng thái (active, paused, error, pending)
        ai_prompt: AI Prompt riêng biệt áp dụng cho nguồn này
        description: Ghi chú / Mô tả chi tiết
        last_scanned_at: Thời gian quét lần cuối
        articles_count: Số bài / dữ liệu đã thu thập được
        success_rate: Tỷ lệ cào dữ liệu thành công (%)
        created_at: Ngày tạo
        updated_at: Ngày cập nhật
    """
    id: int
    name: str
    type: str = "website"
    url: str
    province: Optional[str] = "Toàn quốc"
    district: Optional[str] = ""
    ward: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    schedule: str = "1_hour"
    priority: str = "medium"
    status: str = "active"
    ai_prompt: Optional[str] = ""
    description: Optional[str] = ""
    last_scanned_at: Optional[str] = None
    articles_count: int = 0
    success_rate: float = 100.0
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self) -> dict:
        return self.model_dump()


class SourceCreatePayload(BaseModel):
    """Payload to create a new crawler source."""
    name: str
    type: str = "website"
    url: str
    province: Optional[str] = "Toàn quốc"
    district: Optional[str] = ""
    ward: Optional[str] = ""
    tags: Optional[List[str]] = Field(default_factory=list)
    schedule: Optional[str] = "1_hour"
    priority: Optional[str] = "medium"
    status: Optional[str] = "active"
    ai_prompt: Optional[str] = ""
    description: Optional[str] = ""


class SourceUpdatePayload(BaseModel):
    """Payload to update an existing crawler source."""
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    tags: Optional[List[str]] = None
    schedule: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    ai_prompt: Optional[str] = None
    description: Optional[str] = None
