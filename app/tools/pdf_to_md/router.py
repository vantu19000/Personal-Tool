"""Router for the PDF → Markdown tool.

Routes
------
- GET  ``/tools/pdf-to-md`` — tool page.
- POST ``/tools/pdf-to-md/convert`` — upload one ``.pdf`` (multipart),
  returns the Markdown result: a single ``.md`` file when the PDF has at
  most ``pages_per_file`` pages and no external images, otherwise a ``.zip``
  containing the Markdown part(s) and the ``images/`` folder.
- POST ``/tools/pdf-to-md/folder`` — convert every ``.pdf`` in a source
  folder into an output folder with image assets, returns JSON.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote
import zipfile

import anyio
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app.core import settings_store
from app.core.templates import templates
from app.tools.pdf_to_md import services

MAX_PDF_BYTES = 200 * 1024 * 1024  # 200 MB upload limit

router = APIRouter(tags=["pdf-to-md"])


def _get_pdf_settings() -> Dict[str, Any]:
    """Retrieve effective default settings for the PDF-to-MD tool."""
    defaults = {
        "pages_per_file": 10,
        "extract_images": True,
        "image_embed_mode": "folder",
        "ocr_mode": "auto",
        "ollama_model": "llama3.2-vision",
        "gemini_api_key": "",
    }
    stored = settings_store.get_block("pdf_to_md")
    defaults.update(stored)
    try:
        defaults["pages_per_file"] = max(
            1, min(int(defaults["pages_per_file"]), services.MAX_PAGES_PER_FILE)
        )
    except (TypeError, ValueError):
        defaults["pages_per_file"] = 10
    return defaults


def _attachment_header(filename: str) -> str:
    """RFC 5987 safe header so Vietnamese filenames survive the transfer."""
    return f"attachment; filename*=UTF-8''{quote(filename)}"


@router.get("/pdf-to-md", name="pdf_to_md")
async def pdf_to_md_page(request: Request):
    """Render the tool page."""
    cfg = _get_pdf_settings()
    return templates.TemplateResponse(
        request,
        "tools/pdf_to_md.html",
        {
            "active_tool": "pdf-to-md",
            "pages_per_file": cfg["pages_per_file"],
            "cfg": cfg,
        },
    )


@router.post("/pdf-to-md/convert")
async def convert_upload(
    request: Request,
    file: UploadFile = File(...),
    pages_per_file: Optional[int] = Form(None),
    extract_images: Optional[str] = Form(None),
    image_embed_mode: Optional[str] = Form(None),
    ocr_mode: Optional[str] = Form(None),
    ollama_model: Optional[str] = Form(None),
    gemini_api_key: Optional[str] = Form(None),
):
    """Convert one uploaded PDF and return the Markdown (.md or .zip)."""
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Chỉ nhận file .pdf (mỗi lần một file)."
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File PDF trống (0 byte).")
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413, detail="File PDF quá lớn (tối đa 200 MB)."
        )

    cfg = _get_pdf_settings()
    n = cfg["pages_per_file"] if pages_per_file is None else pages_per_file

    # Determine extract_images flag
    if extract_images is None:
        do_extract = bool(cfg.get("extract_images", True))
    else:
        do_extract = extract_images.lower() in ("true", "1", "on", "yes")

    embed_mode = (image_embed_mode or cfg.get("image_embed_mode", "folder")).strip().lower()
    if embed_mode not in ("folder", "base64"):
        embed_mode = "folder"

    eff_ocr_mode = (ocr_mode or cfg.get("ocr_mode", "auto")).strip().lower()
    eff_ollama_model = (
        ollama_model if ollama_model is not None else cfg.get("ollama_model", "llama3.2-vision")
    ).strip()
    eff_gemini_key = (
        gemini_api_key if gemini_api_key is not None else cfg.get("gemini_api_key", "")
    ).strip()

    try:
        result = await anyio.to_thread.run_sync(
            lambda: services.convert_pdf_bytes(
                data=content,
                pages_per_file=n,
                source_name=filename,
                extract_images=do_extract,
                image_embed_mode=embed_mode,
                ocr_mode=eff_ocr_mode,
                ollama_model=eff_ollama_model,
                gemini_api_key=eff_gemini_key,
            )
        )
    except services.PdfConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    base_stem = services._sanitize_stem(Path(filename).stem)

    # If single part and no external images to deliver, return pure .md
    if len(result.parts) == 1 and not result.images:
        return Response(
            result.parts[0]["content"].encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": _attachment_header(result.parts[0]["name"])},
        )

    # Deliver bundle as .zip (contains .md file(s) and images/ folder)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for part in result.parts:
            zf.writestr(part["name"], part["content"])
        for rel_path, img_bytes in result.images.items():
            zf.writestr(rel_path, img_bytes)

    zip_name = f"{base_stem}_markdown.zip"
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": _attachment_header(zip_name)},
    )


@router.post("/pdf-to-md/folder")
async def convert_folder(
    request: Request,
    source_folder: str = Form(...),
    output_folder: str = Form(...),
    pages_per_file: Optional[int] = Form(None),
    extract_images: Optional[str] = Form(None),
    image_embed_mode: Optional[str] = Form(None),
    ocr_mode: Optional[str] = Form(None),
    ollama_model: Optional[str] = Form(None),
    gemini_api_key: Optional[str] = Form(None),
) -> JSONResponse:
    """Batch-convert every ``.pdf`` in a source folder into an output folder."""
    src = (source_folder or "").strip()
    out = (output_folder or "").strip()
    if not src:
        raise HTTPException(status_code=400, detail="Vui lòng nhập thư mục nguồn.")
    if not out:
        raise HTTPException(status_code=400, detail="Vui lòng nhập thư mục đích.")

    cfg = _get_pdf_settings()
    n = cfg["pages_per_file"] if pages_per_file is None else pages_per_file

    if extract_images is None:
        do_extract = bool(cfg.get("extract_images", True))
    else:
        do_extract = extract_images.lower() in ("true", "1", "on", "yes")

    embed_mode = (image_embed_mode or cfg.get("image_embed_mode", "folder")).strip().lower()
    if embed_mode not in ("folder", "base64"):
        embed_mode = "folder"

    eff_ocr_mode = (ocr_mode or cfg.get("ocr_mode", "auto")).strip().lower()
    eff_ollama_model = (
        ollama_model if ollama_model is not None else cfg.get("ollama_model", "llama3.2-vision")
    ).strip()
    eff_gemini_key = (
        gemini_api_key if gemini_api_key is not None else cfg.get("gemini_api_key", "")
    ).strip()

    def _run() -> dict:
        return services.convert_folder(
            source_folder=Path(src),
            output_folder=Path(out),
            pages_per_file=n,
            extract_images=do_extract,
            image_embed_mode=embed_mode,
            ocr_mode=eff_ocr_mode,
            ollama_model=eff_ollama_model,
            gemini_api_key=eff_gemini_key,
        )

    try:
        result = await anyio.to_thread.run_sync(_run)
    except services.PdfConversionError as exc:
        return JSONResponse(
            {
                "ok": 0,
                "failed": 0,
                "total": 0,
                "errors": [{"file": "-", "error": str(exc)}],
            },
            status_code=400,
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": 0,
                "failed": 0,
                "total": 0,
                "errors": [{"file": "-", "error": f"Lỗi không xác định: {exc}"}],
            },
            status_code=500,
        )

    if result["failed"] == result["total"]:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)
