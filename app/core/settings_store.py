"""Persistent, block-based settings store (JSON on disk).

Design
------
Each tool owns its own *block* of settings. A block is described by metadata
(a display title/description, a Pydantic model for validation, and a list of
renderable fields) in :data:`BLOCKS`. Both the settings router and the
``settings.html`` template render/collect blocks *dynamically* from this
registry — so adding a new tool's configuration is a one-file change here and
requires **no** new route or template.

Settings are stored as a single JSON document at :data:`SETTINGS_FILE`, grouped
by block id::

    {
        "system":        {"home_title": "...", "home_description": "..."},
        "srt_translator": {"system_prompt": "..."}
    }
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Type

from pydantic import BaseModel, Field, ValidationError

from app.core.config import BASE_DIR

# ``app/core/settings_store.py`` -> app/ -> ``app/data`` (git-ignored, local only)
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"


# ---------------------------------------------------------------------------
# Field / block metadata (drives the settings page automatically)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldDef:
    """Metadata for one renderable settings field.

    ``kind`` is one of ``"text" | "textarea" | "number"``. ``placeholder`` /
    ``help_text`` are surfaced in the UI.
    """

    key: str
    label: str
    kind: str = "text"
    placeholder: str = ""
    help_text: str = ""


@dataclass
class BlockDef:
    """A single tool's configuration block."""

    id: str
    title: str
    description: str
    model: Type[BaseModel]
    default: Dict[str, Any]
    fields: List[FieldDef] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pydantic models (validation) for each block
# ---------------------------------------------------------------------------


class SystemSettings(BaseModel):
    """App-wide settings block (homepage title + description)."""

    home_title: str = Field(..., max_length=300)
    home_description: str = Field(..., max_length=1000)


class PdfToMdSettings(BaseModel):
    """PDF → Markdown settings block (chunking size)."""

    pages_per_file: int = Field(10, ge=1, le=500)


class SRTSettings(BaseModel):
    """SRT Translator settings block (the model's system prompt).

    The prompt may contain the literal placeholder ``{target_language}`` which
    is substituted with the chosen target language per request.
    """

    system_prompt: str = Field(..., min_length=5, max_length=8000)


# Default SRT prompt — kept in sync with the historical built-in prompt.
DEFAULT_SRT_PROMPT = (
    "Bạn là trình dịch phụ đề chuyên dụng. "
    "Chỉ dịch giá trị 'text' sang {target_language}. "
    "Giữ nguyên cấu trúc JSON và id, không giải thích, "
    "không thêm lời chào, không bọc markdown thừa. "
    "Trả về DUY NHẤT một mảng JSON gồm các đối tượng "
    '{"id": <số nguyên>, "text": "<bản dịch>"} — id giữ nguyên, '
    "trật tự giữ nguyên, số lượng phần tử bằng với đầu vào."
)


# ---------------------------------------------------------------------------
# Block registry — ADD A NEW TOOL'S CONFIG BLOCK HERE
# ---------------------------------------------------------------------------

BLOCKS: Dict[str, BlockDef] = {
    "system": BlockDef(
        id="system",
        title="System",
        description="Cấu hình chung của ứng dụng (trang chủ).",
        model=SystemSettings,
        default={
            "home_title": "Chào mừng đến với Personal Multi-Tool 👋",
            "home_description": (
                "Bộ công cụ web chạy local. Chọn một tool từ sidebar bên "
                "trái để bắt đầu."
            ),
        },
        fields=[
            FieldDef(
                key="home_title",
                label="Tiêu đề trang chủ",
                kind="text",
                placeholder="Tiêu đề hiển thị ở đầu trang chủ",
            ),
            FieldDef(
                key="home_description",
                label="Mô tả trang chủ",
                kind="textarea",
                placeholder="Mô tả ngắn gọn của trang chủ",
            ),
        ],
    ),
    "srt_translator": BlockDef(
        id="srt_translator",
        title="SRT Translator",
        description="Cấu hình cho tool dịch phụ đề .srt.",
        model=SRTSettings,
        default={"system_prompt": DEFAULT_SRT_PROMPT},
        fields=[
            FieldDef(
                key="system_prompt",
                label="System prompt dịch",
                kind="textarea",
                placeholder="{target_language}",
                help_text=(
                    "Prompt gửi cho model Ollama. Dùng {target_language} để "
                    "điền ngôn ngữ đích (được thay tự động khi dịch)."
                ),
            ),
        ],
    ),
    "pdf_to_md": BlockDef(
        id="pdf_to_md",
        title="PDF to Markdown",
        description="Cấu hình cho tool chuyển PDF text-based sang Markdown.",
        model=PdfToMdSettings,
        default={"pages_per_file": 10},
        fields=[
            FieldDef(
                key="pages_per_file",
                label="Số trang mỗi file Markdown",
                kind="number",
                placeholder="10",
                help_text=(
                    "Mỗi file .md sẽ chứa tối đa số trang này (từ 1 đến 500). "
                    "PDF dài hơn sẽ được tách thành nhiều file/zip."
                ),
            ),
        ],
    ),
}


