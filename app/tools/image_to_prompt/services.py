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
DEFAULT_MODEL = "qwen 3.8"
DEFAULT_TIMEOUT_SECONDS = 1200.0  # 20 phút (20 * 60s)
DEFAULT_CHARACTER_DESC = ""
DEFAULT_ASPECT_RATIO_MODE = "none"
DEFAULT_TARGET_ASPECT_RATIO = "4:5"

# OpenAI Image Generation configuration
SUPPORTED_IMAGE_MODELS = [
    ("gpt-image-2.5-flare", "gpt-image-2.5-flare (Mặc định)"),
    ("gpt-image-2.6-flare", "gpt-image-2.6-flare"),
    ("gpt-image-2.6-sunburst", "gpt-image-2.6-sunburst"),
    ("gpt-image-2.5-sunburst", "gpt-image-2.5-sunburst"),
]
IMAGE_MODEL_NAMES = [m[0] for m in SUPPORTED_IMAGE_MODELS]
DEFAULT_IMAGE_MODEL = "gpt-image-2.5-flare"

SUPPORTED_IMAGE_QUALITIES = [
    ("medium", "medium (Mặc định)"),
    ("low", "low"),
    ("high", "high"),
]
IMAGE_QUALITY_NAMES = [q[0] for q in SUPPORTED_IMAGE_QUALITIES]
DEFAULT_IMAGE_QUALITY = "medium"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

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
    "pt-BR": "Português - Brasil (Tiếng Bồ Đào Nha - Brazil)",
    "en": "English",
    "vi": "Vietnamese (Tiếng Việt)",
    "ja": "Japanese (Tiếng Nhật)",
    "ko": "Korean (Tiếng Hàn)",
    "zh": "Chinese (Tiếng Trung)",
    "fr": "French (Tiếng Pháp)",
    "de": "German (Tiếng Đức)",
    "es": "Spanish (Tiếng Tây Ban Nha)",
}

PROMPT_LANG_NAMES = {
    "pt-BR": "Portuguese (Brazil)",
    "en": "English",
    "vi": "Vietnamese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
}

