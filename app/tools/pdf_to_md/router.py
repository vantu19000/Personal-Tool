"""Router for the PDF → Markdown tool.

Routes
------
- GET  ``/tools/pdf-to-md`` — tool page.
- POST ``/tools/pdf-to-md/convert`` — upload one ``.pdf`` (multipart),
  returns the Markdown result: a single ``.md`` file when the PDF has at
  most ``pages_per_file`` pages, otherwise a ``.zip`` containing all parts.
- POST ``/tools/pdf-to-md/folder`` — convert every ``.pdf`` in a source
  folder into an output folder (local paths, form fields), returns JSON.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from urllib.parse import quote

import anyio
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app.core import settings_store
from app.core.templates import templates
from app.tools.pdf_to_md import services

MAX_PDF_BYTES = 200 * 1024 * 1024  # 200 MB upload limit

router = APIRouter(tags=["pdf-to-md"])


def _default_pages_per_file() -> int:
    try:
        value = int(settings_store.get_block("pdf_to_md")["pages_per_file"])
    except (KeyError, TypeError, ValueError):
        return 10
    return max(1, min(value, services.MAX_PAGES_PER_FILE))


def _attachment_header(filename: str) -> str:
    """RFC 5987 safe header so Vietnamese filenames survive the transfer."""
    return f"attachment; filename*=UTF-8''{quote(filename)}"


@router.get("/pdf-to-md", name="pdf_to_md")
async def pdf_to_md_page(request: Request):
    """Render the tool page."""
    return templates.TemplateResponse(
        request,
        "tools/pdf_to_md.html",
        {
            "active_tool": "pdf-to-md",
            "pages_per_file": _default_pages_per_file(),
        },
    )


@router.post("/pdf-to-md/convert")
async def convert_upload(
    request: Request,
    file: UploadFile = File(...),
    pages_per_file: int | None = Form(None),
):
    """Convert one uploaded PDF and return the Markdown (.md or .zip)."""
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ nhận file .pdf (mỗi lần một file).")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File PDF trống (0 byte).")
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="File PDF quá lớn (tối đa 200 MB).")

    n = _default_pages_per_file() if pages_per_file is None else pages_per_file

    try:
        parts = await anyio.to_thread.run_sync(
            services.convert_pdf_bytes, content, n, filename
        )
    except services.PdfConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    base_stem = services._sanitize_stem(Path(filename).stem)

    if len(parts) == 1:
        return Response(
            parts[0]["content"].encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": _attachment_header(parts[0]["name"])},
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for part in parts:
            zf.writestr(part["name"], part["content"])
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
    pages_per_file: int | None = Form(None),
) -> JSONResponse:
    """Batch-convert every ``.pdf`` in a source folder into an output folder."""
    src = (source_folder or "").strip()
    out = (output_folder or "").strip()
    if not src:
        raise HTTPException(status_code=400, detail="Vui lòng nhập thư mục nguồn.")
    if not out:
        raise HTTPException(status_code=400, detail="Vui lòng nhập thư mục đích.")

    n = _default_pages_per_file() if pages_per_file is None else pages_per_file

    def _run() -> dict:
        return services.convert_folder(Path(src), Path(out), n)

    try:
        result = await anyio.to_thread.run_sync(_run)
    except services.PdfConversionError as exc:
        return JSONResponse(
            {"ok": 0, "failed": 0, "total": 0, "errors": [{"file": "-", "error": str(exc)}]},
            status_code=400,
        )
    except Exception as exc:
        return JSONResponse(
            {"ok": 0, "failed": 0, "total": 0, "errors": [{"file": "-", "error": f"Lỗi không xác định: {exc}"}]},
            status_code=500,
        )

    if result["failed"] == result["total"]:
        return JSONResponse(result, status_code=500)
    return JSONResponse(result)
