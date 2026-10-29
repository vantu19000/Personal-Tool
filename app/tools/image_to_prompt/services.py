"""Core services for Image to Prompt (Reverse Prompt) tool using local Ollama vision models."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional

import aiohttp

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qween3.8"
DEFAULT_TIMEOUT_SECONDS = 1200.0  # 20 phút (20 * 60s)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert AI prompt engineer specializing in prompt creation for modern cloud image generation "
    "models like Google Gemini (Imagen 3) and ChatGPT (DALL-E 3).\n\n"
    "Analyze this image and write a rich, highly descriptive prompt in natural English to recreate this image accurately.\n\n"
    "Guidelines for Gemini & ChatGPT:\n"
    "- Write in fluent, descriptive natural language sentences rather than comma-separated tags.\n"
    "- Describe the subject(s) in detail: appearance, facial expression, pose, clothing, and actions.\n"
    "- Describe the environment, background, setting, lighting (e.g., golden hour, soft studio light, volumetric rays), atmosphere, and color palette.\n"
    "- Specify the artistic medium and camera perspective (e.g., cinematic photography, eye-level shot, 35mm film still, digital illustration).\n"
    "- Avoid negative prompts, keyword spam, or model parameters (no '--ar', no weights like '(masterpiece:1.2)').\n"
    "- Return ONLY the final prompt text. Do not include any greeting, introduction, explanation, or markdown quotes."
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
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
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


def extract_ollama_error(raw_response: str) -> str:
    """Extract raw error message directly from Ollama response JSON or text."""
    if not raw_response or not raw_response.strip():
        return "Lỗi rỗng từ dịch vụ Ollama."
    text = raw_response.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if "error" in data and data["error"]:
                return str(data["error"])
            if "message" in data and data["message"]:
                return str(data["message"])
    except Exception:
        pass
    return text


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
    timeout = aiohttp.ClientTimeout(total=config.timeout_seconds, connect=30.0)

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

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # First attempt: POST /api/chat
            async with session.post(f"{base}/api/chat", json=chat_payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("message", {}).get("content", "")
                    cleaned = clean_extracted_prompt(content)
                    if cleaned:
                        return cleaned
                    raise ImageToPromptError("Ollama trả về nội dung prompt rỗng.")

                err_body = await resp.text()

                # If Ollama endpoint itself is not found (e.g. legacy Ollama), fallback to /api/generate
                if resp.status == 404 and "404 page not found" in err_body.lower():
                    gen_payload = {
                        "model": model_to_use,
                        "prompt": config.prompt,
                        "images": [b64_img],
                        "stream": False,
                        "options": {
                            "temperature": config.temperature,
                        },
                    }
                    async with session.post(f"{base}/api/generate", json=gen_payload) as gen_resp:
                        if gen_resp.status == 200:
                            gen_data = await gen_resp.json()
                            gen_content = gen_data.get("response", "")
                            cleaned = clean_extracted_prompt(gen_content)
                            if cleaned:
                                return cleaned
                            raise ImageToPromptError("Ollama trả về nội dung prompt rỗng.")
                        gen_err = await gen_resp.text()
                        raise ImageToPromptError(extract_ollama_error(gen_err))

                # Extract and raise the EXACT error returned by Ollama
                raise ImageToPromptError(extract_ollama_error(err_body))

    except aiohttp.ClientConnectorError as exc:
        raise ImageToPromptError(f"Không thể kết nối đến Ollama tại {base}. Dịch vụ có đang chạy không?") from exc
    except asyncio.TimeoutError:
        mins = int(config.timeout_seconds // 60)
        raise ImageToPromptError(f"Hết thời gian chờ phản hồi từ Ollama ({int(config.timeout_seconds)}s ~ {mins} phút).")
    except ImageToPromptError:
        raise
    except Exception as exc:
        raise ImageToPromptError(str(exc)) from exc


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
