"""Router for Metadata management (Countries, etc.) using MongoDB.

Endpoints:
- GET  /metadata/countries                 -> Country management web UI
- GET  /metadata/api/countries             -> List countries (JSON)
- POST /metadata/api/countries             -> Create country
- POST /metadata/api/countries/{id}/edit   -> Update country
- POST /metadata/api/countries/{id}/delete -> Delete country
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.database import get_db
from app.core.templates import templates
from app.metadata import services

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/countries", name="metadata-countries")
async def countries_page(
    request: Request,
    search: str = "",
    status: str = "all",
    db: Any = Depends(get_db),
):
    """Render the Country Management screen."""
    data = await services.list_countries(db, search=search, status_filter=status)
    return templates.TemplateResponse(
        request,
        "metadata/countries.html",
        {
            "active_tool": "metadata",
            "active_sub_menu": "countries",
            "countries": data["items"],
            "total_count": data["total"],
            "active_count": data["active_count"],
            "db_connected": data["db_connected"],
            "search": search,
            "status_filter": status,
        },
    )


@router.get("/api/countries", name="api-list-countries")
async def api_list_countries(
    search: str = "",
    status: str = "all",
    db: Any = Depends(get_db),
):
    """Return JSON list of countries."""
    data = await services.list_countries(db, search=search, status_filter=status)
    return JSONResponse(data)


@router.post("/api/countries", name="api-create-country")
async def api_create_country(
    request: Request,
    name: str = Form(...),
    country_code: str = Form(...),
    phone_code: str = Form(...),
    native_name: Optional[str] = Form(None),
    flag_emoji: Optional[str] = Form(None),
    currency_code: Optional[str] = Form(None),
    status: str = Form("active"),
    db: Any = Depends(get_db),
):
    """Create a new country record in MongoDB."""
    try:
        country = await services.create_country(
            db,
            {
                "name": name,
                "country_code": country_code,
                "phone_code": phone_code,
                "native_name": native_name,
                "flag_emoji": flag_emoji,
                "currency_code": currency_code,
                "status": status,
            },
        )
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "country": country})
        return RedirectResponse(url="/metadata/countries", status_code=303)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/countries/{country_id}/edit", name="api-update-country")
async def api_update_country(
    country_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    phone_code: Optional[str] = Form(None),
    native_name: Optional[str] = Form(None),
    flag_emoji: Optional[str] = Form(None),
    currency_code: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Update an existing country record in MongoDB."""
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if country_code is not None:
        update_data["country_code"] = country_code
    if phone_code is not None:
        update_data["phone_code"] = phone_code
    if native_name is not None:
        update_data["native_name"] = native_name
    if flag_emoji is not None:
        update_data["flag_emoji"] = flag_emoji
    if currency_code is not None:
        update_data["currency_code"] = currency_code
    if status is not None:
        update_data["status"] = status

    country = await services.update_country(db, country_id, update_data)
    if not country:
        return JSONResponse({"ok": False, "error": "Country not found"}, status_code=404)

    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": True, "country": country})
    return RedirectResponse(url="/metadata/countries", status_code=303)


@router.post("/api/countries/{country_id}/delete", name="api-delete-country")
async def api_delete_country(
    country_id: int,
    request: Request,
    db: Any = Depends(get_db),
):
    """Delete a country record from MongoDB."""
    success = await services.delete_country(db, country_id)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": success})
    return RedirectResponse(url="/metadata/countries", status_code=303)


@router.post("/api/countries/import-iso", name="api-import-iso-countries")
async def api_import_iso_countries(
    request: Request,
    overwrite: bool = Form(False),
    db: Any = Depends(get_db),
):
    """Import / Migrate 249 ISO countries into MongoDB."""
    result = await services.migrate_iso_countries(db=db, overwrite=overwrite)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse(result)
    return RedirectResponse(url="/metadata/countries", status_code=303)

