"""Core service: SRT translation via local Ollama.

Pipeline
--------
1. Scan a source directory (recursive or flat) for ``.srt`` files.
2. Split each subtitle's entries into chunks (default 32) so the model's
   context window is never exceeded.
3. Send each chunk as a JSON array ``[{"id": 1, "text": "..."}, ...]``
   to Ollama (``POST /api/chat``) with a strict system prompt.
4. Parse the response back (with markdown-fence / bracket fallbacks),
   validate that every id round-tripped, and merge the translations
   onto the original ``pysrt`` objects.
5. Save each file as ``<name>.<target_code>.srt`` under the dest dir
   (sub-directory structure is mirrored).

CLI test (requires a running Ollama)::

    .venv\\Scripts\\python -m app.tools.srt_translator.services \
        .\\subs_src .\\subs_out --model translategemma:4b --target-code vi
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import aiohttp
import pysrt

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "translategemma:4b"
DEFAULT_CHUNK_SIZE = 32  # 30-40 entries/chunk keeps the context window safe
DEFAULT_MAX_RETRIES = 2
DEFAULT_TIMEOUT_SECONDS = 600.0

# Strict system prompt — the model must ONLY return the JSON array.
SYSTEM_PROMPT_TEMPLATE = (
    "Bạn là trình dịch phụ đề chuyên dụng. "
    "Chỉ dịch giá trị 'text' sang {target_language}. "
    "Giữ nguyên cấu trúc JSON và id, không giải thích, "
    "không thêm lời chào, không bọc markdown thừa. "
    "Trả về DUY NHẤT một mảng JSON gồm các đối tượng "
    '{{"id": <số nguyên>, "text": "<bản dịch>"}} — id giữ nguyên, '
    "trật tự giữ nguyên, số lượng phần tử bằng với đầu vào."
)

# Markdown fence fallback: ```json [...] ``` / ``` [...] ```
_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(\[.*?\]|\{.*?\})\s*```", re.DOTALL)

ProgressCallback = Callable[[str, int, int], None]  # (stage, current, total)


class SRTTranslationError(RuntimeError):
    """Base error for the translation pipeline."""


class SRTFormatError(SRTTranslationError):
    """The model returned a payload that could not be parsed/validated."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class TranslationConfig:
    """Runtime knobs for a translation run."""

    base_url: str = DEFAULT_OLLAMA_BASE_URL
    model: str = DEFAULT_MODEL
    target_language: str = "tiếng Việt"
    target_code: str = "vi"  # used for the output filename suffix
    chunk_size: int = DEFAULT_CHUNK_SIZE
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    temperature: float = 0.2

    def __post_init__(self) -> None:
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")


# ---------------------------------------------------------------------------
# 0. Ollama model discovery (used by the web UI)
# ---------------------------------------------------------------------------


async def list_ollama_models(
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: float = 5.0,
) -> list[str]:
    """Return the names of models available on a local Ollama instance.

    Calls ``GET {base_url}/api/tags`` and extracts ``models[].name``.
    Raises :class:`SRTTranslationError` when Ollama is unreachable or
    returns an unexpected payload.
    """
    url = base_url.rstrip("/") + "/api/tags"
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
    except (aiohttp.ClientError, ValueError) as exc:
        raise SRTTranslationError(f"Không liên hệ được Ollama tại {base_url}: {exc}") from exc

    models = data.get("models")
    if not isinstance(models, list):
        raise SRTTranslationError("Phản hồi /api/tags từ Ollama không đúng định dạng.")
    names = [m["name"] for m in models if isinstance(m, dict) and m.get("name")]
    return sorted(names)


# ---------------------------------------------------------------------------
# 1. Scan source directory
# ---------------------------------------------------------------------------


