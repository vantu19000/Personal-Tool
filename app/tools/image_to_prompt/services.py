"""Core services for Image to Prompt (Reverse Prompt) tool using local Ollama vision models."""
from __future__ import annotations

import asyncio
import base64
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional

import aiohttp

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qween3.8"

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert AI prompt engineer. Analyze this image and write a detailed, "
    "highly descriptive prompt to recreate it using an AI image generator (such as Midjourney, "
    "Stable Diffusion, or Flux). Include subject, appearance, composition, artistic style, "
    "medium, lighting, color palette, details, and atmosphere. "
    "Return ONLY the prompt text, without any conversational prefix, introductory phrases, or explanation."
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}


class ImageToPromptError(RuntimeError):
    """Base error for the image to prompt pipeline."""


@dataclass
class PromptConfig:
    """Runtime configuration for reverse prompt generation."""

    base_url: str = DEFAULT_OLLAMA_BASE_URL
    model: str = DEFAULT_MODEL
    prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.2
    timeout_seconds: float = 180.0
    overwrite: bool = False


async def list_ollama_models(
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: float = 5.0,
) -> list[str]:
    """Return the names of models available on local Ollama instance (/api/tags)."""
    url = base_url.rstrip("/") + "/api/tags"
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        raise ImageToPromptError(f"Không kết nối được tới Ollama tại {base_url}: {exc}") from exc

    models = data.get("models")
    if not isinstance(models, list):
        raise ImageToPromptError("Phản hồi /api/tags từ Ollama không đúng định dạng.")
    names = [m["name"] for m in models if isinstance(m, dict) and m.get("name")]
    return sorted(names)


def scan_image_files(folder: str | Path, recursive: bool = False) -> list[Path]:
    """Scan and return all image files in the target folder."""
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ImageToPromptError(f"Thư mục không tồn tại: {root}")

    pattern = "**/*" if recursive else "*"
    files: list[Path] = []
    for p in root.glob(pattern):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(p)

    return sorted(files, key=lambda x: str(x).lower())


def clean_extracted_prompt(text: str) -> str:
    """Clean model response, stripping code blocks, markdown tags, or extra quotes."""
    text = (text or "").strip()
    if not text:
        return ""

    # Remove markdown code fences if wrapped in ```prompt ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:markdown|prompt|txt|text)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    # Remove leading common bot phrases like "Here is the prompt:", "Prompt:", etc.
    text = re.sub(r"^(?:Here is(?: a| the)? prompt:?|Prompt:?|Generated prompt:?)\s*", "", text, flags=re.IGNORECASE).strip()

    # Remove surrounding quotes if entire text is wrapped in "..."
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    return text


async def resolve_model_name(requested_model: str, base_url: str = DEFAULT_OLLAMA_BASE_URL) -> str:
    """Normalize model name (e.g. 'qween3.8' -> 'qwen3.8:latest' if installed on Ollama)."""
    if not requested_model:
        return DEFAULT_MODEL
    try:
        available = await list_ollama_models(base_url, timeout_seconds=3.0)
        if requested_model in available:
            return requested_model
        # Check aliases: qween -> qwen, match tags
        clean_req = requested_model.lower().replace("qween", "qwen").replace(":latest", "")
        for m in available:
            clean_m = m.lower().replace(":latest", "")
            if clean_req == clean_m or clean_m.startswith(clean_req):
                return m
    except Exception:
        pass
    return requested_model


async def generate_prompt_for_image_bytes(
    image_bytes: bytes,
    config: PromptConfig,
) -> str:
    """Send image bytes (base64) to Ollama and return the reverse engineered prompt."""
    if not image_bytes:
        raise ImageToPromptError("Dữ liệu ảnh trống.")

    model_to_use = await resolve_model_name(config.model, config.base_url)

    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    base = config.base_url.rstrip("/")
    timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)

    chat_payload = {
        "model": model_to_use,
        "messages": [
            {
                "role": "user",
                "content": config.prompt,
                "images": [b64_img],
            }
        ],
        "stream": False,
        "options": {
            "temperature": config.temperature,
        },
    }

    last_error: Exception | None = None

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # First attempt: POST /api/chat
        try:
            async with session.post(f"{base}/api/chat", json=chat_payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("message", {}).get("content", "")
                    cleaned = clean_extracted_prompt(content)
                    if cleaned:
                        return cleaned
                else:
                    err_body = await resp.text()
                    last_error = ImageToPromptError(f"Ollama /api/chat trả về mã {resp.status}: {err_body}")
        except Exception as exc:
            last_error = exc

        # Fallback attempt: POST /api/generate
        try:
            gen_payload = {
                "model": model_to_use,
                "prompt": config.prompt,
                "images": [b64_img],
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                },
            }
            async with session.post(f"{base}/api/generate", json=gen_payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("response", "")
                    cleaned = clean_extracted_prompt(content)
                    if cleaned:
                        return cleaned
                else:
                    err_body = await resp.text()
                    raise ImageToPromptError(f"Ollama /api/generate trả về mã {resp.status}: {err_body}")
        except Exception as exc:
            if last_error:
                raise ImageToPromptError(f"Lỗi gọi Ollama: {exc} (Trước đó: {last_error})") from exc
            raise ImageToPromptError(f"Lỗi gọi Ollama: {exc}") from exc

    if last_error:
        raise ImageToPromptError(f"Không nhận được prompt từ Ollama: {last_error}")
    raise ImageToPromptError("Phản hồi rỗng từ mô hình Ollama.")


async def generate_prompt_for_file(
    image_path: Path,
    config: PromptConfig,
) -> str:
    """Read image file and generate prompt."""
    try:
        raw_bytes = await asyncio.to_thread(image_path.read_bytes)
    except OSError as exc:
        raise ImageToPromptError(f"Không thể đọc file ảnh {image_path.name}: {exc}") from exc

    return await generate_prompt_for_image_bytes(raw_bytes, config)


async def process_image_file(
    image_path: Path,
    config: PromptConfig,
) -> dict[str, Any]:
    """Process a single image file, write .txt alongside it, and return status."""
    txt_path = image_path.with_suffix(".txt")

    # Check if .txt file already exists
    if txt_path.exists() and not config.overwrite:
        try:
            existing_content = await asyncio.to_thread(txt_path.read_text, encoding="utf-8", errors="replace")
        except Exception:
            existing_content = ""
        return {
            "status": "skipped",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "prompt": existing_content,
            "reason": "File .txt đã tồn tại (đã bỏ qua vì không chọn ghi đè)",
        }

    try:
        prompt_text = await generate_prompt_for_file(image_path, config)
        await asyncio.to_thread(txt_path.write_text, prompt_text + "\n", encoding="utf-8")
        return {
            "status": "ok",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "prompt": prompt_text,
        }
    except Exception as exc:
        return {
            "status": "error",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "error": str(exc),
        }
