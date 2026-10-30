"""Router for Image Compressor tool.

Provides:
- GET  /tools/image-compressor                : Web UI page
- POST /tools/image-compressor/compress-files : Batch upload & compress
- GET  /tools/image-compressor/download/{batch_id}/{file_idx} : Download single file
- GET  /tools/image-compressor/download-zip/{batch_id}        : Download all as ZIP
- POST /tools/image-compressor/browse-folder  : Native Windows folder picker
- POST /tools/image-compressor/scan-folder    : Scan images in directory
- POST /tools/image-compressor/compress-folder: In-place compress with backup
- POST /tools/image-compressor/open-folder    : Open directory in File Explorer
"""
from __future__ import annotations

import base64
import io
import os
import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.core.templates import templates
from app.tools.image_compressor import services

router = APIRouter()

_FILE_PART_RE = re.compile(r"^file(?:_)?(\d+)?$")


def _is_upload_file(value: object) -> bool:
    return (
        type(value).__name__ == "UploadFile"
        and hasattr(value, "read")
        and hasattr(value, "filename")
    )


def _collect_upload_files(form) -> list:
    """Collect all uploaded files regardless of field name (file, files, file_0, ...)."""
    uploads: list[tuple[int, object]] = []
    counter = 0
    for key, value in form.multi_items():
        if not _is_upload_file(value):
            continue
        key_str = str(key)
        match = _FILE_PART_RE.match(key_str)
        if match and match.group(1):
            idx = int(match.group(1))
        else:
            idx = counter
        counter += 1
        uploads.append((idx, value))
    return [v for _, v in sorted(uploads, key=lambda x: x[0])]


