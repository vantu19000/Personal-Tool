"""Application configuration and the tool registry.

Adding a new tool
-----------------
1. Add an entry to :data:`TOOLS` below (it drives the sidebar automatically).
2. Create a sub-package under ``app/tools/<tool_name>/`` with a ``router.py``.
3. Register the router in ``main.py``.
"""
from pathlib import Path

# ``app/`` directory (config.py lives in app/core/config.py -> up two levels)
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


class Settings:
    """App-wide settings (kept simple on purpose — a plain class)."""

    APP_NAME = "Personal Multi-Tool"
    APP_VERSION = "0.1.0"
    DESCRIPTION = "Bộ công cụ mini chạy hoàn toàn trên máy của bạn"

    TEMPLATES_DIR = TEMPLATES_DIR
    STATIC_DIR = STATIC_DIR


settings = Settings()


# Registry of tools shown in the sidebar (and on the dashboard grid).
# ``id`` is used to highlight the active link in the sidebar.
TOOLS = [
    {
        "id": "srt-translator",
        "name": "SRT Translator",
        "path": "/tools/srt-translator",
        "description": "Dịch file SRT tự động bằng AI, hỗ trợ nhiều ngôn ngữ",
        "category": "ai",
        "category_name": "AI",
        "badge": "✦ AI",
        "badge_color": "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300",
        "icon": "file-text",
        "icon_bg": "bg-purple-50 text-purple-600 dark:bg-purple-950/50 dark:text-purple-400",
        "tags": ["SRT", "Translation", "AI"],
    },
    {
        "id": "pdf-to-md",
        "name": "PDF to Markdown",
        "path": "/tools/pdf-to-md",
        "description": "Chuyển đổi file PDF sang Markdown với độ chính xác cao",
        "category": "document",
        "category_name": "Tài liệu",
        "badge": "Tài liệu",
        "badge_color": "bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300",
        "icon": "file-code",
        "icon_bg": "bg-rose-50 text-rose-500 dark:bg-rose-950/50 dark:text-rose-400",
        "tags": ["PDF", "Markdown", "OCR"],
    },
    {
        "id": "slufy",
        "name": "Slufy",
        "path": "/tools/slufy",
        "description": "Chuyển đổi tiêu đề sang Slug URL chuẩn SEO & xử lý văn bản",
        "category": "media",
        "category_name": "Media",
        "badge": "✦ Media",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300",
        "icon": "image",
        "icon_bg": "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400",
        "tags": ["Slug", "SEO", "Optimize"],
    },
    {
        "id": "guid-generator",
        "name": "GUID Generator",
        "path": "/tools/guid-generator",
        "description": "Tạo GUID, UUID với nhiều định dạng khác nhau",
        "category": "utility",
        "category_name": "Tiện ích",
        "badge": "Tiện ích",
        "badge_color": "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300",
        "icon": "code",
        "icon_bg": "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400",
        "tags": ["GUID", "UUID", "Generator"],
    },
    {
        "id": "hash-calculator",
        "name": "Hash Calculator",
        "path": "/tools/hash-calculator",
        "description": "Tính hash cho file hoặc text (MD5, SHA1, SHA256, ...)",
        "category": "text",
        "category_name": "Văn bản",
        "badge": "Văn bản",
        "badge_color": "bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300",
        "icon": "hash",
        "icon_bg": "bg-teal-50 text-teal-600 dark:bg-teal-950/50 dark:text-teal-400",
        "tags": ["Hash", "MD5", "SHA256"],
    },
    {
        "id": "text-counter",
        "name": "Text Counter",
        "path": "/tools/text-counter",
        "description": "Đếm ký tự, từ, dòng trong văn bản thời gian thực",
        "category": "text",
        "category_name": "Văn bản",
        "badge": "Văn bản",
        "badge_color": "bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300",
        "icon": "type",
        "icon_bg": "bg-sky-50 text-sky-600 dark:bg-sky-950/50 dark:text-sky-400",
        "tags": ["Text", "Counter", "Analysis"],
    },
]
