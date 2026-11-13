"""Application configuration and the tool registry.

Adding a new tool
-----------------
1. Add an entry to :data:`TOOLS` below (it drives the sidebar automatically).
2. Create a sub-package under ``app/tools/<tool_name>/`` with a ``router.py``.
3. Register the router in ``main.py``.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ``app/`` directory (config.py lives in app/core/config.py -> up two levels)
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

# Tự động nạp biến môi trường từ .env nếu có
load_dotenv(PROJECT_DIR / ".env")
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


class Settings:
    """App-wide settings (kept simple on purpose — a plain class)."""

    APP_NAME = "Personal Multi-Tool"
    APP_VERSION = "0.1.0"
    DESCRIPTION = "Bộ công cụ mini chạy hoàn toàn trên máy của bạn"

    TEMPLATES_DIR = TEMPLATES_DIR
    STATIC_DIR = STATIC_DIR

    # Server config
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "9981"))

    # Ollama global config (dùng chung cho toàn bộ các chức năng)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT_SECONDS: int = 600  # Mặc định 10 phút (600s)

    # MongoDB Database config (Docker / Local)
    MONGO_HOST: str = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT: int = int(os.getenv("MONGO_PORT", "27017"))
    MONGO_USER: str = os.getenv("MONGO_USER", "root")
    MONGO_PASSWORD: str = os.getenv("MONGO_PASSWORD", "rootpassword")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "personal_tool_db")
    MONGO_AUTH_SOURCE: str = os.getenv("MONGO_AUTH_SOURCE", "admin")

    @property
    def mongodb_uri(self) -> str:
        override = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
        if override:
            return override
        if self.MONGO_USER and self.MONGO_PASSWORD:
            return (
                f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}@"
                f"{self.MONGO_HOST}:{self.MONGO_PORT}/"
                f"{self.MONGO_DB_NAME}?authSource={self.MONGO_AUTH_SOURCE}"
            )
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB_NAME}"


settings = Settings()


def get_ollama_timeout() -> float:
    """Lấy thời gian timeout Ollama dùng chung cho toàn bộ ứng dụng (mặc định 600s ~ 10 phút)."""
    try:
        from app.core import settings_store
        system_cfg = settings_store.get_block("system")
        val = system_cfg.get("ollama_timeout_seconds")
        if val is not None and str(val).isdigit() and int(val) > 0:
            return float(val)
    except Exception:
        pass
    return float(settings.OLLAMA_TIMEOUT_SECONDS)


def get_ollama_base_url() -> str:
    """Lấy địa chỉ Ollama dùng chung cho toàn bộ ứng dụng (mặc định http://localhost:11434)."""
    try:
        from app.core import settings_store
        system_cfg = settings_store.get_block("system")
        url = system_cfg.get("ollama_base_url")
        if url and str(url).strip():
            return str(url).strip().rstrip("/")
    except Exception:
        pass
    return settings.OLLAMA_BASE_URL


# Registry of tools shown in the sidebar (and on the dashboard grid).
# ``id`` is used to highlight the active link in the sidebar.
TOOLS = [
    {
        "id": "content-ideas",
        "name": "AI Content Ideas",
        "path": "/tools/content-ideas",
        "description": "Quét và phân tích ý tưởng nội dung xu hướng trên mạng bằng AI, tổng hợp theo địa phương, chủ đề và radar trending",
        "category": "ai",
        "category_name": "AI",
        "badge": "✦ Mới",
        "badge_color": "bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300",
        "icon": "sparkles",
        "icon_bg": "bg-violet-50 text-violet-600 dark:bg-violet-950/50 dark:text-violet-400",
        "tags": ["AI", "Content", "Scan", "Trending", "Radar"],
    },
    {
        "id": "image-to-prompt",
        "name": "Image to Prompt",
        "path": "/tools/image-to-prompt",
        "description": "Dịch ngược ảnh thành prompt tạo ảnh AI (Gemini, ChatGPT, DALL-E 3) qua Ollama",
        "category": "ai",
        "category_name": "AI",
        "badge": "✦ Vision AI",
        "badge_color": "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950/60 dark:text-fuchsia-300",
        "icon": "sparkles",
        "icon_bg": "bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-950/50 dark:text-fuchsia-400",
        "tags": ["Image", "Prompt", "Vision", "Gemini", "ChatGPT"],
    },
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
        "id": "image-compressor",
        "name": "Nén Ảnh",
        "path": "/tools/image-compressor",
        "description": "Nén ảnh tối ưu dung lượng hàng loạt hoặc theo thư mục, tự động sao lưu ảnh gốc",
        "category": "media",
        "category_name": "Media",
        "badge": "✦ Nén ảnh",
        "badge_color": "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300",
        "icon": "minimize-2",
        "icon_bg": "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400",
        "tags": ["Image", "Compress", "Optimize", "Backup"],
    },
    {
        "id": "image-metadata",
        "name": "Metadata Ảnh",
        "path": "/tools/image-metadata",
        "description": "Chỉnh sửa tiêu đề, mô tả, tác giả, bản quyền, ngày chụp và vị trí GPS kèm bản đồ tương tác",
        "category": "media",
        "category_name": "Media",
        "badge": "✦ EXIF / GPS",
        "badge_color": "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300",
        "icon": "map-pin",
        "icon_bg": "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400",
        "tags": ["Image", "Metadata", "EXIF", "GPS", "Location"],
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
