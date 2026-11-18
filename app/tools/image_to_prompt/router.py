"""Router for the Image to Prompt (Reverse Prompt) tool.

Routes:
- GET  /tools/image-to-prompt           — UI form page
- GET  /tools/image-to-prompt/models    — models on local Ollama (/api/tags)
- GET  /tools/image-to-prompt/scan      — scan folder for images and check existing .txt
- POST /tools/image-to-prompt/process   — batch reverse prompt from folder with NDJSON stream
- POST /tools/image-to-prompt/single    — single test image reverse prompt
"""
import asyncio
import json
from pathlib import Path

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.core import settings_store
from app.core.templates import templates
from app.tools.image_to_prompt import services

router = APIRouter()


def _get_configured_defaults():
    """Retrieve default settings if configured in settings_store, else fall back to service defaults."""
    block = settings_store.get_block("image_to_prompt")
    model = block.get("default_model") or services.DEFAULT_MODEL
    prompt = block.get("system_prompt")
    if not prompt or prompt.strip() == "Custom prompt description for Ollama":
        prompt = services.DEFAULT_SYSTEM_PROMPT
    language = block.get("default_language") or "pt-BR"
    character_desc = block.get("character_description") or services.DEFAULT_CHARACTER_DESC
    aspect_ratio_mode = block.get("aspect_ratio_mode") or services.DEFAULT_ASPECT_RATIO_MODE
    target_aspect_ratio = block.get("target_aspect_ratio") or services.DEFAULT_TARGET_ASPECT_RATIO
    timeout = float(block.get("timeout_seconds") or services.DEFAULT_TIMEOUT_SECONDS)
    return model, prompt, language, character_desc, aspect_ratio_mode, target_aspect_ratio, timeout


@router.get("/prompt-pronto", name="prompt-pronto-direct")
@router.get("/prompt-pronto/image-to-prompt", name="prompt-pronto-sub")
@router.get("/image-to-prompt", name="image-to-prompt")
async def image_to_prompt_page(request: Request):
    default_model, default_prompt, default_language, default_char, default_ar, default_target_ar, _ = _get_configured_defaults()
    return templates.TemplateResponse(
        request,
        "tools/image_to_prompt.html",
        {
            "active_tool": "image-to-prompt",
            "default_model": default_model,
            "default_prompt": default_prompt,
            "system_default_prompt": services.DEFAULT_SYSTEM_PROMPT,
            "default_language": default_language,
            "default_character_desc": default_char,
            "default_aspect_ratio_mode": default_ar,
            "default_target_aspect_ratio": default_target_ar,
            "languages": services.PROMPT_LANGUAGES,
        },
    )


@router.get("/image-to-prompt/models", name="image-to-prompt-models")
async def image_to_prompt_models() -> JSONResponse:
    """Check Ollama connectivity and return available models."""
    default_model, _, _, _, _, _, _ = _get_configured_defaults()
    try:
        models = await services.list_ollama_models()
        return JSONResponse(
            {"online": True, "models": models, "default": default_model}
        )
    except services.ImageToPromptError:
        return JSONResponse(
            {"online": False, "models": [], "default": default_model}
        )


@router.get("/image-to-prompt/scan", name="image-to-prompt-scan")
async def image_to_prompt_scan(
    folder: str = Query(..., description="Đường dẫn thư mục chứa ảnh"),
    recursive: bool = Query(False, description="Quét thư mục con"),
) -> JSONResponse:
    """Scan folder and return image stats before running batch."""
    if not folder or not folder.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn thư mục.")

    folder_path = Path(folder.strip()).expanduser()
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Thư mục không tồn tại: {folder_path}")

    try:
        files = services.scan_image_files(folder_path, recursive=recursive)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    file_info = []
    existing_txt_count = 0
    for f in files:
        txt_path = f.with_suffix(".txt")
        has_txt = txt_path.exists()
        if has_txt:
            existing_txt_count += 1
        try:
            size_bytes = f.stat().st_size
        except OSError:
            size_bytes = 0

        file_info.append(
            {
                "name": f.name,
                "path": str(f),
                "size_bytes": size_bytes,
                "has_txt": has_txt,
            }
        )

    return JSONResponse(
        {
            "count": len(files),
            "existing_txt_count": existing_txt_count,
            "folder": str(folder_path),
            "files": file_info,
        }
    )


