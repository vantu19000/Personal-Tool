"""Services for Image Compressor tool.

Handles:
- Image compression for multiple formats (JPEG, PNG, WebP, BMP, TIFF) with quality 1-100%.
- Directory scanning, backup preservation, and in-place replacement.
- Temporary storage for batch uploads and zip generation.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
import zipfile

from PIL import Image, ImageOps

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

# In-memory batch storage for multi-file downloads.
# Format: { batch_id: { "created_at": float, "files": [ {"filename": str, "data": bytes, "size": int, ...} ] } }
_BATCH_CACHE: Dict[str, Dict[str, Any]] = {}
_BATCH_TTL_SECONDS = 3600  # 1 hour


def _clean_old_batches() -> None:
    """Evict expired batches from memory."""
    now = time.time()
    expired = [
        bid
        for bid, data in _BATCH_CACHE.items()
        if now - data.get("created_at", 0) > _BATCH_TTL_SECONDS
    ]
    for bid in expired:
        _BATCH_CACHE.pop(bid, None)


def store_batch(files_data: List[Dict[str, Any]]) -> str:
    """Save compressed batch to cache and return unique batch_id."""
    _clean_old_batches()
    batch_id = uuid.uuid4().hex
    _BATCH_CACHE[batch_id] = {
        "created_at": time.time(),
        "files": files_data,
    }
    return batch_id


def get_batch(batch_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve batch by ID."""
    _clean_old_batches()
    return _BATCH_CACHE.get(batch_id)


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def is_image_file(path_or_filename: str) -> bool:
    """Check if file has a supported image extension."""
    ext = os.path.splitext(path_or_filename)[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def compress_image_bytes(
    input_bytes: bytes,
    filename: str,
    quality: int = 20,
) -> Tuple[bytes, str, int, int]:
    """Compress image bytes given a quality ratio (1 to 100, integer).

    Returns:
        (compressed_bytes, format_name, original_size, compressed_size)
    """
    quality = max(1, min(100, int(quality)))
    orig_size = len(input_bytes)

    if orig_size == 0:
        raise ValueError("Tệp tin rỗng.")

    ext = os.path.splitext(filename)[1].lower()

    try:
        with Image.open(io.BytesIO(input_bytes)) as img:
            # Normalize EXIF orientation if available
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            output_io = io.BytesIO()
            save_format = ""

            if ext in (".jpg", ".jpeg"):
                save_format = "JPEG"
                if img.mode in ("RGBA", "LA", "P"):
                    # Create background for alpha if RGBA
                    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    if img.mode in ("RGBA", "LA"):
                        rgb_img.paste(img, mask=img.split()[-1])
                    else:
                        rgb_img.paste(img)
                    img = rgb_img
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                img.save(
                    output_io,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )

            elif ext == ".webp":
                save_format = "WEBP"
                img.save(
                    output_io,
                    format="WEBP",
                    quality=quality,
                    method=6,
                )

            elif ext == ".png":
                save_format = "PNG"
                if quality < 100:
                    try:
                        # Palette color reduction based on quality percentage
                        colors = max(16, min(256, int(256 * (quality / 100.0))))
                        quantized = img.quantize(
                            colors=colors,
                            method=Image.Quantize.MEDIANCUT,
                            dither=Image.Dither.FLOYDSTEINBERG,
                        )
                        quantized.save(
                            output_io,
                            format="PNG",
                            optimize=True,
                            compress_level=9,
                        )
                    except Exception:
                        img.save(
                            output_io,
                            format="PNG",
                            optimize=True,
                            compress_level=9,
                        )
                else:
                    img.save(
                        output_io,
                        format="PNG",
                        optimize=True,
                        compress_level=9,
                    )

            elif ext in (".bmp",):
                save_format = "BMP"
                img.save(output_io, format="BMP")

            elif ext in (".tiff", ".tif"):
                save_format = "TIFF"
                img.save(
                    output_io,
                    format="TIFF",
                    compression="tiff_lzw",
                    quality=quality,
                )

            else:
                # Default fallback using img.format
                save_format = (img.format or "JPEG").upper()
                if save_format in ("JPEG", "JPG"):
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(
                        output_io,
                        format="JPEG",
                        quality=quality,
                        optimize=True,
                    )
                else:
                    img.save(output_io, format=save_format, optimize=True)

            compressed_bytes = output_io.getvalue()
            comp_size = len(compressed_bytes)

            # If compression ended up larger (e.g. at 99-100% on already compressed image),
            # keep original to prevent file growth
            if comp_size > orig_size:
                return input_bytes, save_format, orig_size, orig_size

            return compressed_bytes, save_format, orig_size, comp_size

    except Exception as exc:
        raise RuntimeError(f"Lỗi khi nén ảnh {filename}: {exc}") from exc


def scan_directory_images(
    folder_path: str,
    recursive: bool = True,
    backup_folder_name: str = "backup",
) -> List[Dict[str, Any]]:
    """Scan directory for supported image files, excluding the backup folder."""
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Thư mục không tồn tại: {folder_path}")
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Đường dẫn không phải là thư mục: {folder_path}")

    folder_path = os.path.abspath(folder_path)
    backup_path = os.path.abspath(os.path.join(folder_path, backup_folder_name))

    found_files: List[Dict[str, Any]] = []

    if recursive:
        for root, dirs, files in os.walk(folder_path):
            # Do not traverse into backup folder
            abs_root = os.path.abspath(root)
            if abs_root == backup_path or abs_root.startswith(backup_path + os.sep):
                continue
            # Filter subdirs in-place so os.walk avoids backup
            dirs[:] = [
                d
                for d in dirs
                if os.path.abspath(os.path.join(root, d)) != backup_path
                and d not in (".git", ".svn", "__pycache__", "node_modules")
            ]

            for fname in files:
                if is_image_file(fname):
                    full_file = os.path.join(root, fname)
                    try:
                        fsize = os.path.getsize(full_file)
                        rel_path = os.path.relpath(full_file, folder_path)
                        found_files.append({
                            "path": full_file,
                            "rel_path": rel_path,
                            "filename": fname,
                            "size": fsize,
                            "size_human": format_file_size(fsize),
                        })
                    except OSError:
                        continue
    else:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file() and is_image_file(entry.name):
                    try:
                        fsize = entry.stat().st_size
                        found_files.append({
                            "path": entry.path,
                            "rel_path": entry.name,
                            "filename": entry.name,
                            "size": fsize,
                            "size_human": format_file_size(fsize),
                        })
                    except OSError:
                        continue

    return sorted(found_files, key=lambda x: x["rel_path"].lower())


def compress_directory(
    folder_path: str,
    quality: int = 20,
    recursive: bool = True,
    backup_folder_name: str = "backup",
) -> Dict[str, Any]:
    """Compress all images in folder.
    
    For each image:
    1. Compress into temporary file.
    2. Move original image into backup directory (preserving relative path).
    3. Replace original file with compressed file.
    """
    quality = max(1, min(100, int(quality)))
    folder_path = os.path.abspath(folder_path)
    backup_dir = os.path.abspath(os.path.join(folder_path, backup_folder_name))
    os.makedirs(backup_dir, exist_ok=True)

    images = scan_directory_images(
        folder_path=folder_path,
        recursive=recursive,
        backup_folder_name=backup_folder_name,
    )

    results: List[Dict[str, Any]] = []
    total_orig_size = 0
    total_new_size = 0
    success_count = 0
    failed_count = 0

    for item in images:
        full_path = item["path"]
        rel_path = item["rel_path"]
        filename = item["filename"]
        orig_size = item["size"]
        total_orig_size += orig_size

        temp_compressed = full_path + f".tmp_{uuid.uuid4().hex[:8]}.compress"
        backup_dest = os.path.join(backup_dir, rel_path)

        try:
            # 1. Read and compress
            with open(full_path, "rb") as f:
                raw_bytes = f.read()

            comp_bytes, fmt, _, new_size = compress_image_bytes(
                raw_bytes,
                filename=filename,
                quality=quality,
            )

            # Write compressed output to temp file
            with open(temp_compressed, "wb") as f_tmp:
                f_tmp.write(comp_bytes)

            # 2. Ensure backup target folder exists and move original file there
            os.makedirs(os.path.dirname(backup_dest), exist_ok=True)
            if os.path.exists(backup_dest):
                # If backup file already exists, overwrite or keep
                os.remove(backup_dest)
            shutil.move(full_path, backup_dest)

            # 3. Move compressed temp file to target path
            shutil.move(temp_compressed, full_path)

            total_new_size += new_size
            success_count += 1
            saved_bytes = max(0, orig_size - new_size)
            saved_pct = (
                round((saved_bytes / orig_size) * 100, 1) if orig_size > 0 else 0.0
            )

            results.append({
                "filename": filename,
                "rel_path": rel_path,
                "orig_size": orig_size,
                "orig_size_human": format_file_size(orig_size),
                "new_size": new_size,
                "new_size_human": format_file_size(new_size),
                "saved_bytes": saved_bytes,
                "saved_bytes_human": format_file_size(saved_bytes),
                "saved_pct": saved_pct,
                "status": "success",
                "backup_path": os.path.relpath(backup_dest, folder_path),
            })

        except Exception as exc:
            # Clean up temp file if created
            if os.path.exists(temp_compressed):
                try:
                    os.remove(temp_compressed)
                except Exception:
                    pass

            failed_count += 1
            total_new_size += orig_size
            results.append({
                "filename": filename,
                "rel_path": rel_path,
                "orig_size": orig_size,
                "orig_size_human": format_file_size(orig_size),
                "new_size": orig_size,
                "new_size_human": format_file_size(orig_size),
                "saved_bytes": 0,
                "saved_bytes_human": "0 B",
                "saved_pct": 0.0,
                "status": "error",
                "error": str(exc),
                "backup_path": "",
            })

    total_saved_bytes = max(0, total_orig_size - total_new_size)
    total_saved_pct = (
        round((total_saved_bytes / total_orig_size) * 100, 1)
        if total_orig_size > 0
        else 0.0
    )

    return {
        "folder_path": folder_path,
        "backup_dir": backup_dir,
        "total_images": len(images),
        "success_count": success_count,
        "failed_count": failed_count,
        "total_orig_size": total_orig_size,
        "total_orig_size_human": format_file_size(total_orig_size),
        "total_new_size": total_new_size,
        "total_new_size_human": format_file_size(total_new_size),
        "total_saved_bytes": total_saved_bytes,
        "total_saved_bytes_human": format_file_size(total_saved_bytes),
        "total_saved_pct": total_saved_pct,
        "results": results,
    }


def create_zip_archive(files_data: List[Dict[str, Any]]) -> bytes:
    """Create in-memory zip archive containing compressed images."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in files_data:
            fname = item.get("filename") or "image"
            data = item.get("data")
            if data:
                zip_file.writestr(fname, data)
    return zip_buffer.getvalue()


def _ask_directory_worker() -> Optional[str]:
    """Worker to open native directory browser dialog."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="Chọn thư mục chứa ảnh cần nén")
        root.destroy()
        return selected if selected else None
    except Exception:
        return None


async def pick_folder_dialog() -> Optional[str]:
    """Asynchronously trigger native directory selection dialog."""
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _ask_directory_worker)
