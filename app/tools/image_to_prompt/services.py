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

PROMPT_LANGUAGES = {
    "en": "English",
    "vi": "Vietnamese (Tiếng Việt)",
    "ja": "Japanese (Tiếng Nhật)",
    "ko": "Korean (Tiếng Hàn)",
    "zh": "Chinese (Tiếng Trung)",
    "fr": "French (Tiếng Pháp)",
    "de": "German (Tiếng Đức)",
    "es": "Spanish (Tiếng Tây Ban Nha)",
}

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert AI prompt engineer specializing in visual image analysis and prompt creation for modern "
    "cloud image generation models like Google Gemini (Imagen 3) and ChatGPT (DALL-E 3).\n\n"
    "Analyze this image and provide:\n"
    "1. A concise, catchy Title (name) for the image in {output_language}.\n"
    "2. A rich, highly descriptive Prompt in {output_language} to recreate this image accurately.\n\n"
    "Guidelines for the Prompt:\n"
    "- Character & Reference Face: If a person or character is in the image, identify their gender/type (e.g., a male character, a female character, a man, a woman) and explicitly describe in the prompt that their face is based on the reference image (e.g., 'a male character whose face and facial features are based on the reference image' / 'nhân vật nam dùng ảnh tham chiếu cho khuôn mặt'). Do NOT describe the specific facial features (eyes, nose, lips) from this analyzed image.\n"
    "- Write the prompt in {output_language} using fluent, descriptive natural language sentences rather than comma-separated tags.\n"
    "- Describe the subject's body, appearance, pose, clothing, actions, environment, background, setting, lighting, atmosphere, color palette, camera perspective, and artistic medium in rich detail.\n"
    "- Avoid negative prompts, keyword spam, or model parameters (no '--ar', no weights like '(masterpiece:1.2)').\n\n"
    "Format your output strictly as follows (do not include greetings or explanations):\n"
    "Title: <concise title for the image in {output_language}>\n\n"
    "Prompt:\n"
    "<detailed generation prompt in {output_language}>"
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
    language: str = "en"
    temperature: float = 0.2
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    overwrite: bool = False
    reference_face_bytes: Optional[bytes] = None


