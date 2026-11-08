"""FastAPI router for Image Metadata Editor tool."""
from __future__ import annotations

import io
from pathlib import Path
from urllib.parse import quote
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse

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
