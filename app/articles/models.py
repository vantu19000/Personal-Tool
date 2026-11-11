"""Data models and schemas for Crawled Articles Management (Kho Bài Viết Thu Thập)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


SENTIMENT_METADATA: Dict[str, Dict[str, str]] = {
    "Tích cực": {
        "label": "Tích cực",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800",
        "dot_color": "bg-emerald-500",
    },
    "Sôi nổi": {
        "label": "Sôi nổi",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800",
        "dot_color": "bg-blue-500",
    },
    "Bình yên": {
        "label": "Bình yên",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800",
        "dot_color": "bg-purple-500",
    },
    "Trung lập": {
        "label": "Trung lập",
        "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700",
        "dot_color": "bg-slate-400",
    },
    "Cảnh báo": {
        "label": "Cảnh báo",
        "badge_color": "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800",
        "dot_color": "bg-amber-500",
    },
    "Tiêu cực": {
        "label": "Tiêu cực",
        "badge_color": "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800",
        "dot_color": "bg-rose-500",
    },
}

ARTICLE_STATUS_METADATA: Dict[str, Dict[str, str]] = {
    "new": {
        "label": "Mới thu thập",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800",
    },
    "has_idea": {
        "label": "Đã tạo ý tưởng",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800",
    },
    "processed": {
        "label": "Đã xử lý AI",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800",
    },
    "archived": {
        "label": "Đã lưu trữ",
        "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700",
    },
}


class CrawledArticleModel(BaseModel):
    """MongoDB Document Model for collection 'crawled_articles'.

    Fields:
        id: Integer unique ID
        title: Tiêu đề bài viết / video / tin tức
        summary: Tóm tắt nội dung
        content: Nội dung đầy đủ hoặc transcript
        url: Link gốc bài viết
        source: Tên nguồn thu thập (VnExpress, Tuổi Trẻ, TikTok, VTV24...)
        source_id: ID của nguồn cấu hình trong crawler_sources
        source_type: Loại nguồn (website, rss, facebook, youtube, tiktok, pdf, gdrive, manual, api)
        source_icon: Icon biểu tượng của nguồn (globe, video, rss, facebook...)
        author: Tác giả / Kênh xuất bản
        location: Địa bàn / Tỉnh thành
        category: Chuyên mục (Công nghệ & AI, Bất động sản, E-Commerce, Đời sống...)
        tags: Danh sách thẻ nhãn phân loại
        sentiment: Sắc thái cảm xúc (Tích cực, Sôi nổi, Trung lập, Cảnh báo...)
        viral_potential: Điểm tiềm năng viral (0-100)
        has_ai_idea: Đã được chuyển đổi thành ý tưởng AI hay chưa
        target_product_id: ID sản phẩm / kênh của tôi được gán (tuỳ chọn)
        target_product_name: Tên sản phẩm / kênh của tôi được gán
        status: Trạng thái (new, has_idea, processed, archived)
        crawled_at: Thời điểm cào dữ liệu (e.g. '15 phút trước', 'Hôm nay lúc 14:20')
        created_at: Ngày tạo bản ghi
        updated_at: Ngày cập nhật
    """
    id: int
    title: str
    summary: str
    content: Optional[str] = ""
    url: Optional[str] = ""
    source: str = "Website"
    source_id: Optional[int] = None
    source_type: str = "website"
    source_icon: Optional[str] = "globe"
    author: Optional[str] = ""
    location: Optional[str] = "Toàn quốc"
    category: str = "Tổng hợp"
    tags: List[str] = Field(default_factory=list)
    sentiment: str = "Tích cực"
    viral_potential: int = 80
    has_ai_idea: bool = False
    target_product_id: Optional[int] = None
    target_product_name: Optional[str] = None
    status: str = "new"
    crawled_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self) -> dict:
        return self.model_dump()


class ArticleCreatePayload(BaseModel):
    title: str
    summary: str
    content: Optional[str] = ""
    url: Optional[str] = ""
    source: Optional[str] = "Website"
    source_type: Optional[str] = "website"
    location: Optional[str] = "Toàn quốc"
    category: Optional[str] = "Tổng hợp"
    tags: Optional[List[str]] = Field(default_factory=list)
    sentiment: Optional[str] = "Tích cực"
    viral_potential: Optional[int] = 80
    target_product_id: Optional[int] = None
    target_product_name: Optional[str] = None
    status: Optional[str] = "new"


class ArticleUpdatePayload(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    sentiment: Optional[str] = None
    viral_potential: Optional[int] = None
    has_ai_idea: Optional[bool] = None
    target_product_id: Optional[int] = None
    target_product_name: Optional[str] = None
    status: Optional[str] = None
