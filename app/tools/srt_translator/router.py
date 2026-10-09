"""Router for the SRT Translator tool.

GET  /tools/srt-translator          — form page (upload, model, target language)
POST /tools/srt-translator/translate — runs the translation via Ollama and
                                       streams the translated .srt back as a
                                       download (``<name>.<code>.srt``).
"""
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
import pysrt

from app.core.templates import templates
from app.tools.srt_translator import services

router = APIRouter()

# Target languages offered in the form: code -> (label, filename suffix)
LANGUAGES = {
    "vi": ("Tiếng Việt", "vi"),
    "en": ("English", "en"),
    "ja": ("Tiếng Nhật", "ja"),
    "ko": ("Tiếng Hàn", "ko"),
    "zh": ("Tiếng Trung", "zh"),
    "fr": ("Tiếng Pháp", "fr"),
    "de": ("Tiếng Đức", "de"),
    "es": ("Tiếng Tây Ban Nha", "es"),
}


@router.get("/srt-translator", name="srt-translator")
async def srt_translator(request: Request):
    return templates.TemplateResponse(
        request,
        "tools/srt_translator.html",
        {
            "active_tool": "srt-translator",
            "languages": LANGUAGES,
            "default_model": services.DEFAULT_MODEL,
        },
    )


@router.post("/srt-translator/translate", name="srt-translator-translate")
async def srt_translator_translate(
    file: UploadFile = File(..., description="File phụ đề .srt"),
    model: str = Form(services.DEFAULT_MODEL),
    target: str = Form("vi"),
):
    """Translate one uploaded .srt file and return it as a download."""
    if target not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Ngôn ngữ đích không hợp lệ: {target}")
    if not model or not model.strip():
        raise HTTPException(status_code=400, detail="Tên model không được để trống.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="File trống — không có nội dung để dịch.")

    # Tolerate common encodings of wild SRT files (BOM, Windows-1258, cp1252...).
    text = None
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="Không đọc được nội dung file (định dạng ký tự).")

    # NOTE: use pysrt.from_string — SubRipFile(str) in this pysrt version
    # merely creates a list of characters, it does NOT parse the SRT text.
    subs = pysrt.from_string(text)
    if not len(subs):
        raise HTTPException(status_code=400, detail="File không có phụ đề SRT hợp lệ nào.")

    target_language, target_code = LANGUAGES[target]
    config = services.TranslationConfig(
        model=model.strip(),
        target_language=target_language,
        target_code=target_code,
    )

    try:
        translated = await services.translate_subtitles(subs, config)
    except services.SRTTranslationError as exc:
        raise HTTPException(status_code=502, detail=f"Dịch thất bại: {exc}")

    stem = (file.filename or "subtitles").rsplit("/", 1)[-1]
    if stem.lower().endswith(".srt"):
        stem = stem[:-4]
    out_name = f"{stem}.{target_code}.srt"

    # Serialize each SubRipItem (str(item) = "index\ntimestamp\ntext\n") back
    # into a standard SRT document.
    srt_text = "\n".join(str(item) for item in translated).strip() + "\n"
    return Response(
        content=srt_text,
        media_type="application/x-subrip; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )
