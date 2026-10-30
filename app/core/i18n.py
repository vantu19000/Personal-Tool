"""Internationalization (i18n) engine for Personal-Tool.

Features:
- Thread-safe and async-safe locale management via contextvars.
- JSON-based translation dictionaries located at ``app/locales/<locale>.json``.
- Default language: Vietnamese (vi).
- Fallback chain: requested language -> default language (vi) -> default string -> key.
- Safe string formatting with keyword arguments.
"""
from __future__ import annotations

import contextvars
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import BASE_DIR

LOCALES_DIR = BASE_DIR / "locales"
DEFAULT_LOCALE = "vi"
COOKIE_NAME = "app_lang"

# Context variable tracking current request's locale.
_current_locale: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_locale", default=DEFAULT_LOCALE
)

# In-memory dictionary cache for translations: { "vi": {...}, "en": {...} }
_translations: Dict[str, Dict[str, Any]] = {}
_supported_locales: Dict[str, Dict[str, str]] = {}


def load_translations() -> None:
    """Load all JSON translation files from ``app/locales/``."""
    global _translations, _supported_locales
    loaded_translations: Dict[str, Dict[str, Any]] = {}
    supported: Dict[str, Dict[str, str]] = {}

    if LOCALES_DIR.is_dir():
        for file in LOCALES_DIR.glob("*.json"):
            code = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded_translations[code] = data
                    meta = data.get("meta", {})
                    supported[code] = {
                        "code": code,
                        "name": meta.get("name", code.upper()),
                        "flag": meta.get("flag", "🌐"),
                    }
            except Exception as e:
                # Log or keep default
                print(f"[i18n] Failed to load {file}: {e}")

    # Fallback to vi / en if directory missing
    if "vi" not in supported:
        supported["vi"] = {"code": "vi", "name": "Tiếng Việt", "flag": "🇻🇳"}
    if "en" not in supported:
        supported["en"] = {"code": "en", "name": "English", "flag": "🇺🇸"}

    _translations = loaded_translations
    _supported_locales = supported


# Initialize on import
load_translations()


def get_supported_locales() -> List[Dict[str, str]]:
    """Return list of supported locales with code, name and flag."""
    if not _supported_locales:
        load_translations()
    return list(_supported_locales.values())


def is_locale_supported(locale: str | None) -> bool:
    """Check if the given locale code is supported."""
    if not locale:
        return False
    return locale.lower() in _supported_locales


def get_current_locale() -> str:
    """Get the active locale from contextvar, defaulting to DEFAULT_LOCALE."""
    return _current_locale.get()


def set_current_locale(locale: str) -> None:
    """Set the active locale for the current context."""
    if is_locale_supported(locale):
        _current_locale.set(locale)
    else:
        _current_locale.set(DEFAULT_LOCALE)


def _resolve_nested_key(data: Dict[str, Any], key_path: str) -> Optional[str]:
    """Traverse nested dictionary by dot notation (e.g. 'topbar.search')."""
    parts = key_path.split(".")
    curr: Any = data
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            return None
    return curr if isinstance(curr, str) else None


def translate(
    key: str,
    locale: Optional[str] = None,
    default: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Translate a translation key with optional interpolation.

    Lookup hierarchy:
    1. Requested locale dictionary (or current context locale)
    2. Default locale (vi) dictionary
    3. Explicit default parameter (if supplied)
    4. Original key
    """
    lang = locale or get_current_locale()
    if lang not in _translations:
        lang = DEFAULT_LOCALE

    # 1. Lookup in selected language
    result: Optional[str] = None
    if lang in _translations:
        result = _resolve_nested_key(_translations[lang], key)

    # 2. Fallback to default locale (vi) if missing
    if result is None and lang != DEFAULT_LOCALE and DEFAULT_LOCALE in _translations:
        result = _resolve_nested_key(_translations[DEFAULT_LOCALE], key)

    # 3. Fallback to explicit default
    if result is None:
        result = default if default is not None else key

    # Interpolate formatted variables safely
    if kwargs:
        try:
            return result.format(**kwargs)
        except Exception:
            return result

    return result


# Short alias
t = translate
