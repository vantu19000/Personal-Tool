"""FastAPI router for Image Metadata Editor tool."""
from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.parse import quote
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.templates import templates
from app.tools.image_metadata import services

router = APIRouter()


@router.get("/image-metadata", name="image-metadata")
async def image_metadata_page(request: Request):
    """Render Image Metadata Editor web interface."""
    return templates.TemplateResponse(
        request,
        "tools/image_metadata.html",
        {
            "active_tool": "image-metadata",
            "supported_extensions": sorted(list(services.SUPPORTED_EXTENSIONS)),
            "default_ai_prompt": services.DEFAULT_AI_METADATA_PROMPT,
            "languages": services.RESPONSE_LANGUAGES,
            "default_language": "vi",
        },
    )


@router.get("/image-metadata/ollama-models", name="image-metadata-ollama-models")
async def get_ollama_models():
    """Fetch installed models from local Ollama instance."""
    models = await services.list_ollama_models()
    return JSONResponse({"status": "success", "models": models})


@router.post("/image-metadata/generate-ai", name="image-metadata-generate-ai")
async def generate_ai(
    topic: str = Form(""),
    model: str = Form("llama3:latest"),
    prompt_template: str = Form(""),
    language: str = Form("vi"),
    file: Optional[UploadFile] = File(None),
):
    """Generate image metadata using local Ollama model from user topic and prompt template."""
    clean_topic = topic.strip()
    if not clean_topic:
        raise HTTPException(status_code=400, detail="Vui lòng nhập chủ đề hoặc yêu cầu cho bức ảnh.")

    img_bytes = None
    if file and file.filename:
        try:
            img_bytes = await file.read()
        except Exception:
            img_bytes = None

    try:
        ai_data = await services.generate_ai_metadata(
            topic=clean_topic,
            model=model,
            prompt_template=prompt_template,
            language=language,
            image_bytes=img_bytes,
        )
        return JSONResponse({"status": "success", "data": ai_data})
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi sinh metadata qua Ollama: {str(exc)}")


@router.post("/image-metadata/read", name="image-metadata-read")
async def read_image_metadata(file: UploadFile = File(...)):
    """Upload an image and extract all EXIF, GPS, camera and text metadata."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Không có tệp nào được tải lên.")

    ext = Path(file.filename).suffix.lower()
    if ext not in services.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng tệp '{ext}' không được hỗ trợ. Vui lòng chọn tệp: {', '.join(services.SUPPORTED_EXTENSIONS)}",
        )

    try:
        content = await file.read()
        metadata = services.extract_metadata(content, file.filename)
        return JSONResponse({"status": "success", "data": metadata})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể đọc metadata ảnh: {str(exc)}")


@router.post("/image-metadata/save", name="image-metadata-save")
async def save_image_metadata(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    author: str = Form(""),
    copyright: str = Form(""),
    keywords: str = Form(""),
    rating: Optional[str] = Form(None),
    software: str = Form(""),
    date_taken: str = Form(""),
    date_digitized: str = Form(""),
    date_modified: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
    altitude: str = Form(""),
    camera_make: str = Form(""),
    camera_model: str = Form(""),
    lens_model: str = Form(""),
    iso: Optional[str] = Form(None),
    f_number: Optional[str] = Form(None),
    focal_length: Optional[str] = Form(None),
    clear_gps: bool = Form(False),
    clear_all: bool = Form(False),
    custom_filename: str = Form(""),
):
    """Write modified metadata to a single image and return the updated image file."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Thiếu tệp hình ảnh.")

    ext = Path(file.filename).suffix.lower()
    if ext not in services.SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Định dạng '{ext}' không được hỗ trợ.")

    try:
        content = await file.read()

        meta_dict = {
            "title": title,
            "description": description,
            "author": author,
            "copyright": copyright,
            "keywords": keywords,
            "rating": rating,
            "software": software,
            "date_taken": date_taken,
            "date_digitized": date_digitized,
            "date_modified": date_modified,
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "camera_make": camera_make,
            "camera_model": camera_model,
            "lens_model": lens_model,
            "iso": iso,
            "f_number": f_number,
            "focal_length": focal_length,
        }

        updated_bytes, mime_type = services.update_metadata(
            image_bytes=content,
            meta=meta_dict,
            clear_gps=clear_gps,
            clear_all=clear_all,
        )

        out_name = custom_filename.strip() if custom_filename.strip() else file.filename
        encoded_name = quote(out_name)

        return Response(
            content=updated_bytes,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{out_name}"; filename*=UTF-8\'\'{encoded_name}',
                "X-Filename": encoded_name,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu metadata: {str(exc)}")


@router.post("/image-metadata/save-batch", name="image-metadata-save-batch")
async def save_batch_metadata(
    files: list[UploadFile] = File(...),
    title: str = Form(""),
    description: str = Form(""),
    author: str = Form(""),
    copyright: str = Form(""),
    keywords: str = Form(""),
    rating: Optional[str] = Form(None),
    software: str = Form(""),
    date_taken: str = Form(""),
    date_digitized: str = Form(""),
    date_modified: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
    altitude: str = Form(""),
    camera_make: str = Form(""),
    camera_model: str = Form(""),
    lens_model: str = Form(""),
    iso: Optional[str] = Form(None),
    f_number: Optional[str] = Form(None),
    focal_length: Optional[str] = Form(None),
    clear_gps: bool = Form(False),
    clear_all: bool = Form(False),
):
    """Batch apply metadata to multiple images and return a ZIP download."""
    if not files:
        raise HTTPException(status_code=400, detail="Không có tệp nào được chọn.")

    meta_dict = {
        "title": title,
        "description": description,
        "author": author,
        "copyright": copyright,
        "keywords": keywords,
        "rating": rating,
        "software": software,
        "date_taken": date_taken,
        "date_digitized": date_digitized,
        "date_modified": date_modified,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "camera_make": camera_make,
        "camera_model": camera_model,
        "lens_model": lens_model,
        "iso": iso,
        "f_number": f_number,
        "focal_length": focal_length,
    }

    processed_files: list[tuple[str, bytes]] = []

    for file in files:
        if not file.filename:
            continue
        ext = Path(file.filename).suffix.lower()
        if ext not in services.SUPPORTED_EXTENSIONS:
            continue

        try:
            content = await file.read()
            updated_bytes, _ = services.update_metadata(
                image_bytes=content,
                meta=meta_dict,
                clear_gps=clear_gps,
                clear_all=clear_all,
            )
            processed_files.append((file.filename, updated_bytes))
        except Exception:
            continue

    if not processed_files:
        raise HTTPException(status_code=400, detail="Không có hình ảnh hợp lệ nào được xử lý.")

    zip_bytes = services.create_zip_archive(processed_files)
    zip_name = "metadata_edited_images.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_name}"',
        },
    )