def prepare_prompt(prompt: str, language: str = "en") -> str:
    """Inject output language into the prompt template or append language requirement."""
    lang_name = PROMPT_LANGUAGES.get(language, language)
    p = prompt or DEFAULT_SYSTEM_PROMPT
    if "{output_language}" in p:
        return p.replace("{output_language}", lang_name)
    if language.lower() not in ("en", "english"):
        return (
            f"{p}\n\nImportant Requirement: Both the Title (image name) and the generated image Prompt "
            f"MUST be written entirely in {lang_name}."
        )
    return p


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
    fence_match = re.search(r"```(?:markdown|prompt|txt|text|json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    # Remove leading common bot phrases like "Here is the prompt:", "Prompt:", etc.
    text = re.sub(r"^(?:Here is(?: a| the)? prompt:?|Generated prompt:?)\s*", "", text, flags=re.IGNORECASE).strip()

    # Remove surrounding quotes if entire text is wrapped in "..."
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    return text


def parse_title_and_prompt(text: str) -> dict[str, str]:
    """Parse raw model output or existing txt content into a title and prompt dict."""
    cleaned = clean_extracted_prompt(text)
    if not cleaned:
        return {"title": "", "prompt": ""}

    # 1. Try JSON parsing
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, dict):
                title = str(data.get("title") or data.get("name") or data.get("tieu_de") or "").strip()
                prompt = str(data.get("prompt") or data.get("description") or "").strip()
                if title or prompt:
                    return {
                        "title": title.strip('"\'*# '),
                        "prompt": prompt.strip('"\' '),
                    }
        except Exception:
            pass

    # 2. Markdown headers or labelled sections:
    # Handles: # Image Title, Title:, **Title:**, # Prompt, Prompt:, etc.
    title_pattern = re.compile(
        r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:\*\*)?(?:Image\s*Title|Title|Tiêu\s*đề|Tên\s*ảnh|Name)\s*[:：\-]?(?:\*\*)?\s*[:：\-]?(?:\*\*)?\s*\n*\s*([^\n\r#]+)",
        re.IGNORECASE,
    )

    prompt_section_pattern = re.compile(
        r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:\*\*)?(?:MAIN\s*PROMPT|Image\s*Prompt|Prompt|Gợi\s*ý\s*prompt)\s*[:：\-]?(?:\*\*)?\s*[:：\-]?(?:\*\*)?\s*([\s\S]*?)(?=(?:\n\s*(?:#{1,3}\s*)?(?:\*\*)?Negative\s*Prompt\s*[:：\-]?(?:\*\*)?)|$)",
        re.IGNORECASE,
    )

    prompt_match = prompt_section_pattern.search(cleaned)
    title_match = title_pattern.search(cleaned)

    title = ""
    prompt = ""

    if prompt_match:
        prompt = prompt_match.group(1).strip()
        if title_match:
            if title_match.start() < prompt_match.start():
                title = title_match.group(1).strip()
            else:
                title = title_match.group(1).strip()
        else:
            pre = cleaned[:prompt_match.start()].strip()
            pre = re.sub(
                r"^(?:#{1,3}\s*)?(?:\*\*)?(?:Image\s*Title|Title|Tiêu\s*đề|Tên\s*ảnh|Name)\s*[:：\-]?(?:\*\*)?\s*[:：\-]?(?:\*\*)?\s*",
                "",
                pre,
                flags=re.IGNORECASE,
            ).strip()
            if pre:
                title = pre.split("\n")[0].strip()
    elif title_match:
        title = title_match.group(1).strip()
        after_title = cleaned[title_match.end():].strip()
        prompt = after_title
    else:
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
        if len(lines) == 1:
            full = lines[0]
            if len(full) > 60:
                first_clause = re.split(r"[,;:.!?]", full)[0].strip()
                if 10 <= len(first_clause) <= 60:
                    title = first_clause
                else:
                    split_at = full[:60].rfind(" ")
                    title = full[:split_at].strip() if split_at > 20 else full[:50].strip()
                prompt = full
            else:
                title = full
                prompt = full
        elif len(lines) > 1:
            first_line = lines[0]
            if len(first_line) <= 80:
                title = first_line
                prompt = "\n".join(lines[1:]).strip()
            else:
                title = first_line[:60].strip()
                prompt = "\n".join(lines).strip()

    title = title.strip().strip('"\'*#')
    prompt = prompt.strip().strip('"\'')

    if not title and prompt:
        first_sentence = re.split(r"[.!?\n]", prompt)[0].strip()
        title = first_sentence[:60].strip() if len(first_sentence) > 60 else first_sentence

    return {
        "title": title,
        "prompt": prompt,
    }


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
) -> dict[str, str]:
    """Send image bytes (base64) to Ollama and return dict with 'title' and 'prompt'."""
    if not image_bytes:
        raise ImageToPromptError("Dữ liệu ảnh trống.")

    model_to_use = await resolve_model_name(config.model, config.base_url)
    base_prompt = prepare_prompt(config.prompt, config.language)

    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    images_payload = [b64_img]

    final_prompt = base_prompt
    if config.reference_face_bytes:
        b64_ref = base64.b64encode(config.reference_face_bytes).decode("utf-8")
        images_payload.append(b64_ref)
        final_prompt = (
            f"IMPORTANT: You are analyzing TWO images.\n"
            f"- Image 1: Main scene & composition image (defines subject pose, clothing, actions, environment, lighting, and style).\n"
            f"- Image 2: Reference face image (defines the character's face, facial likeness, eyes, nose, lips, facial structure, skin tone, and identity).\n\n"
            f"CRITICAL INSTRUCTION: The character's face in the generated prompt MUST be strictly the person in Image 2 (the uploaded reference face image). "
            f"Do NOT describe the face from Image 1. Instead, describe the face using the exact facial characteristics of Image 2, and explicitly state in the prompt: "
            f"'The character's face is identical to the uploaded reference face image, perfectly matching the facial features, structure, eyes, nose, lips, skin tone, and likeness of the reference photo.'\n\n"
            f"{base_prompt}"
        )

    base = config.base_url.rstrip("/")
    timeout = aiohttp.ClientTimeout(total=config.timeout_seconds, connect=30.0)

    chat_payload = {
        "model": model_to_use,
        "messages": [
            {
                "role": "user",
                "content": final_prompt,
                "images": images_payload,
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
                        return parse_title_and_prompt(cleaned)
                    raise ImageToPromptError("Ollama trả về nội dung rỗng.")

                err_body = await resp.text()

                # If model does not support multiple images, fallback to single image with prompt directive
                if len(images_payload) > 1 and ("only 1 image" in err_body.lower() or "one image" in err_body.lower() or "only one image" in err_body.lower()):
                    retry_payload = dict(chat_payload)
                    retry_payload["messages"] = [
                        {
                            "role": "user",
                            "content": final_prompt,
                            "images": [b64_img],
                        }
                    ]
                    async with session.post(f"{base}/api/chat", json=retry_payload) as retry_resp:
                        if retry_resp.status == 200:
                            retry_data = await retry_resp.json()
                            retry_content = retry_data.get("message", {}).get("content", "")
                            cleaned = clean_extracted_prompt(retry_content)
                            if cleaned:
                                return parse_title_and_prompt(cleaned)

                # If Ollama endpoint itself is not found (e.g. legacy Ollama), fallback to /api/generate
                if resp.status == 404 and "404 page not found" in err_body.lower():
                    gen_payload = {
                        "model": model_to_use,
                        "prompt": final_prompt,
                        "images": images_payload,
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
                                return parse_title_and_prompt(cleaned)
                            raise ImageToPromptError("Ollama trả về nội dung rỗng.")
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
) -> dict[str, str]:
    """Read image file and generate title and prompt."""
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
        parsed = parse_title_and_prompt(existing_content)
        return {
            "status": "skipped",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "title": parsed.get("title", ""),
            "prompt": parsed.get("prompt", existing_content),
            "reason": "File .txt đã tồn tại (đã bỏ qua vì không chọn ghi đè)",
        }

    try:
        res = await generate_prompt_for_file(image_path, config)
        if isinstance(res, str):
            res = parse_title_and_prompt(res)
        title = res.get("title", "").strip()
        prompt_text = res.get("prompt", "").strip()

        file_content = f"Title: {title}\n\nPrompt:\n{prompt_text}\n"
        await asyncio.to_thread(txt_path.write_text, file_content, encoding="utf-8")
        return {
            "status": "ok",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "title": title,
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
