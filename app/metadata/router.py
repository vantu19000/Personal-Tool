"""Router for Metadata management (Countries, Regions, Units, Provinces, Wards) using MongoDB.

Endpoints:
- GET  /metadata/countries                 -> Country management web UI
- GET  /metadata/api/countries             -> List countries (JSON)
- POST /metadata/api/countries             -> Create country
- POST /metadata/api/countries/{id}/edit   -> Update country
- POST /metadata/api/countries/{id}/delete -> Delete country
- POST /metadata/api/countries/import-iso  -> Import 249 ISO countries

- GET  /metadata/api/regions               -> List 8 Administrative Regions (JSON)
- GET  /metadata/api/units                 -> List 5 Administrative Unit types (JSON)

- GET  /metadata/provinces                 -> Province / City web UI (34 Provinces)
- GET  /metadata/api/provinces             -> List provinces (JSON)
- POST /metadata/api/provinces             -> Create province
- POST /metadata/api/provinces/{id}/edit   -> Update province
- POST /metadata/api/provinces/{id}/delete -> Delete province
- POST /metadata/api/provinces/import-vn   -> Import 34 provinces

- GET  /metadata/wards                     -> Ward / Commune web UI (3,321 Wards)
- GET  /metadata/api/wards                 -> List wards (JSON)
- POST /metadata/api/wards                 -> Create ward
- POST /metadata/api/wards/{id}/edit       -> Update ward
- POST /metadata/api/wards/{id}/delete     -> Delete ward
- POST /metadata/api/wards/import          -> Import 3,321 wards

- POST /metadata/api/reset-all-vn-units    -> Master sync/reset all VN units
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


# ============================================================================
# Country Endpoints
# ============================================================================

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
# Administrative Regions & Units API Endpoints
# ============================================================================

@router.get("/api/regions", name="api-list-regions")
async def api_list_regions(db: Any = Depends(get_db)):
    """Return JSON list of 8 Vietnam administrative regions."""
    items = await services.list_administrative_regions(db=db)
    return JSONResponse({"ok": True, "items": items, "total": len(items)})


@router.get("/api/units", name="api-list-units")
async def api_list_units(db: Any = Depends(get_db)):
    """Return JSON list of 5 Vietnam administrative unit classifications."""
    items = await services.list_administrative_units(db=db)
    return JSONResponse({"ok": True, "items": items, "total": len(items)})


@router.post("/api/reset-all-vn-units", name="api-reset-all-vn-units")
async def api_reset_all_vn_units(request: Request, db: Any = Depends(get_db)):
    """Master Reset / Sync: updates regions, units, 34 provinces, and 3,321 wards."""
    res = await services.migrate_all_vn_units(db=db, reset=True)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse(res)
    return RedirectResponse(url="/metadata/provinces", status_code=303)


# ============================================================================
# Province / City Endpoints (34 Provinces)
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
            "provinces_count": data.get("provinces_count", 0),
            "total_wards_count": data.get("total_wards_count", 3321),
            "regions_list": data.get("regions_list", []),
            "units_list": data.get("units_list", []),
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
    name_en: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    full_name_en: Optional[str] = Form(None),
    code_name: Optional[str] = Form(None),
    type: str = Form("Tỉnh"),
    administrative_unit_id: Optional[int] = Form(None),
    administrative_region_id: Optional[int] = Form(None),
    region: Optional[str] = Form(None),
    region_en: Optional[str] = Form(None),
    merged_from: Optional[str] = Form(None),
    country_code: str = Form("VN"),
    phone_code: Optional[str] = Form(None),
    postal_code_prefix: Optional[str] = Form(None),
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
                "name_en": name_en,
                "full_name": full_name,
                "full_name_en": full_name_en,
                "code_name": code_name,
                "type": type,
                "administrative_unit_id": administrative_unit_id,
                "administrative_region_id": administrative_region_id,
                "region": region,
                "region_en": region_en,
                "merged_from": merged_from,
                "country_code": country_code,
                "phone_code": phone_code,
                "postal_code_prefix": postal_code_prefix,
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
    name_en: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    full_name_en: Optional[str] = Form(None),
    code_name: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    administrative_unit_id: Optional[int] = Form(None),
    administrative_region_id: Optional[int] = Form(None),
    region: Optional[str] = Form(None),
    region_en: Optional[str] = Form(None),
    merged_from: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    phone_code: Optional[str] = Form(None),
    postal_code_prefix: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Update an existing province / city record in MongoDB."""
    update_data = {}
    for key, val in [
        ("name", name),
        ("code", code),
        ("name_en", name_en),
        ("full_name", full_name),
        ("full_name_en", full_name_en),
        ("code_name", code_name),
        ("type", type),
        ("administrative_unit_id", administrative_unit_id),
        ("administrative_region_id", administrative_region_id),
        ("region", region),
        ("region_en", region_en),
        ("merged_from", merged_from),
        ("country_code", country_code),
        ("phone_code", phone_code),
        ("postal_code_prefix", postal_code_prefix),
        ("postal_code", postal_code),
        ("status", status),
    ]:
        if val is not None:
            update_data[key] = val

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
    overwrite: bool = Form(True),
    reset: bool = Form(True),
    db: Any = Depends(get_db),
):
    """Import / Migrate 34 Vietnam provinces/cities into MongoDB."""
    result = await services.migrate_vn_provinces(db=db, overwrite=overwrite, reset=reset)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse(result)
    return RedirectResponse(url="/metadata/provinces", status_code=303)


# ============================================================================
# Ward / Commune (Xã / Phường / Đặc khu) Endpoints (3,321 Wards)
# ============================================================================