@router.get("/image-metadata/folder-scan", name="image-metadata-folder-scan")
async def scan_folder(
    folder: str = Query(..., description="Đường dẫn thư mục chứa ảnh trên máy"),
    recursive: bool = Query(False, description="Quét cả thư mục con"),
):
    """Scan local directory for supported images, ignoring results subfolder."""
    if not folder or not folder.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn thư mục.")

    folder_path = Path(folder.strip()).expanduser()
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Thư mục không tồn tại: {folder_path}")

    try:
        files = services.scan_folder_images(folder_path, recursive=recursive)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    results_dir = folder_path / "results"
    file_list = []
    for f in files:
        try:
            sz = f.stat().st_size
        except OSError:
            sz = 0
        file_list.append({
            "name": f.name,
            "path": str(f),
            "size_bytes": sz,
        })

    return JSONResponse({
        "status": "success",
        "folder": str(folder_path),
        "results_dir": str(results_dir),
        "count": len(files),
        "files": file_list,
    })


@router.post("/image-metadata/process-folder-ai", name="image-metadata-process-folder-ai")
async def process_folder_ai(
    folder: str = Form(...),
    topic: str = Form(""),
    model: str = Form("llama3:latest"),
    language: str = Form("vi"),
    prompt_template: str = Form(""),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    altitude: Optional[str] = Form(None),
    recursive: bool = Form(False),
):
    """Batch process folder images using Ollama, set current datetime, update metadata, and stream progress."""
    if not folder or not folder.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn thư mục.")

    folder_path = Path(folder.strip()).expanduser()
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Thư mục không tồn tại: {folder_path}")

    files = services.scan_folder_images(folder_path, recursive=recursive)
    if not files:
        raise HTTPException(
            status_code=400,
            detail=f"Không tìm thấy ảnh hợp lệ ({', '.join(services.SUPPORTED_EXTENSIONS)}) trong thư mục {folder_path}",
        )

    # Parse location overrides if provided
    override_lat: float | None = None
    override_lon: float | None = None
    override_alt: float | None = None

    if latitude and str(latitude).strip():
        try:
            override_lat = float(str(latitude).strip())
        except ValueError:
            override_lat = None

    if longitude and str(longitude).strip():
        try:
            override_lon = float(str(longitude).strip())
        except ValueError:
            override_lon = None

    if altitude and str(altitude).strip():
        try:
            override_alt = float(str(altitude).strip())
        except ValueError:
            override_alt = None

    results_dir = folder_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    total = len(files)

    async def event_stream():
        def line(obj: dict) -> str:
            return json.dumps(obj, ensure_ascii=False) + "\n"

        yield line({
            "type": "start",
            "total": total,
            "folder": str(folder_path),
            "results_dir": str(results_dir),
        })

        ok_count = 0
        failed_count = 0

        for idx, img_path in enumerate(files):
            yield line({
                "type": "file_start",
                "index": idx + 1,
                "total": total,
                "filename": img_path.name,
                "path": str(img_path),
            })

            try:
                result = await services.process_folder_ai_image(
                    image_path=img_path,
                    output_dir=results_dir,
                    topic=topic,
                    model=model,
                    language=language,
                    prompt_template=prompt_template,
                    override_lat=override_lat,
                    override_lon=override_lon,
                    override_alt=override_alt,
                )
                ok_count += 1
                yield line({
                    "type": "file_done",
                    "index": idx + 1,
                    "total": total,
                    **result,
                })
            except Exception as exc:
                failed_count += 1
                yield line({
                    "type": "file_error",
                    "index": idx + 1,
                    "total": total,
                    "filename": img_path.name,
                    "error": str(exc),
                })

        yield line({
            "type": "done",
            "total": total,
            "ok": ok_count,
            "failed": failed_count,
            "results_dir": str(results_dir),
        })

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
