"""FastAPI Router for Prompt Templates management."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.database import get_mongo_database
from app.core.templates import templates
from app.prompt_templates.models import PromptTemplateCreate, PromptTemplateUpdate
from app.prompt_templates.services import prompt_template_repo

router = APIRouter()


@router.get("/tools/prompt-templates", response_class=HTMLResponse, name="prompt-templates-screen")
@router.get("/prompt-templates", response_class=HTMLResponse, name="prompt-templates-screen-direct")
async def prompt_templates_screen(
    request: Request,
    search: Optional[str] = None,
    category: Optional[str] = None,
    db=Depends(get_mongo_database),
):
    """Render Prompt Template Management screen."""
    all_items = await prompt_template_repo.get_all_templates(search=search, category=category, db=db)
    
    # Calculate categories & stats
    categories = sorted(list({t.get("category", "Chân dung") for t in all_items if t.get("category")}))
    total_count = len(all_items)
    default_tpl = next((t for t in all_items if t.get("is_default")), None)
    db_connected = await prompt_template_repo.is_connected(db=db)

    return templates.TemplateResponse(
        request,
        "tools/prompt_templates.html",
        {
            "active_tool": "prompt-templates",
            "templates": all_items,
            "categories": categories,
            "total_count": total_count,
            "default_template": default_tpl,
            "current_search": search or "",
            "current_category": category or "all",
            "db_connected": db_connected,
        },
    )


@router.get("/api/prompt-templates", name="api-list-prompt-templates")
async def api_list_prompt_templates(
    search: Optional[str] = None,
    category: Optional[str] = None,
    db=Depends(get_mongo_database),
):
    """API endpoint to list all prompt templates as JSON for dropdowns and external consumers."""
    items = await prompt_template_repo.get_all_templates(search=search, category=category, db=db)
    return JSONResponse({"status": "ok", "total": len(items), "data": items})


@router.get("/api/prompt-templates/{template_id}", name="api-get-prompt-template")
async def api_get_prompt_template(
    template_id: int,
    db=Depends(get_mongo_database),
):
    """API endpoint to get a single prompt template by ID."""
    tpl = await prompt_template_repo.get_template_by_id(template_id, db=db)
    if not tpl:
        raise HTTPException(status_code=404, detail="Không tìm thấy template với ID đã cung cấp.")
    return JSONResponse({"status": "ok", "data": tpl})


@router.post("/api/prompt-templates", name="api-create-prompt-template")
async def api_create_prompt_template(
    request: Request,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    category: Optional[str] = Form("Chân dung"),
    language: Optional[str] = Form("pt-BR"),
    prompt_content: Optional[str] = Form(None),
    aspect_ratio_mode: Optional[str] = Form("none"),
    target_aspect_ratio: Optional[str] = Form("4:5"),
    is_default: Optional[bool] = Form(False),
    db=Depends(get_mongo_database),
):
    """Create a new prompt template, accepting Form data or JSON body."""
    data: dict = {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body_json = await request.json()
            data = dict(body_json)
        except Exception:
            data = {}
    else:
        data = {
            "name": name or "",
            "description": description or "",
            "category": category or "Chân dung",
            "language": language or "pt-BR",
            "prompt_content": prompt_content or "",
            "aspect_ratio_mode": aspect_ratio_mode or "none",
            "target_aspect_ratio": target_aspect_ratio or "4:5",
            "is_default": bool(is_default),
        }

    if not data.get("name") or not data.get("prompt_content"):
        raise HTTPException(status_code=400, detail="Tên template và nội dung Prompt là bắt buộc.")

    created = await prompt_template_repo.create_template(data, db=db)
    return JSONResponse(
        {"status": "ok", "message": f"Đã tạo thành công template '{created.get('name')}'", "data": created},
        status_code=status.HTTP_201_CREATED,
    )


@router.put("/api/prompt-templates/{template_id}", name="api-update-prompt-template")
@router.post("/api/prompt-templates/{template_id}/edit", name="api-update-prompt-template-post")
async def api_update_prompt_template(
    template_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    prompt_content: Optional[str] = Form(None),
    aspect_ratio_mode: Optional[str] = Form(None),
    target_aspect_ratio: Optional[str] = Form(None),
    is_default: Optional[bool] = Form(None),
    db=Depends(get_mongo_database),
):
    """Update an existing prompt template."""
    existing = await prompt_template_repo.get_template_by_id(template_id, db=db)
    if not existing:
        raise HTTPException(status_code=404, detail="Không tìm thấy template để cập nhật.")

    update_data: dict = {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body_json = await request.json()
            update_data = {k: v for k, v in body_json.items() if v is not None}
        except Exception:
            update_data = {}
    else:
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if category is not None:
            update_data["category"] = category
        if language is not None:
            update_data["language"] = language
        if prompt_content is not None:
            update_data["prompt_content"] = prompt_content
        if aspect_ratio_mode is not None:
            update_data["aspect_ratio_mode"] = aspect_ratio_mode
        if target_aspect_ratio is not None:
            update_data["target_aspect_ratio"] = target_aspect_ratio
        if is_default is not None:
            update_data["is_default"] = bool(is_default)

    if not update_data:
        raise HTTPException(status_code=400, detail="Không có dữ liệu cập nhật.")

    updated = await prompt_template_repo.update_template(template_id, update_data, db=db)
    return JSONResponse(
        {"status": "ok", "message": f"Đã cập nhật thành công template '{updated.get('name')}'", "data": updated}
    )


@router.delete("/api/prompt-templates/{template_id}", name="api-delete-prompt-template")
@router.post("/api/prompt-templates/{template_id}/delete", name="api-delete-prompt-template-post")
async def api_delete_prompt_template(
    template_id: int,
    db=Depends(get_mongo_database),
):
    """Delete a prompt template by ID."""
    existing = await prompt_template_repo.get_template_by_id(template_id, db=db)
    if not existing:
        raise HTTPException(status_code=404, detail="Không tìm thấy template để xóa.")

    await prompt_template_repo.delete_template(template_id, db=db)
    return JSONResponse(
        {"status": "ok", "message": f"Đã xóa thành công template '{existing.get('name')}'."}
    )


@router.post("/api/prompt-templates/{template_id}/set-default", name="api-set-default-prompt-template")
async def api_set_default_prompt_template(
    template_id: int,
    db=Depends(get_mongo_database),
):
    """Set a template as the system default."""
    updated = await prompt_template_repo.set_default_template(template_id, db=db)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy template.")
    return JSONResponse(
        {"status": "ok", "message": f"Đã đặt template '{updated.get('name')}' làm mặc định.", "data": updated}
    )


@router.post("/api/prompt-templates/reset-defaults", name="api-reset-default-prompt-templates")
async def api_reset_default_prompt_templates(
    db=Depends(get_mongo_database),
):
    """Reset all prompt templates back to system factory defaults."""
    reset_list = await prompt_template_repo.reset_defaults(db=db)
    return JSONResponse(
        {"status": "ok", "message": "Đã khôi phục thành công các template mẫu chuẩn ban đầu.", "total": len(reset_list)}
    )
