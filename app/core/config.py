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
    DESCRIPTION = "Local web multi-tool suite"

    TEMPLATES_DIR = TEMPLATES_DIR
    STATIC_DIR = STATIC_DIR


settings = Settings()


# Registry of tools shown in the sidebar (and on the dashboard grid).
# ``id`` is used to highlight the active link in the sidebar.
TOOLS = [
    {"id": "srt-translator", "name": "SRT Translator", "path": "/tools/srt-translator"},
    # {"id": "tool-2", "name": "Tool 2", "path": "/tools/tool-2"},
]
