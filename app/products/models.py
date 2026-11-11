"""Data models and schemas for My Products & Publishing Channels Management (Quản lý Sản phẩm / Kênh phân phối)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PlatformTypeEnum(str, Enum):
    """Supported product platforms / publishing channels."""
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    WEB_BLOG = "web_blog"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    THREADS = "threads"
    TWITTER_X = "twitter_x"
    LINKEDIN = "linkedin"
    PODCAST = "podcast"
    OTHER = "other"


PLATFORM_METADATA: Dict[str, Dict[str, str]] = {
    "youtube": {
        "key": "youtube",
        "label": "YouTube",
        "sub_label": "Kênh Video & Shorts",
        "icon": "youtube",
        "badge_color": "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-900",
        "color_class": "text-rose-600 dark:text-rose-400",
        "bg_soft": "bg-rose-50 dark:bg-rose-950/40",
        "default_format": "Video dài (>8p) & YouTube Shorts (<60s)",
    },
    "tiktok": {
        "key": "tiktok",
        "label": "TikTok",
        "sub_label": "Kênh Video ngắn & Trend",
        "icon": "video",
        "badge_color": "bg-pink-100 text-pink-700 dark:bg-pink-950/60 dark:text-pink-300 border-pink-200 dark:border-pink-900",
        "color_class": "text-pink-600 dark:text-pink-400",
        "bg_soft": "bg-pink-50 dark:bg-pink-950/40",
        "default_format": "Video ngắn dọc (9:16, 30s-60s)",
    },
    "web_blog": {
        "key": "web_blog",
        "label": "Web Blog",
        "sub_label": "Website & Blog SEO",
        "icon": "globe",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900",
        "color_class": "text-blue-600 dark:text-blue-400",
        "bg_soft": "bg-blue-50 dark:bg-blue-950/40",
        "default_format": "Bài viết chuẩn SEO (1200 - 2500 từ)",
    },
    "facebook": {
        "key": "facebook",
        "label": "Facebook",
        "sub_label": "Fanpage & Group cộng đồng",
        "icon": "facebook",
        "badge_color": "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-900",
        "color_class": "text-indigo-600 dark:text-indigo-400",
        "bg_soft": "bg-indigo-50 dark:bg-indigo-950/40",
        "default_format": "Post ảnh / Carousel + Caption dài thảo luận",
    },
    "instagram": {
        "key": "instagram",
        "label": "Instagram",
        "sub_label": "Reels & Visual Feed",
        "icon": "instagram",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-900",
        "color_class": "text-purple-600 dark:text-purple-400",
        "bg_soft": "bg-purple-50 dark:bg-purple-950/40",
        "default_format": "Carousel 10 slide & Reels ngắn",
    },
    "pinterest": {
        "key": "pinterest",
        "label": "Pinterest",
        "sub_label": "Ghim ảnh & Ý tưởng thiết kế",
        "icon": "pin",
        "badge_color": "bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300 border-red-200 dark:border-red-900",
        "color_class": "text-red-600 dark:text-red-400",
        "bg_soft": "bg-red-50 dark:bg-red-950/40",
        "default_format": "Infographic dọc (2:3) & Idea Pins",
    },
    "threads": {
        "key": "threads",
        "label": "Threads",
        "sub_label": "Micro-blogging ngắn",
        "icon": "message-circle",
        "badge_color": "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border-slate-300 dark:border-slate-700",
        "color_class": "text-slate-700 dark:text-slate-300",
        "bg_soft": "bg-slate-100 dark:bg-slate-900/60",
        "default_format": "Chuỗi Thread ngắn (1-5 post liên kết)",
    },
    "twitter_x": {
        "key": "twitter_x",
        "label": "X (Twitter)",
        "sub_label": "Tin nhanh & Threads",
        "icon": "hash",
        "badge_color": "bg-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100 border-zinc-300 dark:border-zinc-700",
        "color_class": "text-zinc-800 dark:text-zinc-200",
        "bg_soft": "bg-zinc-100 dark:bg-zinc-900/60",
        "default_format": "Thread phân tích súc tích + hình minh họa",
    },
    "linkedin": {
        "key": "linkedin",
        "label": "LinkedIn",
        "sub_label": "Mạng chuyên gia B2B",
        "icon": "linkedin",
        "badge_color": "bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-900",
        "color_class": "text-sky-600 dark:text-sky-400",
        "bg_soft": "bg-sky-50 dark:bg-sky-950/40",
        "default_format": "Bài viết phân tích chuyên sâu + Case Study",
    },
    "podcast": {
        "key": "podcast",
        "label": "Podcast",
        "sub_label": "Audio & Spotify/Apple",
        "icon": "mic",
        "badge_color": "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-900",
        "color_class": "text-amber-600 dark:text-amber-400",
        "bg_soft": "bg-amber-50 dark:bg-amber-950/40",
        "default_format": "Audio tập 15-45 phút + kịch bản hội thoại",
    },
    "other": {
        "key": "other",
        "label": "Khác",
        "sub_label": "Sản phẩm / Kênh tùy biến",
        "icon": "box",
        "badge_color": "bg-teal-100 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 border-teal-200 dark:border-teal-900",
        "color_class": "text-teal-600 dark:text-teal-400",
        "bg_soft": "bg-teal-50 dark:bg-teal-950/40",
        "default_format": "Định dạng tùy chọn",
    },
}

PRODUCT_STATUS_METADATA: Dict[str, Dict[str, str]] = {
    "active": {
        "key": "active",
        "label": "Đang hoạt động",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800",
        "dot_color": "bg-emerald-500",
    },
    "paused": {
        "key": "paused",
        "label": "Tạm dừng sản xuất",
        "badge_color": "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800",
        "dot_color": "bg-amber-500",
    },
    "planning": {
        "key": "planning",
        "label": "Đang lên kế hoạch",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800",
        "dot_color": "bg-blue-500",
    },
    "archived": {
        "key": "archived",
        "label": "Đã lưu trữ",
        "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700",
        "dot_color": "bg-slate-400",
    },
}


class ProductModel(BaseModel):
    """MongoDB Document Model for collection 'my_products'.

    Represents a specific product, distribution channel, brand, or publishing property owned by the user.

    Fields:
        id: Integer unique ID
        name: Tên sản phẩm / Tên kênh (e.g. 'Kênh YouTube BĐS Thủ Đô')
        platform: Loại nền tảng (youtube, tiktok, web_blog, instagram, pinterest, facebook, threads, twitter_x, linkedin, podcast, other)
        code: Mã định danh ngắn / slug (e.g. 'yt-bds-thudo')
        url: Đường dẫn URL / Handle kênh (e.g. 'https://youtube.com/@bdsthudo')
        niche: Chủ đề / Ngách nội dung (e.g. 'Bất động sản & Quy hoạch')
        target_audience: Đối tượng độc giả / khách hàng mục tiêu (e.g. 'Nhà đầu tư cá nhân 28-50 tuổi')
        content_format: Định dạng nội dung chủ đạo (e.g. 'Video phân tích 10-15 phút + Shorts')
        posting_frequency: Kế hoạch / Tần suất đăng (e.g. '3 video/tuần')
        brand_voice: Tone giọng & phong cách (e.g. 'Chuyên nghiệp, tin cậy, khách quan')
        ai_system_prompt: AI Prompt riêng định hướng sáng tạo content cho kênh này
        tags: Danh sách tags phân loại
        status: Trạng thái (active, paused, planning, archived)
        followers_metric: Số lượt theo dõi / sub (e.g. '45.2K Subscribers')
        assigned_ideas_count: Số ý tưởng đã gán cho kênh này
        published_content_count: Số bài / video đã xuất bản thành công
        last_published_at: Lần xuất bản gần nhất
        description: Ghi chú / Mục tiêu phát triển kênh
        created_at: Ngày tạo
        updated_at: Ngày cập nhật
    """
    id: int
    name: str
    platform: str = "youtube"
    code: Optional[str] = ""
    url: Optional[str] = ""
    niche: Optional[str] = "Chung"
    target_audience: Optional[str] = ""
    content_format: Optional[str] = ""
    posting_frequency: Optional[str] = "Hàng tuần"
    brand_voice: Optional[str] = ""
    ai_system_prompt: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    status: str = "active"
    followers_metric: Optional[str] = ""
    assigned_ideas_count: int = 0
    published_content_count: int = 0
    last_published_at: Optional[str] = None
    description: Optional[str] = ""
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self) -> dict:
        return self.model_dump()


class ProductCreatePayload(BaseModel):
    name: str
    platform: str = "youtube"
    code: Optional[str] = ""
    url: Optional[str] = ""
    niche: Optional[str] = "Chung"
    target_audience: Optional[str] = ""
    content_format: Optional[str] = ""
    posting_frequency: Optional[str] = "Hàng tuần"
    brand_voice: Optional[str] = ""
    ai_system_prompt: Optional[str] = ""
    tags: Optional[List[str]] = Field(default_factory=list)
    status: Optional[str] = "active"
    followers_metric: Optional[str] = ""
    description: Optional[str] = ""


class ProductUpdatePayload(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    code: Optional[str] = None
    url: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    content_format: Optional[str] = None
    posting_frequency: Optional[str] = None
    brand_voice: Optional[str] = None
    ai_system_prompt: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    followers_metric: Optional[str] = None
    description: Optional[str] = None
