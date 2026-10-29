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
    prompt = block.get("system_prompt") or services.DEFAULT_SYSTEM_PROMPT
    language = block.get("default_language") or "en"
    timeout = float(block.get("timeout_seconds") or services.DEFAULT_TIMEOUT_SECONDS)
    return model, prompt, language, timeout


@router.get("/image-to-prompt", name="image-to-prompt")
async def image_to_prompt_page(request: Request):
    default_model, default_prompt, default_language, _ = _get_configured_defaults()
    return templates.TemplateResponse(
        request,
        "tools/image_to_prompt.html",
        {
            "active_tool": "image-to-prompt",
            "default_model": default_model,
            "default_prompt": default_prompt,
            "default_language": default_language,
            "languages": services.PROMPT_LANGUAGES,
        },
    )


@router.get("/image-to-prompt/models", name="image-to-prompt-models")
async def image_to_prompt_models() -> JSONResponse:
    """Check Ollama connectivity and return available models."""
    default_model, _, _, _ = _get_configured_defaults()
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
    model: str = Form(services.DEFAULT_MODEL),
    prompt: str = Form(""),
    language: str = Form("en"),
):
    """Test generating a reverse prompt on a single uploaded image."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="File tải lên không có dữ liệu.")

    _, default_prompt, default_language, default_timeout = _get_configured_defaults()
    config = services.PromptConfig(
        model=model.strip() or services.DEFAULT_MODEL,
        prompt=prompt.strip() or default_prompt,
        language=language.strip() or default_language,
        timeout_seconds=default_timeout,
    )

    try:
        result_prompt = await services.generate_prompt_for_image_bytes(raw, config)
        return JSONResponse({"prompt": result_prompt, "filename": file.filename or "image"})
    except services.ImageToPromptError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/image-to-prompt/process", name="image-to-prompt-process")
async def image_to_prompt_process(
    folder: str = Form(..., description="Thư mục chứa ảnh"),
    model: str = Form(services.DEFAULT_MODEL),
    prompt: str = Form(""),
    language: str = Form("en"),
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

    _, default_prompt, default_language, default_timeout = _get_configured_defaults()
    config = services.PromptConfig(
        model=model.strip() or services.DEFAULT_MODEL,
        prompt=prompt.strip() or default_prompt,
        language=language.strip() or default_language,
        timeout_seconds=default_timeout,
        overwrite=overwrite,
    )

    total = len(files)

    async def event_stream():
        def line(obj: dict) -> str:
            return json.dumps(obj, ensure_ascii=False) + "\n"

        yield line({"type": "start", "total": total, "folder": str(folder_path)})

        ok = skipped = failed = 0
        last_error = None

        for index, img_path in enumerate(files):
            # Signal image processing started
            yield line({"type": "file_start", "index": index + 1, "total": total, "file": str(img_path), "filename": img_path.name})

            # Process image and save .txt
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