def scan_srt_files(source_dir: str | Path, recursive: bool = True) -> list[Path]:
    """Return every ``.srt`` file under *source_dir*.

    ``recursive=True`` walks subdirectories (``rglob``), otherwise only
    the top level is scanned (``glob``). Results are sorted so output
    order is deterministic.
    """
    root = Path(source_dir).expanduser().resolve()
    if not root.is_dir():
        raise SRTTranslationError(f"Source directory not found: {root}")

    if recursive:
        files = [p for p in root.rglob("*.srt") if p.is_file()]
    else:
        files = [p for p in root.glob("*.srt") if p.is_file()]
    return sorted(files, key=lambda p: str(p).lower())


# ---------------------------------------------------------------------------
# 2. Prompt building + response parsing (with fallbacks)
# ---------------------------------------------------------------------------


def _build_system_prompt(config: TranslationConfig) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(target_language=config.target_language)


def _build_user_message(
    config: TranslationConfig,
    chunk: Sequence[pysrt.SubRipItem],
    strict: bool = False,
) -> str:
    """Serialize a chunk to the ``[{"id": .., "text": ..}]`` payload."""
    payload = [{"id": item.index, "text": item.text} for item in chunk]
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    if strict:
        return (
            "Lần trả về trước không hợp lệ. Dịch lại và trả về DUY NHẤT mảng "
            "JSON thuần (không markdown, không chú thích, không văn bản thừa). "
            "Mỗi phần tử đúng dạng {\"id\": <số>, \"text\": \"<bản dịch>\"}. "
            "Dữ liệu cần dịch:\n" + body
        )
    return (
        "Dịch giá trị 'text' của từng phần tử sang "
        f"{config.target_language} và trả về lại đúng mảng JSON với id không "
        "đổi (chỉ thay 'text' bằng bản dịch):\n" + body
    )


def _extract_json(raw: str) -> list[dict[str, Any]]:
    """Best-effort extraction of the JSON array from a model response.

    Order of attempts:
    1. Direct ``json.loads`` (clean response).
    2. Markdown fenced block: ```json ... ``` / ``` ... ```.
    3. First ``[...]`` bracket span in the text.

    Raises :class:`SRTFormatError` if nothing parses.
    """
    text = (raw or "").strip()
    if not text:
        raise SRTFormatError("Empty response from Ollama")

    candidates: list[str] = [text]

    fence = _FENCE_RE.search(text)
    if fence:
        candidates.append(fence.group(1))

    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        data = _coerce_to_list(data)
        if data is not None:
            return data
        last_error = SRTFormatError("Parsed JSON is not a list of {id, text}")

    raise SRTFormatError(
        f"Could not extract a JSON array from model output "
        f"(last error: {last_error}). Raw head: {text[:200]!r}"
    )


def _coerce_to_list(data: Any) -> list[dict[str, Any]] | None:
    """Accept a bare list, or a dict wrapping the list (e.g. 'translations')."""
    if isinstance(data, dict):
        for key in ("translations", "items", "result", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # Single-object response: wrap it.
            data = [data] if "id" in data and "text" in data else None
    if not isinstance(data, list):
        return None
    cleaned = [item for item in data if isinstance(item, dict) and "id" in item]
    return cleaned or None


def _validate_translations(
    parsed: list[dict[str, Any]], expected_ids: Sequence[int]
) -> dict[int, str]:
    """Ensure every expected id came back with a non-empty string 'text'."""
    result: dict[int, str] = {}
    for item in parsed:
        try:
            key = int(item["id"])
        except (TypeError, ValueError):
            continue
        value = item.get("text")
        if isinstance(value, str) and value.strip():
            result[key] = value.strip()

    missing = [i for i in expected_ids if i not in result]
    if missing:
        raise SRTFormatError(
            f"Response missing {len(missing)}/{len(expected_ids)} entries "
            f"(e.g. ids {missing[:5]}...)"
        )
    return result


# ---------------------------------------------------------------------------
# 3. Chunking + Ollama call
# ---------------------------------------------------------------------------


def _chunk_entries(
    entries: Sequence[pysrt.SubRipItem], chunk_size: int
) -> list[list[pysrt.SubRipItem]]:
    return [entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)]


