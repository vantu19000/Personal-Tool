"""Router for the SRT Translator tool.

GET  /tools/srt-translator           — form page (upload, model, target language)
GET  /tools/srt-translator/models    — models available on local Ollama (/api/tags)
POST /tools/srt-translator/translate — runs the translation via Ollama and
                                       streams the translated .srt back as a
                                       download (``<name>.<code>.srt``).
POST /tools/srt-translator/folder    — batch mode: translates every .srt in a
                                       local source folder into an output folder,
                                       streaming NDJSON progress events.
GET  /tools/srt-translator/folder/scan — lists the .srt files under a folder.
"""
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
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


@router.get("/srt-translator/models", name="srt-translator-models")
async def srt_translator_models() -> JSONResponse:
    """List models available on the local Ollama instance (web UI select).

    Returns ``{"online": bool, "models": [names...], "default": name}``.
    Ollama being offline is not an HTTP error — the UI falls back to the
    default model instead.
    """
    try:
        models = await services.list_ollama_models()
    except services.SRTTranslationError:
        return JSONResponse(
            {"online": False, "models": [], "default": services.DEFAULT_MODEL}
        )
    return JSONResponse(
        {"online": True, "models": models, "default": services.DEFAULT_MODEL}
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


# ---------------------------------------------------------------------------
# Batch mode — translate every .srt in a local source folder into an output
# folder. Files are processed one by one (Ollama is a single local worker);
# progress is streamed back as NDJSON events so the UI can show a live list.
# ---------------------------------------------------------------------------


@router.get("/srt-translator/folder/scan", name="srt-translator-folder-scan")
async def srt_translator_folder_scan(source: str = Query(..., description="Đường dẫn thư mục nguồn")) -> JSONResponse:
    """List the .srt files found under a local folder (UI preview before starting)."""
    if not source or not source.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập thư mục nguồn.")
    root = Path(source).expanduser()
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"Thư mục không tồn tại: {root}")
    files = services.scan_srt_files(root, recursive=True)
    return JSONResponse({"count": len(files), "files": [str(f) for f in files]})


@router.post("/srt-translator/folder", name="srt-translator-folder")
async def srt_translator_folder(
    source_folder: str = Form(..., description="Thư mục nguồn chứa file .srt"),
    output_folder: str = Form(..., description="Thư mục đích để ghi kết quả"),
    model: str = Form(services.DEFAULT_MODEL),
    target: str = Form("vi"),
):
    """Translate every ``.srt`` under *source_folder* into *output_folder*.

    Streams NDJSON progress events (one line per file as it finishes) and
    ends with a ``done`` event summarising ok/failed counts.
    """
    if target not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Ngôn ngữ đích không hợp lệ: {target}")
    if not model or not model.strip():
        raise HTTPException(status_code=400, detail="Tên model không được để trống.")
    if not source_folder or not source_folder.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập thư mục nguồn.")
    if not output_folder or not output_folder.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập thư mục đích.")

    src = Path(source_folder).expanduser()
    out = Path(output_folder).expanduser()
    if not src.is_dir():
        raise HTTPException(status_code=400, detail=f"Thư mục nguồn không tồn tại: {src}")
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Không tạo được thư mục đích {out}: {exc}")

    files = services.scan_srt_files(src, recursive=True)
    if not files:
        raise HTTPException(status_code=400, detail=f"Không tìm thấy file .srt nào trong {src}")

    target_language, target_code = LANGUAGES[target]
    config = services.TranslationConfig(
        model=model.strip(),
        target_language=target_language,
        target_code=target_code,
    )
    total = len(files)

    # Per-file results land in this queue as translate_files finishes each file.
    queue: asyncio.Queue = asyncio.Queue()

    def on_file_done(entry: dict) -> None:
        queue.put_nowait(entry)

    async def event_stream():
        def line(obj: dict) -> str:
            return json.dumps(obj, ensure_ascii=False) + "\n"

        yield line({"type": "start", "total": total, "files": [str(f) for f in files]})
        task = asyncio.ensure_future(
            services.translate_files(src, out, config=config, on_file_done=on_file_done)
        )
        ok = failed = 0
        try:
            for index in range(total):
                entry = await queue.get()
                is_ok = entry.get("status") == "ok"
                ok += int(is_ok)
                failed += int(not is_ok)
                evt = {"type": "file_done" if is_ok else "file_error", "index": index + 1, **entry}
                yield line(evt)
            # Surface any unexpected pipeline error (per-file errors are already caught).
            await task
            yield line({"type": "done", "total": total, "ok": ok, "failed": failed, "output_folder": str(out)})
        finally:
            # Client disconnected mid-run: stop translating, keep finished files.
            if not task.done():
                task.cancel()

    return StreamingResponse(event_stream(), media_type="application/x-ndjson; charset=utf-8")