DEFAULT_SYSTEM_PROMPT = (
    "Dịch ngược bức ảnh thành prompt tạo ảnh AI chi tiết, dùng để chia sẻ cho người khác.\n\n"
    "YÊU CẦU QUAN TRỌNG VỀ KHUÔN MẶT THAM CHIẾU:\n"
    "Prompt này sẽ được chia sẻ cho người khác. Khi họ dùng prompt, họ sẽ tải lên kèm khuôn mặt của họ để làm ảnh tham chiếu (reference image / face reference). "
    "Do đó, trong nội dung prompt BẮT BUỘC phải nhắc đến việc: khuôn mặt và đặc điểm nhận diện của nhân vật / người phụ nữ (female character / model) sẽ dựa trên ảnh tham chiếu "
    "do người dùng tải lên (ví dụ bằng {output_language}: 'o rosto e os traços faciais devem ser exatamente baseados na imagem de referência anexada'). "
    "Tuyệt đối không mô tả chi tiết khuôn mặt gốc trong ảnh để người dùng dễ thay thế khuôn mặt của họ.\n\n"
    "BẮT CHƯỚC TOÀN BỘ CÁC YẾU TỐ CÒN LẠI TỪ BỨC ẢNH GỐC:\n"
    "- Không gian & Môi trường: Ánh sáng, bóng đổ, không khí xung quanh, nhiệt độ màu.\n"
    "- Phong cách: Phong cách nhiếp ảnh chân thực, độ nét cao, chất lượng hình ảnh cao cấp.\n"
    "- Khoảng cách camera: Cận cảnh (close-up), trung cảnh (medium shot) hoặc toàn thân (full-body).\n"
    "- Vị trí & góc máy camera: Góc ngang tầm mắt (eye-level), góc thấp (low-angle), góc cao, v.v.\n"
    "- Dáng người, hành động, hành vi & cảm xúc: Tư thế, cử chỉ tay, dáng người, cảm xúc tinh tế và chi tiết tới mức cô gái đang nhìn vào đâu (ví dụ: nhìn thẳng vào ống kính, nhìn nghiêng 45 độ, ánh mắt suy tư...).\n"
    "- Tông màu: Bảng màu chủ đạo, độ tương phản và ánh sáng.\n"
    "- Background: Hậu cảnh, bối cảnh xung quanh, chi tiết nội thất/ngoại cảnh và độ sâu trường ảnh (bokeh).\n"
    "- Tỷ lệ ảnh: {aspect_ratio} (hoặc 4:5).\n\n"
    "GỢI Ý 5 TIÊU ĐỀ CHO PROMPT (TỐI ƯU SEO):\n"
    "Gợi ý cho tôi 5 cái tên (tiêu đề) cho prompt, tối ưu SEO tốt bằng {output_language}.\n"
    "Định dạng bắt buộc cho từng tiêu đề:\n"
    "[Loại ảnh: Retrato / Foto Editorial / Foto Executiva] + [Chủ thể: de uma mulher elegante / Feminina] + [Tư thế/Bối cảnh/Điểm nhấn]\n\n"
    "NGÔN NGỮ ĐẦU RA:\n"
    "- Cả 5 Tiêu đề và Nội dung Prompt BẮT BUỘC phải viết bằng: {output_language}.\n\n"
    "ĐỊNH DẠNG TRẢ VỀ (Bắt buộc giữ đúng các nhãn 'Title:' và 'Prompt:'):\n"
    "Title:\n"
    "1. <Tiêu đề 1>\n"
    "2. <Tiêu đề 2>\n"
    "3. <Tiêu đề 3>\n"
    "4. <Tiêu đề 4>\n"
    "5. <Tiêu đề 5>\n\n"
    "Prompt:\n"
    "<Nội dung prompt dài, mô tả cực kỳ chi tiết bằng {output_language}, kết thúc với: Aspect ratio: {aspect_ratio}. --ar {aspect_ratio}>"
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
    """Append or correct aspect ratio tags/descriptions in the prompt based on mode."""
    if not prompt or not aspect_ratio or mode == "none":
        return prompt

    cleaned = prompt.strip()
    ar_tag = f"--ar {aspect_ratio}"
    natural_tag = f"Aspect ratio: {aspect_ratio}"

    # If the prompt already has a mismatching --ar or Aspect ratio (e.g. model generated 2:3 instead of 4:5), replace it
    if re.search(r"--ar\s+\d+:\d+", cleaned, re.IGNORECASE):
        cleaned = re.sub(r"--ar\s+\d+:\d+", ar_tag, cleaned, flags=re.IGNORECASE)
    if re.search(r"aspect\s+ratio:\s*\d+:\d+", cleaned, re.IGNORECASE):
        cleaned = re.sub(r"aspect\s+ratio:\s*\d+:\d+", natural_tag, cleaned, flags=re.IGNORECASE)

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
    language: str = "pt-BR"
    character_description: str = ""
    aspect_ratio_mode: str = DEFAULT_ASPECT_RATIO_MODE
    target_aspect_ratio: str = DEFAULT_TARGET_ASPECT_RATIO
    temperature: float = 0.2
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    overwrite: bool = False
    reference_face_bytes: Optional[bytes] = None
    # OpenAI Image Generation options
    generate_image: bool = False
    image_model: str = DEFAULT_IMAGE_MODEL
    image_quality: str = DEFAULT_IMAGE_QUALITY
    openai_api_key: str = ""
    openai_base_url: str = DEFAULT_OPENAI_BASE_URL


def prepare_prompt(
    prompt: str,
    language: str = "pt-BR",
    character_description: str = "",
    aspect_ratio: str = "",
    width: int = 0,
    height: int = 0,
    aspect_ratio_mode: str = "none",
) -> str:
    """Inject output language, character description, and aspect ratio into the prompt template."""
    lang_name = PROMPT_LANGUAGES.get(language, language)
    p = prompt or DEFAULT_SYSTEM_PROMPT

    if "{output_language}" in p:
        p = p.replace("{output_language}", lang_name)
    elif language.lower() not in ("en", "english"):
        p = (
            f"{p}\n\nImportant Requirement: Both the Titles (SEO names) and the generated image Prompt "
            f"MUST be written entirely in {lang_name}."
        )

    # Character description (optional backward-compatibility if user custom prompt still has {character_description})
    if "{character_description}" in p:
        p = p.replace("{character_description}", character_description)
    elif character_description.strip():
        p = f"{p}\n\nCharacter Guideline: {character_description.strip()}."

    # Aspect ratio
    if "{aspect_ratio}" in p:
        p = p.replace("{aspect_ratio}", aspect_ratio or "4:5")
    elif aspect_ratio and aspect_ratio_mode != "none":
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


def rename_images_to_standard_format(folder: str | Path, recursive: bool = False) -> list[dict[str, str]]:
    """Step 1: Rename all images in folder to image-1.ext, image-2.ext...
    
    Also renames any existing corresponding .txt file (e.g. old_name.txt -> image-1.txt).
    Uses a 2-pass rename with unique temporary names to prevent overwrite collisions.
    Returns list of dicts: [{'old_name': str, 'new_name': str, 'path': str}].
    """
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ImageToPromptError(f"Thư mục không tồn tại: {root}")

    files = scan_image_files(root, recursive=recursive)
    if not files:
        return []

    # Sort files naturally so image1, image2, image10 are ordered properly
    def natural_sort_key(p: Path):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", p.name)]

    files = sorted(files, key=natural_sort_key)

    import uuid
    session_id = uuid.uuid4().hex[:8]

    # Plan renames: (orig_img, temp_img, target_img, orig_txt_opt, temp_txt_opt, target_txt)
    plan = []
    for idx, img_path in enumerate(files, start=1):
        ext = img_path.suffix.lower()
        target_name = f"image-{idx}{ext}"
        target_path = img_path.parent / target_name

        temp_name = f"__pronto_tmp_{session_id}_{idx}__{ext}"
        temp_path = img_path.parent / temp_name

        orig_txt = img_path.with_suffix(".txt")
        has_txt = orig_txt.exists() and orig_txt.is_file()
        temp_txt = img_path.parent / f"__pronto_tmp_{session_id}_{idx}__.txt" if has_txt else None
        target_txt = target_path.with_suffix(".txt")

        plan.append({
            "orig_img": img_path,
            "temp_img": temp_path,
            "target_img": target_path,
            "orig_txt": orig_txt if has_txt else None,
            "temp_txt": temp_txt,
            "target_txt": target_txt,
        })

    # Pass 1: rename all images and corresponding existing .txt to temporary names
    for item in plan:
        item["orig_img"].rename(item["temp_img"])
        if item["orig_txt"] and item["temp_txt"] and item["orig_txt"].exists():
            item["orig_txt"].rename(item["temp_txt"])

    # Pass 2: rename from temporary names to final image-{idx}.ext
    records = []
    for item in plan:
        item["temp_img"].rename(item["target_img"])
        if item["temp_txt"] and item["temp_txt"].exists():
            item["temp_txt"].rename(item["target_txt"])
        records.append({
            "old_name": item["orig_img"].name,
            "new_name": item["target_img"].name,
            "path": str(item["target_img"]),
        })

    return records


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


def clean_multiline_title(text: str) -> str:
    """Clean multiline title section (e.g. 5 SEO titles), preserving numbered list or bullets."""
    raw = (text or "").strip()
    if not raw:
        return ""
    lines = [line.strip() for line in raw.split("\n") if line.strip()]
    if not lines:
        return ""
    if len(lines) == 1:
        return clean_extracted_title(lines[0])

    cleaned_lines = []
    for line in lines:
        l = line.strip()
        # If line is wrapped in bold e.g. **1. Retrato...** -> 1. Retrato...
        if l.startswith("**") and l.endswith("**") and len(l) > 4:
            l = l[2:-2].strip()
        # Remove markdown heading hashes if present
        l = re.sub(r"^#{1,6}\s*", "", l).strip()
        # Strip redundant labels if present on standalone line
        if re.match(
            r"^(?:Image\s*Title|Titles|Title|Tiêu\s*đề(?:\s*ảnh)?|Tên\s*(?:ảnh|hình\s*ảnh)?|Name|Sugestões\s*de\s*Títulos)\s*[:：\-]*(?:\*\*)?\s*$",
            l,
            re.IGNORECASE,
        ):
            continue
        if l:
            cleaned_lines.append(l)

    return "\n".join(cleaned_lines).strip()


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
                title = data.get("title") or data.get("titles") or data.get("name") or data.get("tieu_de") or ""
                if isinstance(title, list):
                    title_str = "\n".join(str(t).strip() for t in title if str(t).strip())
                else:
                    title_str = str(title).strip()
                prompt = str(data.get("prompt") or data.get("description") or "").strip()
                if title_str or prompt:
                    return {
                        "title": clean_multiline_title(title_str) if "\n" in title_str else clean_extracted_title(title_str),
                        "prompt": clean_extracted_prompt_body(prompt),
                    }
        except Exception:
            pass

    # 2. Section matching: Look for Title section and Prompt section
    # Handles: Title:, **Title:**, # Image Title, Sugestões de Títulos:, Prompt:, etc.
    title_header_regex = re.compile(
        r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:Image\s*Title|Titles|Title|Tiêu\s*đề(?:\s*ảnh)?|Tên\s*(?:ảnh|hình\s*ảnh)?|Name|Sugestões\s*de\s*Títulos)"
        r"(?:\s*\([^)]*\))?"
        r"(?:\*\*)?\s*[:：\-]*(?:\*\*)?\s*",
        re.IGNORECASE,
    )
    prompt_header_regex = re.compile(
        r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:MAIN\s*PROMPT|Image\s*Prompt|Prompt|Gợi\s*ý\s*prompt|Mô\s*tả\s*prompt|Nội\s*dung\s*prompt)"
        r"(?:\s*\([^)]*\))?"
        r"(?:\*\*)?\s*[:：\-]*(?:\*\*)?\s*",
        re.IGNORECASE,
    )

    p_match = prompt_header_regex.search(cleaned)
    t_match = title_header_regex.search(cleaned)

    title = ""
    prompt = ""

    if t_match and p_match:
        if t_match.start() < p_match.start():
            raw_title = cleaned[t_match.end() : p_match.start()].strip()
            raw_prompt = cleaned[p_match.end() :].strip()
        else:
            raw_prompt = cleaned[p_match.end() : t_match.start()].strip()
            raw_title = cleaned[t_match.end() :].strip()

        title = clean_multiline_title(raw_title) if "\n" in raw_title else clean_extracted_title(raw_title)
        prompt = clean_extracted_prompt_body(raw_prompt)
        return {"title": title, "prompt": prompt}

    elif p_match:
        pre = cleaned[: p_match.start()].strip()
        raw_prompt = cleaned[p_match.end() :].strip()
        pre = re.sub(
            r"^(?:#{1,3}\s*)?(?:\*\*)?(?:Image\s*Title|Titles|Title|Tiêu\s*đề|Tên\s*ảnh|Name)\s*[:：\-]?(?:\*\*)?\s*",
            "",
            pre,
            flags=re.IGNORECASE,
        ).strip()
        title = clean_multiline_title(pre) if "\n" in pre else clean_extracted_title(pre)
        prompt = clean_extracted_prompt_body(raw_prompt)
        return {"title": title, "prompt": prompt}

    elif t_match:
        after = cleaned[t_match.end() :].strip()
        lines = [ln.strip() for ln in after.split("\n") if ln.strip()]
        if len(lines) == 1:
            title = clean_extracted_title(lines[0])
            prompt = ""
        elif len(lines) <= 5 and any(re.match(r"^\d+[\.\)]", ln) for ln in lines):
            title = clean_multiline_title(after)
            prompt = ""
        else:
            title = clean_extracted_title(lines[0])
            prompt = clean_extracted_prompt_body("\n".join(lines[1:]))
        return {"title": title, "prompt": prompt}

    # Fallback heuristics
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    if not lines:
        return {"title": "", "prompt": ""}
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
        # Check aliases: qwen 3.8 -> qwen3.8:latest, qween -> qwen, match tags
        clean_req = requested_model.lower().replace(" ", "").replace("qween", "qwen").replace(":latest", "")
        for m in available:
            clean_m = m.lower().replace(" ", "").replace(":latest", "")
            if clean_req == clean_m or clean_m.startswith(clean_req) or clean_req in clean_m:
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

    w, h, detected_ar = detect_image_dimensions_and_ratio(image_bytes)
    # If aspect_ratio_mode is 'none', do not imitate physical image aspect ratio
    if config.aspect_ratio_mode == "none":
        aspect_ratio = config.target_aspect_ratio.strip() if (config.target_aspect_ratio and config.target_aspect_ratio.strip().lower() != "auto") else "4:5"
    elif config.target_aspect_ratio and config.target_aspect_ratio.strip().lower() != "auto":
        aspect_ratio = config.target_aspect_ratio.strip()
    else:
        aspect_ratio = detected_ar

    model_to_use = await resolve_model_name(config.model, config.base_url)
    base_prompt = prepare_prompt(
        prompt=config.prompt,
        language=config.language,
        character_description=config.character_description,
        aspect_ratio=aspect_ratio,
        width=w,
        height=h,
        aspect_ratio_mode=config.aspect_ratio_mode,
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


async def generate_image_openai(
    prompt: str,
    api_key: str = "",
    model: str = DEFAULT_IMAGE_MODEL,
    quality: str = DEFAULT_IMAGE_QUALITY,
    base_url: str = DEFAULT_OPENAI_BASE_URL,
    timeout_seconds: float = 180.0,
    size: Optional[str] = None,
) -> bytes:
    """Call OpenAI Images API (/v1/images/generations) to generate image bytes."""
    clean_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    if not clean_key:
        raise ImageToPromptError("Chưa cung cấp OpenAI API Key. Vui lòng nhập OpenAI API Key để tạo ảnh.")

    clean_base = (base_url or os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)).strip().rstrip("/")
    url = f"{clean_base}/images/generations"

    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "model": model or DEFAULT_IMAGE_MODEL,
        "prompt": prompt,
        "quality": quality or DEFAULT_IMAGE_QUALITY,
        "n": 1,
        "response_format": "b64_json",
    }
    if size:
        payload["size"] = size

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("data", [])
                    if not items:
                        raise ImageToPromptError("OpenAI API không trả về hình ảnh nào.")
                    first_item = items[0]
                    if "b64_json" in first_item and first_item["b64_json"]:
                        return base64.b64decode(first_item["b64_json"])
                    if "url" in first_item and first_item["url"]:
                        async with session.get(first_item["url"]) as img_resp:
                            img_resp.raise_for_status()
                            return await img_resp.read()
                    raise ImageToPromptError("Phản hồi từ OpenAI không chứa ảnh b64_json hoặc url.")

                err_text = await resp.text()

                # Some proxies / models reject response_format parameter. Retry without it if rejected.
                if "response_format" in err_text.lower():
                    payload_no_fmt = {k: v for k, v in payload.items() if k != "response_format"}
                    async with session.post(url, headers=headers, json=payload_no_fmt) as retry_resp:
                        if retry_resp.status == 200:
                            retry_data = await retry_resp.json()
                            retry_items = retry_data.get("data", [])
                            if retry_items and "url" in retry_items[0]:
                                async with session.get(retry_items[0]["url"]) as img_resp:
                                    img_resp.raise_for_status()
                                    return await img_resp.read()
                            elif retry_items and "b64_json" in retry_items[0]:
                                return base64.b64decode(retry_items[0]["b64_json"])

                try:
                    err_json = json.loads(err_text)
                    err_msg = err_json.get("error", {}).get("message") or str(err_json)
                except Exception:
                    err_msg = err_text
                raise ImageToPromptError(f"OpenAI API Error ({resp.status}): {err_msg}")

    except asyncio.TimeoutError:
        raise ImageToPromptError(f"Hết thời gian chờ phản hồi tạo ảnh từ OpenAI ({int(timeout_seconds)}s).")
    except aiohttp.ClientConnectorError as exc:
        raise ImageToPromptError(f"Không thể kết nối tới OpenAI API tại {clean_base}: {exc}") from exc
    except ImageToPromptError:
        raise
    except Exception as exc:
        raise ImageToPromptError(f"Lỗi tạo ảnh với OpenAI: {exc}") from exc


def save_result_image(
    image_bytes: bytes,
    original_path: Path,
) -> Path:
    """Save the generated result image as <stem>-result.<ext> alongside original_path."""
    ext = original_path.suffix.lower() if original_path.suffix else ".png"
    target_path = original_path.parent / f"{original_path.stem}-result{ext}"
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            if ext in (".jpg", ".jpeg"):
                if im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                im.save(target_path, format="JPEG", quality=95)
            elif ext == ".webp":
                im.save(target_path, format="WEBP", quality=95)
            elif ext == ".png":
                im.save(target_path, format="PNG")
            else:
                target_path = original_path.parent / f"{original_path.stem}-result.png"
                target_path.write_bytes(image_bytes)
    except Exception:
        target_path.write_bytes(image_bytes)
    return target_path


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
    result_ext = image_path.suffix.lower() if image_path.suffix else ".png"
    expected_result_img = image_path.parent / f"{image_path.stem}-result{result_ext}"

    if txt_path.exists() and not config.overwrite:
        try:
            existing_content = await asyncio.to_thread(txt_path.read_text, encoding="utf-8", errors="replace")
        except Exception:
            existing_content = ""
        parsed = parse_title_and_prompt(existing_content)
        prompt_text = parsed.get("prompt", existing_content)

        # If generate_image is requested and the result image does not exist yet, generate it
        result_img_path_str = str(expected_result_img) if expected_result_img.exists() else None
        img_err = None
        newly_generated_img = False

        if config.generate_image and not expected_result_img.exists() and prompt_text:
            try:
                gen_bytes = await generate_image_openai(
                    prompt=prompt_text,
                    api_key=config.openai_api_key,
                    model=config.image_model,
                    quality=config.image_quality,
                    base_url=config.openai_base_url,
                    timeout_seconds=min(config.timeout_seconds, 300.0),
                )
                saved_path = await asyncio.to_thread(save_result_image, gen_bytes, image_path)
                result_img_path_str = str(saved_path)
                newly_generated_img = True
            except Exception as e:
                img_err = str(e)

        return {
            "status": "ok" if newly_generated_img else "skipped",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "result_image": Path(result_img_path_str).name if result_img_path_str else None,
            "result_image_path": result_img_path_str,
            "image_error": img_err,
            "title": parsed.get("title", ""),
            "prompt": prompt_text,
            "aspect_ratio": ar,
            "width": w,
            "height": h,
            "reason": "Đã tạo ảnh kết quả từ prompt có sẵn" if newly_generated_img else "File .txt đã tồn tại (đã bỏ qua vì không chọn ghi đè)",
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

        if "\n" in title:
            file_content = f"Title:\n{title}\n\nPrompt:\n{prompt_text}\n"
        else:
            file_content = f"Title: {title}\n\nPrompt:\n{prompt_text}\n"
        await asyncio.to_thread(txt_path.write_text, file_content, encoding="utf-8")

        result_img_path_str = None
        img_err = None
        if config.generate_image and prompt_text:
            try:
                gen_bytes = await generate_image_openai(
                    prompt=prompt_text,
                    api_key=config.openai_api_key,
                    model=config.image_model,
                    quality=config.image_quality,
                    base_url=config.openai_base_url,
                    timeout_seconds=min(config.timeout_seconds, 300.0),
                )
                saved_path = await asyncio.to_thread(save_result_image, gen_bytes, image_path)
                result_img_path_str = str(saved_path)
            except Exception as e:
                img_err = str(e)

        return {
            "status": "ok",
            "file": str(image_path),
            "filename": image_path.name,
            "txt_file": str(txt_path),
            "result_image": Path(result_img_path_str).name if result_img_path_str else None,
            "result_image_path": result_img_path_str,
            "image_error": img_err,
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