@router.post("/tools/image-to-prompt/single", name="image-to-prompt-single")
@router.post("/image-to-prompt/single", name="image-to-prompt-single-direct")
async def image_to_prompt_single(
    file: UploadFile = File(..., description="File hình ảnh cần tạo prompt"),
    reference_face: Optional[UploadFile] = File(None, description="Ảnh mặt tham chiếu (tùy chọn)"),
    model: str = Form(services.DEFAULT_MODEL),
    prompt: str = Form(""),
    language: str = Form("en"),
    character_desc: str = Form(""),
    aspect_ratio_mode: str = Form(""),
    target_aspect_ratio: str = Form("4:5"),
):
    """Test generating a reverse prompt on a single uploaded image with optional reference face."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="File tải lên không có dữ liệu.")

    ref_bytes = await reference_face.read() if reference_face else None
    if ref_bytes and len(ref_bytes) == 0:
        ref_bytes = None

    def_model, default_prompt, default_language, def_char, def_ar, def_target_ar, default_timeout = _get_configured_defaults()
    config = services.PromptConfig(
        model=model.strip() or def_model,
        prompt=prompt.strip() or default_prompt,
        language=language.strip() or default_language,
        character_description=character_desc.strip() if character_desc.strip() else def_char,
        aspect_ratio_mode=aspect_ratio_mode.strip() if aspect_ratio_mode.strip() else def_ar,
        target_aspect_ratio=target_aspect_ratio.strip() if target_aspect_ratio.strip() else def_target_ar,
        timeout_seconds=default_timeout,
        reference_face_bytes=ref_bytes,
    )

    try:
        result = await services.generate_prompt_for_image_bytes(raw, config)
        if isinstance(result, str):
            result = services.parse_title_and_prompt(result)
        return JSONResponse({
            "title": result.get("title", ""),
            "prompt": result.get("prompt", ""),
            "aspect_ratio": result.get("aspect_ratio", "4:5"),
            "width": result.get("width", 0),
            "height": result.get("height", 0),
            "filename": file.filename or "image",
        })
    except services.ImageToPromptError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tools/image-to-prompt/save-defaults", name="image-to-prompt-save-defaults")
@router.post("/image-to-prompt/save-defaults", name="image-to-prompt-save-defaults-direct")
async def image_to_prompt_save_defaults(
    model: str = Form("qwen 3.8"),
    language: str = Form("pt-BR"),
    prompt: str = Form(""),
    character_desc: str = Form(""),
    aspect_ratio_mode: str = Form("none"),
    target_aspect_ratio: str = Form("4:5"),
):
    """Save current descriptions and options as application defaults."""
    try:
        settings_store.settings_store.save_blocks({
            "image_to_prompt": {
                "default_model": model.strip() or services.DEFAULT_MODEL,
                "default_language": language.strip() or "pt-BR",
                "system_prompt": prompt.strip() or services.DEFAULT_SYSTEM_PROMPT,
                "character_description": character_desc.strip() or services.DEFAULT_CHARACTER_DESC,
                "aspect_ratio_mode": aspect_ratio_mode.strip() or services.DEFAULT_ASPECT_RATIO_MODE,
                "target_aspect_ratio": target_aspect_ratio.strip() or services.DEFAULT_TARGET_ASPECT_RATIO,
            }
        })
        return JSONResponse({"status": "ok", "message": "Đã lưu cấu hình làm mặc định thành công!"})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Không thể lưu cấu hình: {exc}")


@router.post("/tools/image-to-prompt/rename", name="image-to-prompt-rename")
@router.post("/image-to-prompt/rename", name="image-to-prompt-rename-direct")
async def image_to_prompt_rename(
    folder: str = Form(..., description="Đường dẫn thư mục chứa ảnh cần đổi tên"),
    recursive: bool = Form(False),
):
    """Step 1 helper: Rename all images in folder to image-1.ext, image-2.ext..."""
    if not folder or not folder.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn thư mục.")

    folder_path = Path(folder.strip()).expanduser()
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Thư mục không tồn tại: {folder_path}")

    try:
        renamed = services.rename_images_to_standard_format(folder_path, recursive=recursive)
        return JSONResponse({
            "status": "ok",
            "message": f"Đã đổi tên thành công {len(renamed)} file ảnh theo định dạng image-1, image-2...",
            "count": len(renamed),
            "files": renamed,
        })
    except services.ImageToPromptError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đổi tên: {exc}")


@router.post("/tools/image-to-prompt/process", name="image-to-prompt-process-tools")
@router.post("/image-to-prompt/process", name="image-to-prompt-process")
async def image_to_prompt_process(
    folder: str = Form(..., description="Thư mục chứa ảnh"),
    reference_face: Optional[UploadFile] = File(None, description="Ảnh mặt tham chiếu áp dụng cho cả thư mục (tùy chọn)"),
    model: str = Form(services.DEFAULT_MODEL),
    prompt: str = Form(""),
    language: str = Form("pt-BR"),
    character_desc: str = Form(""),
    aspect_ratio_mode: str = Form(""),
    target_aspect_ratio: str = Form("4:5"),
    auto_rename: bool = Form(True, description="Tự động đổi tên ảnh thành image-1.ext, image-2.ext... trước khi gọi Ollama"),
    overwrite: bool = Form(False),
    recursive: bool = Form(False),
):
    """Process all images in the folder, saving reverse prompt as .txt alongside each image."""
    if not folder or not folder.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn thư mục.")

    folder_path = Path(folder.strip()).expanduser()
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Thư mục không tồn tại: {folder_path}")

    files = services.scan_image_files(folder_path, recursive=recursive)
    if not files:
        raise HTTPException(
            status_code=400,
            detail=f"Không tìm thấy hình ảnh nào ({', '.join(services.SUPPORTED_EXTENSIONS)}) trong thư mục {folder_path}",
        )

    ref_bytes = await reference_face.read() if reference_face else None
    if ref_bytes and len(ref_bytes) == 0:
        ref_bytes = None

    def_model, default_prompt, default_language, def_char, def_ar, def_target_ar, default_timeout = _get_configured_defaults()
    config = services.PromptConfig(
        model=model.strip() or def_model,
        prompt=prompt.strip() or default_prompt,
        language=language.strip() or default_language,
        character_description=character_desc.strip() if character_desc.strip() else def_char,
        aspect_ratio_mode=aspect_ratio_mode.strip() if aspect_ratio_mode.strip() else def_ar,
        target_aspect_ratio=target_aspect_ratio.strip() if target_aspect_ratio.strip() else def_target_ar,
        timeout_seconds=default_timeout,
        overwrite=overwrite,
        reference_face_bytes=ref_bytes,
    )

    async def event_stream():
        def line(obj: dict) -> str:
            return json.dumps(obj, ensure_ascii=False) + "\n"

        current_files = files

        # Step 1: Rename images to standard image-1.ext, image-2.ext... if auto_rename is True
        if auto_rename:
            try:
                renamed_records = services.rename_images_to_standard_format(folder_path, recursive=recursive)
                if renamed_records:
                    yield line({
                        "type": "rename_done",
                        "renamed_count": len(renamed_records),
                        "message": f"Step 1: Đã đổi tên thành công {len(renamed_records)} ảnh thành image-1.ext, image-2.ext...",
                        "records": renamed_records,
                    })
                    # Re-scan newly renamed files
                    current_files = services.scan_image_files(folder_path, recursive=recursive)
            except Exception as r_err:
                yield line({
                    "type": "rename_warning",
                    "error": f"Cảnh báo Step 1 đổi tên: {r_err}. Tiếp tục xử lý với tên file hiện tại.",
                })

        total = len(current_files)
        yield line({"type": "start", "total": total, "folder": str(folder_path)})

        ok = skipped = failed = 0
        last_error = None

        for index, img_path in enumerate(current_files):
            # Signal image processing started (Step 2)
            yield line({"type": "file_start", "index": index + 1, "total": total, "file": str(img_path), "filename": img_path.name})

            # Process image with Ollama and save .txt (Step 3)
            result = await services.process_image_file(img_path, config)
            st = result.get("status")

            if st == "ok":
                ok += 1
                yield line({"type": "file_done", "index": index + 1, "total": total, **result})
            elif st == "skipped":
                skipped += 1
                yield line({"type": "file_skipped", "index": index + 1, "total": total, **result})
            else:
                failed += 1
                last_error = result.get("error")
                yield line({"type": "file_error", "index": index + 1, "total": total, **result})

        yield line({
            "type": "done",
            "total": total,
            "ok": ok,
            "skipped": skipped,
            "failed": failed,
            "folder": str(folder_path),
            "last_error": last_error if failed > 0 else None,
        })

    return StreamingResponse(event_stream(), media_type="application/x-ndjson; charset=utf-8")