def _make_thumbnail_base64(image_bytes: bytes, max_size: int = 120) -> str:
    """Generate small base64 thumbnail for preview."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as img:
            img.thumbnail((max_size, max_size))
            thumb_io = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img.save(thumb_io, format="PNG")
                mime = "image/png"
            else:
                img.save(thumb_io, format="JPEG", quality=70)
                mime = "image/jpeg"
            b64_str = base64.b64encode(thumb_io.getvalue()).decode("ascii")
            return f"data:{mime};base64,{b64_str}"
    except Exception:
        return ""


@router.get("/image-compressor", name="image-compressor")
async def image_compressor_page(request: Request):
    """Render Image Compressor page."""
    return templates.TemplateResponse(
        request,
        "tools/image_compressor.html",
        {
            "active_tool": "image-compressor",
            "default_quality": 20,
            "supported_extensions": sorted(list(services.SUPPORTED_EXTENSIONS)),
        },
    )


@router.post("/image-compressor/compress-files", name="image-compressor-compress-files")
async def compress_files(request: Request):
    """Compress multiple uploaded image files."""
    form = await request.form()
    raw_quality = form.get("quality") or 20
    try:
        quality = int(raw_quality)
        quality = max(1, min(100, quality))
    except (ValueError, TypeError):
        quality = 20

    files = _collect_upload_files(form)
    if not files:
        return {"success": False, "error": "Chưa chọn tệp ảnh nào để nén."}

    compressed_list = []
    total_orig = 0
    total_comp = 0

    for idx, upload_file in enumerate(files):
        filename = getattr(upload_file, "filename", f"image_{idx}.jpg") or f"image_{idx}.jpg"
        content = await upload_file.read()
        if not content:
            continue

        try:
            comp_bytes, fmt, orig_size, comp_size = services.compress_image_bytes(
                content,
                filename=filename,
                quality=quality,
            )
            saved_bytes = max(0, orig_size - comp_size)
            saved_pct = (
                round((saved_bytes / orig_size) * 100, 1) if orig_size > 0 else 0.0
            )

            total_orig += orig_size
            total_comp += comp_size

            # Generate preview thumbnail
            thumb_data = _make_thumbnail_base64(comp_bytes)

            compressed_list.append({
                "idx": len(compressed_list),
                "filename": filename,
                "data": comp_bytes,
                "orig_size": orig_size,
                "orig_size_human": services.format_file_size(orig_size),
                "comp_size": comp_size,
                "comp_size_human": services.format_file_size(comp_size),
                "saved_bytes": saved_bytes,
                "saved_bytes_human": services.format_file_size(saved_bytes),
                "saved_pct": saved_pct,
                "format": fmt,
                "thumbnail": thumb_data,
                "status": "success",
            })
        except Exception as exc:
            compressed_list.append({
                "idx": len(compressed_list),
                "filename": filename,
                "data": None,
                "orig_size": len(content),
                "orig_size_human": services.format_file_size(len(content)),
                "comp_size": len(content),
                "comp_size_human": services.format_file_size(len(content)),
                "saved_bytes": 0,
                "saved_bytes_human": "0 B",
                "saved_pct": 0.0,
                "format": "N/A",
                "thumbnail": "",
                "status": "error",
                "error": str(exc),
            })

    # Store batch in memory cache
    batch_id = services.store_batch(compressed_list)

    # Prepare response payload (strip raw data bytes)
    response_files = [
        {k: v for k, v in item.items() if k != "data"}
        for item in compressed_list
    ]

    total_saved_bytes = max(0, total_orig - total_comp)
    total_saved_pct = (
        round((total_saved_bytes / total_orig) * 100, 1) if total_orig > 0 else 0.0
    )

    return {
        "success": True,
        "batch_id": batch_id,
        "quality": quality,
        "total_files": len(files),
        "total_orig_size": total_orig,
        "total_orig_human": services.format_file_size(total_orig),
        "total_comp_size": total_comp,
        "total_comp_human": services.format_file_size(total_comp),
        "total_saved_bytes": total_saved_bytes,
        "total_saved_human": services.format_file_size(total_saved_bytes),
        "total_saved_pct": total_saved_pct,
        "files": response_files,
    }


@router.get("/image-compressor/download/{batch_id}/{file_idx}", name="image-compressor-download-file")
async def download_single_file(batch_id: str, file_idx: int):
    """Download single compressed image."""
    batch = services.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Phiên nén đã hết hạn hoặc không tồn tại.")

    files = batch.get("files", [])
    if file_idx < 0 or file_idx >= len(files):
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp.")

    target = files[file_idx]
    data = target.get("data")
    if not data:
        raise HTTPException(status_code=400, detail="Tệp tin bị lỗi trong lúc nén.")

    filename = target.get("filename") or f"compressed_{file_idx}.jpg"
    quoted_name = quote(filename)

    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_name}",
        },
    )


@router.get("/image-compressor/download-zip/{batch_id}", name="image-compressor-download-zip")
async def download_all_zip(batch_id: str):
    """Download all compressed images from batch in a ZIP file."""
    batch = services.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Phiên nén đã hết hạn hoặc không tồn tại.")

    files = batch.get("files", [])
    zip_bytes = services.create_zip_archive(files)

    zip_filename = f"compressed_images_{batch_id[:8]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{zip_filename}",
        },
    )


@router.post("/image-compressor/browse-folder", name="image-compressor-browse-folder")
async def browse_folder():
    """Trigger native folder dialog and return selected path."""
    selected = await services.pick_folder_dialog()
    return {"success": True, "folder": selected}


class ScanFolderRequest(BaseModel):
    folder_path: str = Field(..., description="Đường dẫn thư mục")
    recursive: bool = Field(True, description="Quét cả thư mục con")


@router.post("/image-compressor/scan-folder", name="image-compressor-scan-folder")
async def scan_folder(payload: ScanFolderRequest):
    """Scan folder for eligible images and calculate initial stats."""
    folder = payload.folder_path.strip()
    if not folder:
        return {"success": False, "error": "Vui lòng nhập đường dẫn thư mục."}

    try:
        images = services.scan_directory_images(folder, recursive=payload.recursive)
        total_size = sum(img["size"] for img in images)
        backup_dir = os.path.join(folder, "backup")

        return {
            "success": True,
            "folder_path": folder,
            "backup_dir": backup_dir,
            "count": len(images),
            "total_size": total_size,
            "total_size_human": services.format_file_size(total_size),
            "preview_files": images[:15],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


class CompressFolderRequest(BaseModel):
    folder_path: str = Field(..., description="Đường dẫn thư mục")
    quality: int = Field(20, ge=1, le=100, description="Tỷ lệ nén % từ 1-100")
    recursive: bool = Field(True, description="Quét cả thư mục con")


@router.post("/image-compressor/compress-folder", name="image-compressor-compress-folder")
async def compress_folder_endpoint(payload: CompressFolderRequest):
    """Compress all images in target directory, moving originals to backup/ and replacing them."""
    folder = payload.folder_path.strip()
    if not folder:
        return {"success": False, "error": "Vui lòng nhập đường dẫn thư mục."}

    try:
        summary = services.compress_directory(
            folder_path=folder,
            quality=payload.quality,
            recursive=payload.recursive,
        )
        return {"success": True, "data": summary}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


class OpenFolderRequest(BaseModel):
    folder_path: str = Field(..., description="Đường dẫn thư mục cần mở")


@router.post("/image-compressor/open-folder", name="image-compressor-open-folder")
async def open_folder_in_explorer(payload: OpenFolderRequest):
    """Open folder in Windows Explorer."""
    folder = payload.folder_path.strip()
    if not folder or not os.path.exists(folder):
        return {"success": False, "error": "Thư mục không tồn tại."}

    try:
        os.startfile(folder)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": f"Không thể mở thư mục: {exc}"}