async def _ollama_chat(
    session: aiohttp.ClientSession,
    config: TranslationConfig,
    system_prompt: str,
    user_message: str,
) -> str:
    """One non-streaming ``POST /api/chat`` call; returns assistant text."""
    url = config.base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": config.model,
        "stream": False,
        "system": system_prompt,
        "temperature": config.temperature,
        "messages": [{"role": "user", "content": user_message}],
    }
    timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)
    async with session.post(url, json=payload, timeout=timeout) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise SRTTranslationError(f"Ollama HTTP {resp.status} at {url}: {body[:500]}")
        data = await resp.json()

    content = (data.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise SRTFormatError(f"Ollama returned no message content: {str(data)[:300]}")
    return content


async def translate_chunk(
    session: aiohttp.ClientSession,
    config: TranslationConfig,
    chunk: Sequence[pysrt.SubRipItem],
) -> dict[int, str]:
    """Translate one chunk with retries on format / network failures.

    Retries after the first use a hardened user message explicitly telling
    the model to return pure JSON.
    """
    system_prompt = _build_system_prompt(config)
    expected_ids = [item.index for item in chunk]
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            user_message = _build_user_message(config, chunk, strict=attempt > 0)
            raw = await _ollama_chat(session, config, system_prompt, user_message)
            parsed = _extract_json(raw)
            return _validate_translations(parsed, expected_ids)
        except (SRTFormatError, aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_error = exc
            if attempt < config.max_retries:
                await asyncio.sleep(1.5 * (attempt + 1))
    raise SRTTranslationError(
        f"Chunk (ids {expected_ids[0]}-{expected_ids[-1]}) failed after "
        f"{config.max_retries + 1} attempts: {last_error}"
    ) from last_error


# ---------------------------------------------------------------------------
# 4. Merge results + write output
# ---------------------------------------------------------------------------


def _merge_into_subtitles(
    subs: pysrt.SubRipFile, translations: dict[int, str]
) -> pysrt.SubRipFile:
    """Build a new SubRipFile carrying translated text (timings preserved).

    Entries missing from *translations* keep their original text so a
    partial failure never loses a line.
    """
    translated = pysrt.SubRipFile()
    for item in subs:
        translated.append(
            pysrt.SubRipItem(
                index=item.index,
                start=item.start,
                end=item.end,
                text=translations.get(item.index, item.text),
            )
        )
    return translated


def build_output_path(
    src: Path, dest_dir: Path, source_root: Path, target_code: str
) -> Path:
    """Map a source file to its translated destination path.

    Mirrors the relative structure under *source_root*, e.g.
    ``root/movies/show.srt`` -> ``dest/movies/show.vi.srt``.
    """
    try:
        rel_parent = src.parent.relative_to(source_root)
    except ValueError:
        rel_parent = Path()
    out = dest_dir / rel_parent / f"{src.stem}.{target_code}.srt"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


async def translate_subtitles(
    subs: pysrt.SubRipFile,
    config: TranslationConfig,
    progress: Optional[ProgressCallback] = None,
) -> pysrt.SubRipFile:
    """Translate every entry of *subs* via Ollama; returns a new file obj."""
    chunks = _chunk_entries(list(subs), config.chunk_size)
    all_translations: dict[int, str] = {}

    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        for i, chunk in enumerate(chunks, start=1):
            if progress:
                progress("translating", i, len(chunks))
            all_translations.update(await translate_chunk(session, config, chunk))

    return _merge_into_subtitles(subs, all_translations)


async def translate_files(
    source_dir: str | Path,
    dest_dir: str | Path,
    config: TranslationConfig | None = None,
    recursive: bool = True,
    progress: Optional[ProgressCallback] = None,
    on_file_done: Optional[Callable[[dict[str, str]], None]] = None,
) -> list[dict[str, str]]:
    """Translate every ``.srt`` under *source_dir* into *dest_dir*.

    Returns a per-file report: ``{"source", "output", "entries", "status"}``.
    A failure on one file is recorded and does not stop the rest.

    *on_file_done* (when given) is called synchronously with each finished
    entry — used by the web UI to stream per-file progress.
    """
    config = config or TranslationConfig()
    source_root = Path(source_dir).expanduser().resolve()
    dest_root = Path(dest_dir).expanduser().resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    files = scan_srt_files(source_root, recursive=recursive)
    if not files:
        raise SRTTranslationError(f"No .srt files found under {source_root}")

    report: list[dict[str, str]] = []
    for i, src in enumerate(files, start=1):
        if progress:
            progress("file", i, len(files))
        entry: dict[str, str] = {
            "source": str(src),
            "output": str(build_output_path(src, dest_root, source_root, config.target_code)),
            "entries": "0",
            "status": "ok",
        }
        try:
            subs = pysrt.open(str(src))
            entry["entries"] = str(len(subs))
            translated = await translate_subtitles(subs, config)
            translated.save(entry["output"], encoding="utf-8")
        except (SRTTranslationError, pysrt.Error, OSError) as exc:
            entry["status"] = f"error: {exc}"
        report.append(entry)
        if on_file_done:
            on_file_done(entry)
    return report


# ---------------------------------------------------------------------------
# 5. CLI test runner
# ---------------------------------------------------------------------------


def _print_progress(stage: str, current: int, total: int) -> None:
    if stage == "file":
        print(f"[{current}/{total}] processing file...", flush=True)
    elif stage == "translating":
        print(f"    chunk {current}/{total}", flush=True)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="srt-translator",
        description="Translate .srt files with a local Ollama model.",
    )
    parser.add_argument("source_dir", help="Folder containing .srt files")
    parser.add_argument("dest_dir", help="Folder to write translated .srt files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model (default: %(default)s)")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE_URL, help="Ollama server URL (default: %(default)s)")
    parser.add_argument("--target-language", default="tiếng Việt", help="Human language name for the prompt (default: %(default)s)")
    parser.add_argument("--target-code", default="vi", help="Filename suffix code, e.g. vi (default: %(default)s)")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Entries per request (default: %(default)s)")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Retries per bad chunk (default: %(default)s)")
    parser.add_argument("--flat", action="store_true", help="Do not recurse into subdirectories")
    parser.add_argument("--dry-run", action="store_true", help="Only list the .srt files that would be processed")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    files = scan_srt_files(args.source_dir, recursive=not args.flat)
    print(f"Found {len(files)} .srt file(s) under {args.source_dir}")
    for path in files:
        print(f"  - {path}")
    if args.dry_run or not files:
        return 0

    config = TranslationConfig(
        base_url=args.base_url,
        model=args.model,
        target_language=args.target_language,
        target_code=args.target_code,
        chunk_size=args.chunk_size,
        max_retries=args.max_retries,
    )
    print(
        f"model={config.model} lang={config.target_language!r} "
        f"chunk_size={config.chunk_size} retries={config.max_retries}"
    )

    started = time.monotonic()
    report = asyncio.run(
        translate_files(
            args.source_dir,
            args.dest_dir,
            config=config,
            recursive=not args.flat,
            progress=_print_progress,
        )
    )

    failed = [row for row in report if not row["status"] == "ok"]
    for row in report:
        mark = "OK " if row["status"] == "ok" else "ERR"
        print(f"  [{mark}] {row['source']} -> {row['output']} "
              f"({row['entries']} entries, {row['status']})")
    elapsed = time.monotonic() - started
    print(f"Done in {elapsed:.1f}s — {len(report) - len(failed)} ok, {len(failed)} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())