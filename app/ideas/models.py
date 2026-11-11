"""Data models and schemas for AI Ideas Management (Kho Ý Tưởng AI từ Database)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


IDEA_STATUS_METADATA: Dict[str, Dict[str, str]] = {
    "ready": {
        "label": "Sẵn sàng viết",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800",
        "dot_color": "bg-emerald-500",
    },
    "drafting": {
        "label": "Đang viết nháp",
        "badge_color": "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800",
        "dot_color": "bg-amber-500",
    },
    "reviewing": {
        "label": "Chờ duyệt",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800",
        "dot_color": "bg-blue-500",
    },
    "published": {
        "label": "Đã xuất bản",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800",
        "dot_color": "bg-purple-500",
    },
    "archived": {
        "label": "Đã lưu trữ",
        "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700",
        "dot_color": "bg-slate-400",
    },
}

RECOMMENDED_FORMATS: List[Dict[str, str]] = [
    {"value": "Bài viết dài (Blog / Website)", "label": "Bài viết dài (Blog / Website)", "icon": "file-text"},
    {"value": "Video ngắn (TikTok / Shorts / Reels)", "label": "Video ngắn (TikTok / Shorts / Reels)", "icon": "video"},
    {"value": "Infographic Carousel (Fanpage / Threads)", "label": "Infographic Carousel (Fanpage / Threads)", "icon": "images"},
    {"value": "Video dài (YouTube 10-15 phút)", "label": "Video dài (YouTube 10-15 phút)", "icon": "youtube"},
    {"value": "Kịch bản Livestream / Podcast", "label": "Kịch bản Livestream / Podcast", "icon": "mic"},
    {"value": "Bản tin Email (Newsletter)", "label": "Bản tin Email (Newsletter)", "icon": "mail"},
]


class AIIdeaModel(BaseModel):
    """MongoDB Document Model for collection 'ai_ideas'.

    Fields:
        id: Integer unique ID
        title: Tiêu đề ý tưởng do AI gợi ý (hút click, đúng trọng tâm)
        angle: Góc khai thác nội dung độc đáo (Angle)
        target_audience: Đối tượng độc giả mục tiêu
        recommended_format: Định dạng bài đề xuất (Blog, TikTok, Carousel...)
        viral_score: Điểm dự đoán tiềm năng viral (0-100)
        status: Trạng thái (ready, drafting, reviewing, published, archived)
        keywords: Danh sách từ khóa hoặc hashtag gợi ý
        outline: Dàn ý chi tiết bài viết (Heading 2, Heading 3, Key takeaways)
        source_article_id: ID bài viết thu thập gốc (nếu trích xuất từ bài cào)
        source_article: Tên bài viết hoặc nguồn cào gốc
        target_product_id: ID sản phẩm / kênh xuất bản của người dùng
        target_product_name: Tên sản phẩm / kênh xuất bản
        target_platform: Nền tảng (youtube, tiktok, blog, facebook, instagram, pinterest...)
        ai_prompt_used: Prompt hoặc mô hình AI đã tạo ra ý tưởng này
        notes: Ghi chú cá nhân của người biên tập
        created_at: Ngày tạo
        updated_at: Ngày cập nhật
    """

    id: int
    title: str
    angle: str = ""
    target_audience: str = ""
    recommended_format: str = "Bài viết dài (Blog / Website)"
    viral_score: int = Field(default=80, ge=0, le=100)
    status: str = "ready"
    keywords: List[str] = Field(default_factory=list)
    outline: Optional[str] = ""
    source_article_id: Optional[int] = None
    source_article: Optional[str] = ""
    target_product_id: Optional[int] = None
    target_product_name: Optional[str] = ""
    target_platform: Optional[str] = ""
    ai_prompt_used: Optional[str] = ""
    notes: Optional[str] = ""
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_mongo_doc(self) -> Dict[str, Any]:
        """Convert pydantic model to MongoDB document dict."""
        return self.model_dump()


class AIIdeaCreateSchema(BaseModel):
    """Schema for creating a new AI idea."""

    title: str
    angle: Optional[str] = ""
    target_audience: Optional[str] = ""
    recommended_format: Optional[str] = "Bài viết dài (Blog / Website)"
    viral_score: int = Field(default=85, ge=0, le=100)
    status: str = "ready"
    keywords: Any = Field(default_factory=list)
    outline: Optional[str] = ""
    source_article_id: Optional[int] = None
    source_article: Optional[str] = ""
    target_product_id: Optional[int] = None
    target_product_name: Optional[str] = ""
    target_platform: Optional[str] = ""
    ai_prompt_used: Optional[str] = ""
    notes: Optional[str] = ""


class AIIdeaUpdateSchema(BaseModel):
    """Schema for updating an existing AI idea."""

    title: Optional[str] = None
    angle: Optional[str] = None
    target_audience: Optional[str] = None
    recommended_format: Optional[str] = None
    viral_score: Optional[int] = None
    status: Optional[str] = None
    keywords: Optional[Any] = None
    outline: Optional[str] = None
    source_article_id: Optional[int] = None
    source_article: Optional[str] = None
    target_product_id: Optional[int] = None
    target_product_name: Optional[str] = None
    target_platform: Optional[str] = None
    notes: Optional[str] = None