@router.get("/wards", name="metadata-wards")
@router.get("/wards/", include_in_schema=False)
async def wards_page(
    request: Request,
    search: str = "",
    province: str = "all",
    type: str = "all",
    status: str = "all",
    page: int = 1,
    page_size: int = 25,
    db: Any = Depends(get_db),
):
    """Render the Ward / Commune / Island zone management screen."""
    data = await services.list_wards(
        db,
        search=search,
        province_filter=province,
        type_filter=type,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    return templates.TemplateResponse(
        request,
        "metadata/wards.html",
        {
            "active_tool": "metadata",
            "active_sub_menu": "wards",
            "wards": data["items"],
            "total_count": data["total"],
            "active_count": data["active_count"],
            "phuong_count": data["phuong_count"],
            "xa_count": data["xa_count"],
            "dackhu_count": data.get("dackhu_count", 0),
            "thitran_count": data.get("thitran_count", 0),
            "provinces_list": data["provinces_list"],
            "db_connected": data["db_connected"],
            "pagination": data.get("pagination"),
            "search": search,
            "province_filter": province,
            "type_filter": type,
            "status_filter": status,
        },
    )


@router.get("/api/wards", name="api-list-wards")
async def api_list_wards(
    search: str = "",
    province: str = "all",
    type: str = "all",
    status: str = "all",
    page: int = 1,
    page_size: int = 25,
    db: Any = Depends(get_db),
):
    """Return JSON list of wards with pagination."""
    data = await services.list_wards(
        db,
        search=search,
        province_filter=province,
        type_filter=type,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    if "pagination" in data and hasattr(data["pagination"], "to_dict"):
        data["pagination"] = data["pagination"].to_dict()
    return JSONResponse(data)


@router.post("/api/wards", name="api-create-ward")
async def api_create_ward(
    request: Request,
    name: str = Form(...),
    code: Optional[str] = Form(None),
    name_en: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    full_name_en: Optional[str] = Form(None),
    code_name: Optional[str] = Form(None),
    type: str = Form("Xã"),
    administrative_unit_id: Optional[int] = Form(None),
    province_id: Optional[int] = Form(None),
    province_code: Optional[str] = Form(None),
    province_name: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    district_name: Optional[str] = Form(None),
    merged_note: Optional[str] = Form(None),
    status: str = Form("active"),
    db: Any = Depends(get_db),
):
    """Create a new ward / commune record in MongoDB."""
    try:
        ward = await services.create_ward(
            db,
            {
                "name": name,
                "code": code,
                "name_en": name_en,
                "full_name": full_name,
                "full_name_en": full_name_en,
                "code_name": code_name,
                "type": type,
                "administrative_unit_id": administrative_unit_id,
                "province_id": province_id,
                "province_code": province_code,
                "province_name": province_name,
                "postal_code": postal_code,
                "district_name": district_name,
                "merged_note": merged_note,
                "status": status,
            },
        )
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
            return JSONResponse({"ok": True, "ward": ward})
        return RedirectResponse(url="/metadata/wards", status_code=303)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/api/wards/{ward_id}/edit", name="api-update-ward")
async def api_update_ward(
    ward_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    name_en: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    full_name_en: Optional[str] = Form(None),
    code_name: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    administrative_unit_id: Optional[int] = Form(None),
    province_id: Optional[int] = Form(None),
    province_code: Optional[str] = Form(None),
    province_name: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    district_name: Optional[str] = Form(None),
    merged_note: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: Any = Depends(get_db),
):
    """Update an existing ward / commune record in MongoDB."""
    update_data = {}
    for key, val in [
        ("name", name),
        ("code", code),
        ("name_en", name_en),
        ("full_name", full_name),
        ("full_name_en", full_name_en),
        ("code_name", code_name),
        ("type", type),
        ("administrative_unit_id", administrative_unit_id),
        ("province_id", province_id),
        ("province_code", province_code),
        ("province_name", province_name),
        ("postal_code", postal_code),
        ("district_name", district_name),
        ("merged_note", merged_note),
        ("status", status),
    ]:
        if val is not None:
            update_data[key] = val

    ward = await services.update_ward(db, ward_id, update_data)
    if not ward:
        return JSONResponse({"ok": False, "error": "Ward not found"}, status_code=404)

    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": True, "ward": ward})
    return RedirectResponse(url="/metadata/wards", status_code=303)


@router.post("/api/wards/{ward_id}/delete", name="api-delete-ward")
async def api_delete_ward(
    ward_id: int,
    request: Request,
    db: Any = Depends(get_db),
):
    """Delete a ward record from MongoDB."""
    success = await services.delete_ward(db, ward_id)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse({"ok": success})
    return RedirectResponse(url="/metadata/wards", status_code=303)


@router.post("/api/wards/import", name="api-import-wards")
async def api_import_wards(
    request: Request,
    limit: Optional[int] = Form(None),
    reset: bool = Form(False),
    db: Any = Depends(get_db),
):
    """Import wards from local dataset file into MongoDB."""
    result = await services.import_vn_wards(db=db, limit=limit, reset=reset)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse(result)
    return RedirectResponse(url="/metadata/wards", status_code=303)


@router.post("/api/wards/sync-web", name="api-sync-wards-web")
async def api_sync_wards_web(
    request: Request,
    limit: Optional[int] = Form(None),
    reset: bool = Form(True),
    db: Any = Depends(get_db),
):
    """Sync/reload all 3,321 wards from dataset into MongoDB."""
    result = await services.import_vn_wards(db=db, limit=limit, reset=reset)
    accept = request.headers.get("accept", "")
    if "application/json" in accept or "fetch" in request.headers.get("sec-fetch-mode", ""):
        return JSONResponse(result)
    return RedirectResponse(url="/metadata/wards", status_code=303)