class SettingsValidationError(ValueError):
    """Raised when submitted settings fail Pydantic validation."""


def _default_data() -> Dict[str, Dict[str, Any]]:
    """Fresh defaults for every registered block."""
    return {block_id: copy.deepcopy(block.default) for block_id, block in BLOCKS.items()}


def _merge_over_defaults(
    defaults: Dict[str, Dict[str, Any]], raw: Any
) -> Dict[str, Dict[str, Any]]:
    """Merge persisted values over defaults.

    Only keys that exist in the current registry are kept, so stale/removed
    fields from an older settings file never leak into the schema.
    """
    merged = copy.deepcopy(defaults)
    if not isinstance(raw, dict):
        return merged
    for block_id, block_vals in raw.items():
        if block_id not in merged or not isinstance(block_vals, dict):
            continue
        for key, value in block_vals.items():
            if key in merged[block_id]:
                merged[block_id][key] = value
    return merged


class SettingsStore:
    """Thread-safe in-memory + on-disk settings store."""

    def __init__(self, path: Path = SETTINGS_FILE) -> None:
        self._path = path
        self._lock = RLock()
        self._data = self._load()

    # -- internal ----------------------------------------------------------
    def _load(self) -> Dict[str, Dict[str, Any]]:
        defaults = _default_data()
        if not self._path.exists():
            return defaults
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return defaults
        return _merge_over_defaults(defaults, raw)

    def _persist(self) -> None:
        """Atomic write (temp file + rename) so a crash never corrupts the file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self._path)

    # -- public API --------------------------------------------------------
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._data)

    def get_block(self, block_id: str) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data.get(block_id, {}))

    def get_field(self, block_id: str, key: str, default: Any = None) -> Any:
        with self._lock:
            value = self._data.get(block_id, {}).get(key)
            return default if value is None else value

    def save_blocks(
        self, blocks: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Validate + persist a partial update (block_id -> {field: value}).

        Unknown blocks / fields are ignored. Returns the full stored state.
        Raises :class:`SettingsValidationError` on invalid input.
        """
        with self._lock:
            for block_id, values in (blocks or {}).items():
                block = BLOCKS.get(block_id)
                if block is None or not isinstance(values, dict):
                    continue
                valid_keys = set(block.model.model_fields.keys())
                candidate = {
                    k: v
                    for k, v in self._data.get(block_id, {}).items()
                    if k in valid_keys
                }
                candidate.update({k: v for k, v in values.items() if k in valid_keys})
                try:
                    validated = block.model.model_validate(candidate)
                except ValidationError as exc:
                    raise SettingsValidationError(str(exc)) from exc
                self._data[block_id] = validated.model_dump()
            self._persist()
            return copy.deepcopy(self._data)

    def reset(self) -> Dict[str, Dict[str, Any]]:
        """Restore every block to its defaults and persist."""
        with self._lock:
            self._data = _default_data()
            self._persist()
            return copy.deepcopy(self._data)


# Application-wide singleton.
settings_store = SettingsStore()


# ---------------------------------------------------------------------------
# Module-level convenience functions — stable public API.
#
# These delegate to the singleton above so callers can simply do:
#     from app.core import settings_store
#     settings_store.get_field("srt_translator", "system_prompt")
# without caring about the instance.
# ---------------------------------------------------------------------------


def get_all() -> Dict[str, Dict[str, Any]]:
    """Return the full effective settings state (defaults + user overrides)."""
    return settings_store.get_all()


def get_block(block_id: str) -> Dict[str, Any]:
    """Return the effective settings dict for a single block."""
    return settings_store.get_block(block_id)


def get_field(block_id: str, key: str, default: Any = None) -> Any:
    """Return one effective field value (defaults + user overrides)."""
    return settings_store.get_field(block_id, key, default)


def save_blocks(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Persist user overrides (full replace) and return the new state."""
    return settings_store.save_blocks(payload)


def reset() -> Dict[str, Dict[str, Any]]:
    """Delete the user overrides file and return the fresh default state."""
    return settings_store.reset()
