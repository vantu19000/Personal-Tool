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


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
async def metadata_root_redirect():
    """Redirect /metadata root to countries screen."""
    return RedirectResponse(url="/metadata/countries", status_code=307)


@router.get("/countries", name="metadata-countries")
async def countries_page(
    request: Request,
    search: str = "",
    status: str = "all",
    page: int = 1,
    page_size: int = 25,
    db: Any = Depends(get_db),
):
    """Render the Country Management screen with pagination."""
    data = await services.list_countries(
        db, search=search, status_filter=status, page=page, page_size=page_size
    )
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
            "pagination": data.get("pagination"),
            "search": search,
            "status_filter": status,
        },
    )


@router.get("/api/countries", name="api-list-countries")
async def api_list_countries(
    search: str = "",
    status: str = "all",
    page: int = 1,
    page_size: int = 25,
    db: Any = Depends(get_db),
):
    """Return JSON list of countries with pagination."""
    data = await services.list_countries(
        db, search=search, status_filter=status, page=page, page_size=page_size
    )
    if "pagination" in data and hasattr(data["pagination"], "to_dict"):
        data["pagination"] = data["pagination"].to_dict()
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


# ============================================================================
# Province / City Endpoints
# ============================================================================

@router.get("/provinces", name="metadata-provinces")
async def provinces_page(
    request: Request,
    search: str = "",
    status: str = "all",
    region: str = "all",
    type: str = "all",
    page: int = 1,
    page_size: int = 25,
    db: Any = Depends(get_db),
):
    """Render the Province / City management screen with pagination and filters."""
    data = await services.list_provinces(
        db,
        search=search,
        status_filter=status,
        region_filter=region,
        type_filter=type,
        page=page,
        page_size=page_size,
    )
    return templates.TemplateResponse(
        request,
        "metadata/provinces.html",
        {
            "active_tool": "metadata",
            "active_sub_menu": "provinces",
            "provinces": data["items"],
            "total_count": data["total"],
            "active_count": data["active_count"],
            "central_cities_count": data.get("central_cities_count", 0),
            "db_connected": data["db_connected"],
            "pagination": data.get("pagination"),
            "search": search,
            "status_filter": status,
            "region_filter": region,
            "type_filter": type,
        },
    )


@router.get("/api/provinces", name="api-list-provinces")
async def api_list_provinces(
    search: str = "",
    status: str = "all",
    region: str = "all",
    type: str = "all",
    page: int = 1,
    page_size: int = 25,
    db: Any = Depends(get_db),
):
    """Return JSON list of provinces with pagination."""
    data = await services.list_provinces(
        db,
        search=search,
        status_filter=status,
        region_filter=region,
        type_filter=type,
        page=page,
        page_size=page_size,
    )
    if "pagination" in data and hasattr(data["pagination"], "to_dict"):
        data["pagination"] = data["pagination"].to_dict()
    return JSONResponse(data)


@router.post("/api/provinces", name="api-create-province")
async def api_create_province(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    type: str = Form("Tỉnh"),
    region: Optional[str] = Form(None),
    country_code: str = Form("VN"),
    phone_code: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    status: str = Form("active"),
    db: Any = Depends(get_db),
):
    """Create a new province / city record in MongoDB."""
    try:
        province = await services.create_province(
            db,
            {
                "name": name,
                "code": code,
                "type": type,
                "region": region,
                "country_code": country_code,
                "phone_code": phone_code,
                "postal_code": postal_code,
                "status": status,
            },
        )
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "province": province})
        return RedirectResponse(url="/metadata/provinces", status_code=303)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/provinces/{province_id}/edit", name="api-update-province")
async def api_update_province(
    province_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    region: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    phone_code: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Update an existing province / city record in MongoDB."""
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if code is not None:
        update_data["code"] = code
    if type is not None:
        update_data["type"] = type
    if region is not None:
        update_data["region"] = region
    if country_code is not None:
        update_data["country_code"] = country_code
    if phone_code is not None:
        update_data["phone_code"] = phone_code
    if postal_code is not None:
        update_data["postal_code"] = postal_code
    if status is not None:
        update_data["status"] = status

    province = await services.update_province(db, province_id, update_data)
    if not province:
        return JSONResponse({"ok": False, "error": "Province not found"}, status_code=404)

    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": True, "province": province})
    return RedirectResponse(url="/metadata/provinces", status_code=303)


@router.post("/api/provinces/{province_id}/delete", name="api-delete-province")
async def api_delete_province(
    province_id: int,
    request: Request,
    db: Any = Depends(get_db),
):
    """Delete a province record from MongoDB."""
    success = await services.delete_province(db, province_id)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": success})
    return RedirectResponse(url="/metadata/provinces", status_code=303)


@router.post("/api/provinces/import-vn", name="api-import-vn-provinces")
async def api_import_vn_provinces(
    request: Request,
    overwrite: bool = Form(False),
    db: Any = Depends(get_db),
):
    """Import / Migrate 63 Vietnam provinces/cities into MongoDB."""
    result = await services.migrate_vn_provinces(db=db, overwrite=overwrite)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse(result)
    return RedirectResponse(url="/metadata/provinces", status_code=303)


