"""Core services for Image to Prompt (Reverse Prompt) tool using local Ollama vision models."""
from __future__ import annotations

import asyncio
import base64
import io
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional

import aiohttp
from PIL import Image

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qween3.8"
DEFAULT_TIMEOUT_SECONDS = 1200.0  # 20 phút (20 * 60s)
DEFAULT_CHARACTER_DESC = "nhân vật nam dùng ảnh tham chiếu cho khuôn mặt"
DEFAULT_ASPECT_RATIO_MODE = "both"

STANDARD_RATIOS = [
    (1, 1, "1:1"),
    (16, 9, "16:9"),
    (9, 16, "9:16"),
    (4, 3, "4:3"),
    (3, 4, "3:4"),
    (3, 2, "3:2"),
    (2, 3, "2:3"),
    (4, 5, "4:5"),
    (5, 4, "5:4"),
    (21, 9, "21:9"),
    (9, 21, "9:21"),
]

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
    "cloud image generation models like Google Gemini (Imagen 3), Midjourney, and ChatGPT (DALL-E 3).\n\n"
    "Analyze this image and provide:\n"
    "1. A concise, catchy Title (name) for the image in {output_language}.\n"
    "2. A rich, highly descriptive Prompt in {output_language} to recreate this image accurately.\n\n"
    "Guidelines for the Prompt:\n"
    "- Character & Reference Face: If a person or character is in the image, identify their gender/type (e.g., a male character, a female character, a man, a woman) and explicitly describe in the prompt that their face is based on the reference image (e.g., 'a male character whose face and facial features are based on the reference image' / 'nhân vật nam dùng ảnh tham chiếu cho khuôn mặt'). Do NOT describe the specific facial features (eyes, nose, lips) from this analyzed image.\n"
    "- Aspect Ratio: Replicate the original image aspect ratio ({aspect_ratio}).\n"
    "- Write the prompt in {output_language} using fluent, descriptive natural language sentences rather than comma-separated tags.\n"
    "- Describe the subject's body, appearance, pose, clothing, actions, environment, background, setting, lighting, atmosphere, color palette, camera perspective, and artistic medium in rich detail.\n\n"
    "Format your output strictly as follows (use EXACTLY the label prefixes 'Title:' and 'Prompt:' as shown, do not translate or add language tags to these labels):\n"
    "Title: <concise title for the image in {output_language}>\n\n"
    "Prompt:\n"
    "<detailed generation prompt in {output_language}>"
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}


class ImageToPromptError(RuntimeError):
    """Base error for the image to prompt pipeline."""


def detect_image_dimensions_and_ratio(image_bytes: bytes) -> tuple[int, int, str]:
    """Detect image width, height, and closest standard aspect ratio string (e.g. '16:9', '1:1')."""
    if not image_bytes:
        return 0, 0, "1:1"
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
    except Exception:
        return 0, 0, "1:1"

    if w <= 0 or h <= 0:
        return 0, 0, "1:1"

    ratio_val = w / h
    best_ratio = "1:1"
    min_diff = float("inf")
    for rw, rh, name in STANDARD_RATIOS:
        target = rw / rh
        diff = abs(ratio_val - target)
        if diff < min_diff:
            min_diff = diff
            best_ratio = name

    # If the ratio deviates notably from standard ratios, calculate reduced fraction or decimal
    if min_diff > 0.08:
        g = math.gcd(w, h)
        rw, rh = w // g, h // g
        if rw <= 30 and rh <= 30:
            best_ratio = f"{rw}:{rh}"
        else:
            best_ratio = f"{round(ratio_val, 2)}:1"

    return w, h, best_ratio


def apply_aspect_ratio_to_prompt(prompt: str, aspect_ratio: str, mode: str = "both") -> str:
    """Append aspect ratio tags or descriptions to the prompt based on mode."""
    if not prompt or not aspect_ratio or mode == "none":
        return prompt

    cleaned = prompt.strip()
    ar_tag = f"--ar {aspect_ratio}"
    natural_tag = f"Aspect ratio: {aspect_ratio}"

    has_ar = bool(re.search(r"--ar\s+\d+:\d+", cleaned, re.IGNORECASE))
    has_natural = bool(re.search(r"aspect\s+ratio:\s*\d+:\d+", cleaned, re.IGNORECASE))

    if mode == "midjourney":
        if not has_ar:
            cleaned = f"{cleaned} {ar_tag}"
    elif mode == "natural":
        if not has_natural:
            cleaned = f"{cleaned}\n\n{natural_tag}."
    elif mode == "both":
        additions = []
        if not has_natural:
            additions.append(f"{natural_tag}.")
        if not has_ar:
            additions.append(ar_tag)
        if additions:
            cleaned = f"{cleaned} {' '.join(additions)}"

    return cleaned.strip()


@dataclass
class PromptConfig:
    """Runtime configuration for reverse prompt generation."""

    base_url: str = DEFAULT_OLLAMA_BASE_URL
    model: str = DEFAULT_MODEL
    prompt: str = DEFAULT_SYSTEM_PROMPT
    language: str = "en"
    character_description: str = DEFAULT_CHARACTER_DESC
    aspect_ratio_mode: str = DEFAULT_ASPECT_RATIO_MODE
    temperature: float = 0.2
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    overwrite: bool = False
    reference_face_bytes: Optional[bytes] = None


def prepare_prompt(
    prompt: str,
    language: str = "en",
    character_description: str = "",
    aspect_ratio: str = "",
    width: int = 0,
    height: int = 0,
) -> str:
    """Inject output language, character description, and aspect ratio into the prompt template."""
    lang_name = PROMPT_LANGUAGES.get(language, language)
    p = prompt or DEFAULT_SYSTEM_PROMPT

    if "{output_language}" in p:
        p = p.replace("{output_language}", lang_name)
    elif language.lower() not in ("en", "english"):
        p = (
            f"{p}\n\nImportant Requirement: Both the Title (image name) and the generated image Prompt "
            f"MUST be written entirely in {lang_name}."
        )

    # Character description
    if "{character_description}" in p:
        char_desc = character_description or DEFAULT_CHARACTER_DESC
        p = p.replace("{character_description}", char_desc)
    elif character_description:
        p = f"{p}\n\nCharacter Guideline: {character_description}."

    # Aspect ratio
    if "{aspect_ratio}" in p:
        p = p.replace("{aspect_ratio}", aspect_ratio or "1:1")
    elif aspect_ratio:
        dim_info = f" ({width}x{height})" if width and height else ""
        p = f"{p}\n\nAspect Ratio Guideline: Original image aspect ratio is {aspect_ratio}{dim_info}. Replicate this ratio."

    if width and height:
        p = p.replace("{width}", str(width)).replace("{height}", str(height))

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


def clean_extracted_title(title: str) -> str:
    """Clean extracted title, stripping parentheticals like (Title), (Tiêu đề), labels, and markdown."""
    t = (title or "").strip()
    if not t:
        return ""
    # Strip numbering at start: e.g. "1. ", "1 - "
    t = re.sub(r"^(?:[\d\.\)\-\*\+]\s*)+", "", t).strip()
    # Strip parenthetical annotations at the start like (Title), (Tiêu đề), (bằng tiếng Việt), (Vietnamese)...
    t = re.sub(
        r"^\s*\(?\s*(?:Image\s*Title|Title|Tiêu\s*đề(?:\s*ảnh)?|Tên\s*(?:ảnh|hình\s*ảnh)?|Name|tiếng\s*[^)]*|bằng\s*tiếng\s*[^)]*|vietnamese|english)\s*\)?\s*[:：\-]*(?:\*\*)?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(
        r"^\s*\([^)]*(?:title|tên|tiêu đề|tiếng|vietnamese|english|ảnh|name)[^)]*\)\s*[:：\-]*(?:\*\*)?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    # Strip residual label prefix: "Title:", "Tiêu đề:", "**Title:**"
    t = re.sub(
        r"^(?:#{1,6}\s*)?(?:\*\*)?(?:Image\s*Title|Title|Tiêu\s*đề(?:\s*ảnh)?|Tên\s*(?:ảnh|hình\s*ảnh)?|Name)(?:\s*\([^)]*\))?(?:\*\*)?\s*[:：\-]*(?:\*\*)?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    # Strip any remaining leading/trailing punctuation or markdown symbols
    t = re.sub(r"^[\s\*#_`:\-–—\(\)]+", "", t)
    t = re.sub(r"[\s\*#_`:\-–—]+$", "", t)
    if len(t) >= 2 and ((t[0] == '"' and t[-1] == '"') or (t[0] == "'" and t[-1] == "'")):
        t = t[1:-1].strip()
    return t


def clean_extracted_prompt_body(prompt: str) -> str:
    """Clean extracted prompt, removing leftover header markers like '(bằng tiếng Việt):**', etc."""
    p = (prompt or "").strip()
    if not p:
        return ""
    # Strip leading numbering if prompt starts with "2. " or "2 - "
    p = re.sub(r"^(?:[\d\.\)\-\*\+]\s*)+", "", p).strip()
    # Strip leading language or prompt label tags e.g. "(bằng tiếng Việt):**", "Prompt (bằng tiếng Việt):**"
    p = re.sub(
        r"^(?:#{1,6}\s*)?(?:\*\*)?(?:MAIN\s*PROMPT|Image\s*Prompt|Prompt|Gợi\s*ý\s*prompt|Mô\s*tả\s*prompt|Nội\s*dung\s*prompt)?"
        r"\s*\([^)]*(?:tiếng|vietnamese|english|language|ngôn ngữ|prompt)[^)]*\)"
        r"(?:\*\*)?"
        r"\s*[:：\-]*(?:\*\*)?\s*[:：\-]*(?:\*\*)?\s*",
        "",
        p,
        flags=re.IGNORECASE,
    ).strip()
    # Strip standalone parenthetical line at the top: e.g. "(bằng tiếng Việt):**\n"
    p = re.sub(
        r"^\s*\([^)]*(?:tiếng|vietnamese|english|language|ngôn ngữ|prompt)[^)]*\)\s*[:：\-]*(?:\*\*)?\s*",
        "",
        p,
        flags=re.IGNORECASE,
    ).strip()
    # Strip residual dangling bold/markdown header prefix at prompt start e.g. "**", "##", ":**"
    p = re.sub(r"^(?:\*\*|[:：\-\*#_`])+\s*", "", p).strip()
    return p


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
                        "title": clean_extracted_title(title),
                        "prompt": clean_extracted_prompt_body(prompt),
                    }
        except Exception:
            pass

    # 2. Markdown headers or labelled sections:
    # Handles: # Image Title, Title:, **Title:**, # Prompt, Prompt:, (Title):**, (bằng tiếng Việt):**, etc.
    title_pattern = re.compile(
        r"(?:^|\n)\s*(?:[\d\.\)\-\*\+]\s*)*"
        r"(?:#{1,6}\s*)?"
        r"(?:\*\*)?"
        r"\(?\s*"
        r"(?:Image\s*Title|Title|Tiêu\s*đề(?:\s*ảnh)?|Tên\s*(?:ảnh|hình\s*ảnh)?|Name)"
        r"(?:\s*\([^)]*\))?"
        r"\)?\s*"
        r"(?:\*\*)?"
        r"\s*[:：\-]?(?:\*\*)?\s*[:：\-]?(?:\*\*)?\s*"
        r"([^\n\r#]+)",
        re.IGNORECASE,
    )

    prompt_section_pattern = re.compile(
        r"(?:^|\n)\s*(?:[\d\.\)\-\*\+]\s*)*"
        r"(?:#{1,6}\s*)?"
        r"(?:\*\*)?"
        r"\(?\s*"
        r"(?:MAIN\s*PROMPT|Image\s*Prompt|Prompt|Gợi\s*ý\s*prompt|Mô\s*tả\s*prompt|Nội\s*dung\s*prompt|bằng\s*tiếng\s*[^:：\*\n\)]+|tiếng\s*[^:：\*\n\)]+)"
        r"(?:\s*\([^)]*\))?"
        r"\)?\s*"
        r"(?:\*\*)?"
        r"\s*[:：\-]?(?:\*\*)?\s*[:：\-]?(?:\*\*)?\s*"
        r"([\s\S]*?)"
        r"(?=(?:\n\s*(?:#{1,6}\s*)?(?:\*\*)?Negative\s*Prompt\s*[:：\-]?(?:\*\*)?)|$)",
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

    title = clean_extracted_title(title)
    prompt = clean_extracted_prompt_body(prompt)

    if not title and prompt:
        first_sentence = re.split(r"[.!?\n]", prompt)[0].strip()
        title = clean_extracted_title(first_sentence[:60].strip() if len(first_sentence) > 60 else first_sentence)

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
) -> dict[str, Any]:
    """Send image bytes (base64) to Ollama and return dict with 'title', 'prompt', 'aspect_ratio', 'width', 'height'."""
    if not image_bytes:
        raise ImageToPromptError("Dữ liệu ảnh trống.")

    w, h, aspect_ratio = detect_image_dimensions_and_ratio(image_bytes)
    model_to_use = await resolve_model_name(config.model, config.base_url)
    base_prompt = prepare_prompt(
        prompt=config.prompt,
        language=config.language,
        character_description=config.character_description,
        aspect_ratio=aspect_ratio,
        width=w,
        height=h,
    )

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

    def _package_result(raw_text: str) -> dict[str, Any]:
        parsed = parse_title_and_prompt(raw_text)
        final_prompt_text = apply_aspect_ratio_to_prompt(
            parsed.get("prompt", ""),
            aspect_ratio=aspect_ratio,
            mode=config.aspect_ratio_mode,
        )
        return {
            "title": parsed.get("title", ""),
            "prompt": final_prompt_text,
            "aspect_ratio": aspect_ratio,
            "width": w,
            "height": h,
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
                        return _package_result(cleaned)
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
                                return _package_result(cleaned)

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
                                return _package_result(cleaned)
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
) -> dict[str, Any]:
    """Read image file and generate title, prompt, and aspect ratio."""
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

    # Read dimensions/aspect ratio for metadata
    try:
        raw_bytes = await asyncio.to_thread(image_path.read_bytes)
        w, h, ar = detect_image_dimensions_and_ratio(raw_bytes)
    except Exception:
        raw_bytes = b""
        w, h, ar = 0, 0, "1:1"

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
            "aspect_ratio": ar,
            "width": w,
            "height": h,
            "reason": "File .txt đã tồn tại (đã bỏ qua vì không chọn ghi đè)",
        }

    try:
        res = await generate_prompt_for_image_bytes(raw_bytes, config) if raw_bytes else await generate_prompt_for_file(image_path, config)
        if isinstance(res, str):
            res = parse_title_and_prompt(res)
        title = res.get("title", "").strip()
        prompt_text = res.get("prompt", "").strip()
        ar_res = res.get("aspect_ratio", ar)
        w_res = res.get("width", w)
        h_res = res.get("height", h)

        file_content = f"Title: {title}\n\nPrompt:\n{prompt_text}\n"
        await asyncio.to_thread(txt_path.write_text, file_content, encoding="utf-8")
        return {
            "status": "ok",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "title": title,
            "prompt": prompt_text,
            "aspect_ratio": ar_res,
            "width": w_res,
            "height": h_res,
        }
    except Exception as exc:
        return {
            "status": "error",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "aspect_ratio": ar,
            "width": w,
            "height": h,
            "error": str(exc),
        }
