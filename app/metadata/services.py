"""Services for Country Metadata management with MongoDB.

Built on top of `BaseMongoRepository` from `app.core.mongo_base` to provide
standardized data access, auto indexing, seeding, and fallback support.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository

logger = logging.getLogger(__name__)

# Collection name in MongoDB
COLLECTION_NAME = "metadata_countries"

# Standard seed countries list
DEFAULT_COUNTRIES = [
    {
        "id": 1,
        "name": "Việt Nam",
        "country_code": "VN",
        "phone_code": "+84",
        "native_name": "Việt Nam",
        "flag_emoji": "🇻🇳",
        "currency_code": "VND",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 2,
        "name": "Hoa Kỳ (Mỹ)",
        "country_code": "US",
        "phone_code": "+1",
        "native_name": "United States",
        "flag_emoji": "🇺🇸",
        "currency_code": "USD",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 3,
        "name": "Nhật Bản",
        "country_code": "JP",
        "phone_code": "+81",
        "native_name": "日本 (Nihon)",
        "flag_emoji": "🇯🇵",
        "currency_code": "JPY",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 4,
        "name": "Hàn Quốc",
        "country_code": "KR",
        "phone_code": "+82",
        "native_name": "대한민국 (Daehan Minguk)",
        "flag_emoji": "🇰🇷",
        "currency_code": "KRW",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 5,
        "name": "Vương Quốc Anh",
        "country_code": "GB",
        "phone_code": "+44",
        "native_name": "United Kingdom",
        "flag_emoji": "🇬🇧",
        "currency_code": "GBP",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 6,
        "name": "Pháp",
        "country_code": "FR",
        "phone_code": "+33",
        "native_name": "France",
        "flag_emoji": "🇫🇷",
        "currency_code": "EUR",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 7,
        "name": "Đức",
        "country_code": "DE",
        "phone_code": "+49",
        "native_name": "Deutschland",
        "flag_emoji": "🇩🇪",
        "currency_code": "EUR",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 8,
        "name": "Singapore",
        "country_code": "SG",
        "phone_code": "+65",
        "native_name": "Singapore",
        "flag_emoji": "🇸🇬",
        "currency_code": "SGD",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 9,
        "name": "Thái Lan",
        "country_code": "TH",
        "phone_code": "+66",
        "native_name": "ประเทศไทย (Mueang Thai)",
        "flag_emoji": "🇹🇭",
        "currency_code": "THB",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 10,
        "name": "Úc (Australia)",
        "country_code": "AU",
        "phone_code": "+61",
        "native_name": "Australia",
        "flag_emoji": "🇦🇺",
        "currency_code": "AUD",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 11,
        "name": "Canada",
        "country_code": "CA",
        "phone_code": "+1",
        "native_name": "Canada",
        "flag_emoji": "🇨🇦",
        "currency_code": "CAD",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 12,
        "name": "Trung Quốc",
        "country_code": "CN",
        "phone_code": "+86",
        "native_name": "中国 (Zhongguo)",
        "flag_emoji": "🇨🇳",
        "currency_code": "CNY",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 13,
        "name": "Đài Loan",
        "country_code": "TW",
        "phone_code": "+886",
        "native_name": "台灣 (Taiwan)",
        "flag_emoji": "🇹🇼",
        "currency_code": "TWD",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 14,
        "name": "Malaysia",
        "country_code": "MY",
        "phone_code": "+60",
        "native_name": "Malaysia",
        "flag_emoji": "🇲🇾",
        "currency_code": "MYR",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 15,
        "name": "Indonesia",
        "country_code": "ID",
        "phone_code": "+62",
        "native_name": "Indonesia",
        "flag_emoji": "🇮🇩",
        "currency_code": "IDR",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
]

# Shared BaseMongoRepository instance for Country metadata
country_repo = BaseMongoRepository(collection_name=COLLECTION_NAME, id_field="id")


async def ensure_collection_and_seed(db: Any = None) -> bool:
    """Ensure the country collection exists and seed default countries if empty."""
    index_specs = [
        ("id", True),
        ("country_code", True),
        "name",
    ]
    return await country_repo.seed_if_empty(DEFAULT_COUNTRIES, index_specs=index_specs, db=db)


async def list_countries(
    db: Any = None,
    search: str = "",
    status_filter: str = "",
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """Retrieve countries from MongoDB with optional search, filter, and pagination."""
    # Ensure initialized/seeded
    await ensure_collection_and_seed(db=db)

    query: Dict[str, Any] = {}
    if search:
        regex_pattern = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"name": regex_pattern},
            {"country_code": regex_pattern},
            {"phone_code": regex_pattern},
            {"native_name": regex_pattern},
        ]

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    items, pagination, db_connected = await country_repo.find_paginated(
        query=query,
        sort_field="id",
        sort_dir=1,
        page=page,
        page_size=page_size,
        db=db,
    )

    # Count active records
    active_count = 0
    if db_connected:
        col = country_repo.get_collection(db)
        if col is not None:
            try:
                active_query = dict(query)
                active_query["status"] = "active"
                active_count = await col.count_documents(active_query)
            except Exception:
                active_count = sum(1 for c in items if c.get("status") == "active")
    else:
        active_count = sum(1 for c in items if c.get("status") == "active")

    return {
        "items": items,
        "total": pagination.total_items,
        "active_count": active_count,
        "db_connected": db_connected,
        "pagination": pagination,
    }


async def create_country(db: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new country record in MongoDB."""
    name = str(data.get("name", "")).strip()
    country_code = str(data.get("country_code", "")).strip().upper()
    phone_code = str(data.get("phone_code", "")).strip()

    if not name or not country_code or not phone_code:
        raise ValueError("Tên quốc gia, mã quốc gia và mã vùng điện thoại là bắt buộc.")

    if not phone_code.startswith("+"):
        phone_code = f"+{phone_code}"

    doc = {
        "name": name,
        "country_code": country_code,
        "phone_code": phone_code,
        "native_name": str(data.get("native_name", "")).strip() or None,
        "flag_emoji": str(data.get("flag_emoji", "")).strip() or "🌐",
        "currency_code": str(data.get("currency_code", "")).strip().upper() or None,
        "status": str(data.get("status", "active")),
    }

    return await country_repo.insert(doc, auto_id=True, db=db)


async def update_country(db: Any, country_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing country in MongoDB."""
    update_fields: Dict[str, Any] = {}

    if "name" in data and data["name"]:
        update_fields["name"] = str(data["name"]).strip()
    if "country_code" in data and data["country_code"]:
        update_fields["country_code"] = str(data["country_code"]).strip().upper()
    if "phone_code" in data and data["phone_code"]:
        pc = str(data["phone_code"]).strip()
        update_fields["phone_code"] = pc if pc.startswith("+") else f"+{pc}"
    if "native_name" in data:
        update_fields["native_name"] = str(data["native_name"]).strip() or None
    if "flag_emoji" in data:
        update_fields["flag_emoji"] = str(data["flag_emoji"]).strip() or "🌐"
    if "currency_code" in data:
        update_fields["currency_code"] = str(data["currency_code"]).strip().upper() or None
    if "status" in data:
        update_fields["status"] = str(data["status"])

    return await country_repo.update(country_id, update_fields, db=db)


async def delete_country(db: Any, country_id: int) -> bool:
    """Delete a country record from MongoDB."""
    return await country_repo.delete(country_id, db=db)


def load_iso_countries_json() -> List[Dict[str, Any]]:
    """Load the pre-built ISO 3166-1 dataset from data/iso_countries.json."""
    import json
    from pathlib import Path
    data_path = Path(__file__).resolve().parent / "data" / "iso_countries.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return []


async def migrate_iso_countries(
    db: Any = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Migrate 249 ISO countries into MongoDB with smart upsert.

    - If country_code already exists:
        - If overwrite=False: preserves existing record (keeps user edits).
        - If overwrite=True: updates fields.
    - If country_code does not exist:
        - Inserts new record with autoincrement ID.
    """
    iso_list = load_iso_countries_json()
    if not iso_list:
        return {"ok": False, "error": "ISO dataset file not found."}

    await ensure_collection_and_seed(db=db)
    col = country_repo.get_collection(db)

    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    if col is not None:
        try:
            # Fetch existing codes
            existing_docs = await col.find({}, {"country_code": 1, "id": 1, "_id": 0}).to_list(length=10000)
            existing_map = {doc.get("country_code", "").upper(): doc.get("id") for doc in existing_docs if doc.get("country_code")}

            # Next id counter
            next_id = await country_repo.get_next_id(db=db)

            for item in iso_list:
                code = item.get("country_code", "").upper()
                if not code:
                    continue

                if code in existing_map:
                    if overwrite:
                        update_payload = dict(item)
                        update_payload.pop("country_code", None)
                        await country_repo.update(existing_map[code], update_payload, db=db)
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    new_doc = dict(item)
                    new_doc["id"] = next_id
                    next_id += 1
                    await country_repo.insert(new_doc, auto_id=False, db=db)
                    existing_map[code] = new_doc["id"]
                    inserted_count += 1

            total_now = await col.count_documents({})
            return {
                "ok": True,
                "total_iso": len(iso_list),
                "inserted": inserted_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "total_now": total_now,
            }
        except Exception as exc:
            logger.error(f"Migration error: {exc}")
            return {"ok": False, "error": str(exc)}

    return {"ok": False, "error": "Database not connected"}


# ============================================================================
# Province / City (Tỉnh / Thành phố) Metadata Management
# ============================================================================

PROVINCE_COLLECTION_NAME = "metadata_provinces"
province_repo = BaseMongoRepository(collection_name=PROVINCE_COLLECTION_NAME, id_field="id")


def load_vn_provinces_json() -> List[Dict[str, Any]]:
    """Load the pre-built 63 Vietnam provinces/cities dataset from data/vn_provinces.json."""
    import json
    from pathlib import Path
    data_path = Path(__file__).resolve().parent / "data" / "vn_provinces.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return []


async def ensure_province_collection_and_seed(db: Any = None) -> bool:
    """Ensure the province collection exists and seed with Vietnam provinces if empty."""
    index_specs = [
        ("id", True),
        ("code", False),
        "name",
        "region",
        "type",
    ]
    vn_list = load_vn_provinces_json()
    return await province_repo.seed_if_empty(vn_list, index_specs=index_specs, db=db)


async def list_provinces(
    db: Any = None,
    search: str = "",
    status_filter: str = "all",
    region_filter: str = "all",
    type_filter: str = "all",
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """Retrieve provinces from MongoDB with optional search, filters, and pagination."""
    await ensure_province_collection_and_seed(db=db)

    query: Dict[str, Any] = {}
    if search:
        regex_pattern = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"name": regex_pattern},
            {"code": regex_pattern},
            {"phone_code": regex_pattern},
            {"postal_code": regex_pattern},
            {"region": regex_pattern},
        ]

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    if region_filter and region_filter != "all":
        query["region"] = region_filter

    if type_filter and type_filter != "all":
        query["type"] = type_filter

    items, pagination, db_connected = await province_repo.find_paginated(
        query=query,
        sort_field="id",
        sort_dir=1,
        page=page,
        page_size=page_size,
        db=db,
    )

    # Compute quick stats
    active_count = 0
    total_count = pagination.total_items
    central_cities_count = 0

    if db_connected:
        col = province_repo.get_collection(db)
        if col is not None:
            try:
                active_count = await col.count_documents({"status": "active"})
                central_cities_count = await col.count_documents({"type": {"$regex": "Trung ương", "$options": "i"}})
            except Exception:
                active_count = sum(1 for c in items if c.get("status") == "active")
                central_cities_count = sum(1 for c in items if "Trung ương" in c.get("type", ""))
    else:
        active_count = sum(1 for c in items if c.get("status") == "active")
        central_cities_count = sum(1 for c in items if "Trung ương" in c.get("type", ""))

    return {
        "items": items,
        "total": total_count,
        "active_count": active_count,
        "central_cities_count": central_cities_count,
        "db_connected": db_connected,
        "pagination": pagination,
    }


async def create_province(db: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new province / city record in MongoDB."""
    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip()

    if not name or not code:
        raise ValueError("Tên tỉnh/thành phố và mã hành chính là bắt buộc.")

    doc = {
        "name": name,
        "code": code,
        "type": str(data.get("type", "Tỉnh")).strip() or "Tỉnh",
        "region": str(data.get("region", "")).strip() or None,
        "country_code": str(data.get("country_code", "VN")).strip().upper() or "VN",
        "phone_code": str(data.get("phone_code", "")).strip() or None,
        "postal_code": str(data.get("postal_code", "")).strip() or None,
        "status": str(data.get("status", "active")),
    }

    return await province_repo.insert(doc, auto_id=True, db=db)


async def update_province(db: Any, province_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing province / city in MongoDB."""
    update_fields: Dict[str, Any] = {}

    if "name" in data and data["name"]:
        update_fields["name"] = str(data["name"]).strip()
    if "code" in data and data["code"]:
        update_fields["code"] = str(data["code"]).strip()
    if "type" in data and data["type"]:
        update_fields["type"] = str(data["type"]).strip()
    if "region" in data:
        update_fields["region"] = str(data["region"]).strip() or None
    if "country_code" in data:
        update_fields["country_code"] = str(data["country_code"]).strip().upper() or "VN"
    if "phone_code" in data:
        update_fields["phone_code"] = str(data["phone_code"]).strip() or None
    if "postal_code" in data:
        update_fields["postal_code"] = str(data["postal_code"]).strip() or None
    if "status" in data:
        update_fields["status"] = str(data["status"])

    return await province_repo.update(province_id, update_fields, db=db)


async def delete_province(db: Any, province_id: int) -> bool:
    """Delete a province / city record from MongoDB."""
    return await province_repo.delete(province_id, db=db)


async def migrate_vn_provinces(
    db: Any = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Import / Migrate 63 Vietnam provinces/cities into MongoDB with smart upsert."""
    vn_list = load_vn_provinces_json()
    if not vn_list:
        return {"ok": False, "error": "Vietnam provinces dataset file not found."}

    await ensure_province_collection_and_seed(db=db)
    col = province_repo.get_collection(db)

    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    if col is not None:
        try:
            existing_docs = await col.find({}, {"code": 1, "name": 1, "id": 1, "_id": 0}).to_list(length=10000)
            existing_code_map = {str(doc.get("code", "")).strip().upper(): doc.get("id") for doc in existing_docs if doc.get("code")}
            existing_name_map = {str(doc.get("name", "")).strip().lower(): doc.get("id") for doc in existing_docs if doc.get("name")}

            next_id = await province_repo.get_next_id(db=db)

            for item in vn_list:
                code_key = str(item.get("code", "")).strip().upper()
                name_key = str(item.get("name", "")).strip().lower()

                target_id = existing_code_map.get(code_key) or existing_name_map.get(name_key)

                if target_id is not None:
                    if overwrite:
                        update_payload = dict(item)
                        update_payload.pop("id", None)
                        await province_repo.update(target_id, update_payload, db=db)
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    new_doc = dict(item)
                    new_doc["id"] = next_id
                    next_id += 1
                    await province_repo.insert(new_doc, auto_id=False, db=db)
                    existing_code_map[code_key] = new_doc["id"]
                    existing_name_map[name_key] = new_doc["id"]
                    inserted_count += 1

            total_now = await col.count_documents({})
            return {
                "ok": True,
                "total_provinces": len(vn_list),
                "inserted": inserted_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "total_now": total_now,
            }
        except Exception as exc:
            logger.error(f"Province migration error: {exc}")
            if province_repo.enable_fallback:
                inserted_count = 0
                for item in vn_list:
                    exists = any(
                        p.get("code") == item.get("code") or p.get("name") == item.get("name")
                        for p in province_repo._memory_cache
                    )
                    if not exists:
                        province_repo._memory_cache.append(dict(item))
                        inserted_count += 1
                return {
                    "ok": True,
                    "total_provinces": len(vn_list),
                    "inserted": inserted_count,
                    "updated": 0,
                    "skipped": len(vn_list) - inserted_count,
                    "total_now": len(province_repo._memory_cache),
                    "fallback": True,
                }
            return {"ok": False, "error": str(exc)}

    # Fallback when DB is not connected
    if province_repo.enable_fallback:
        inserted_count = 0
        for item in vn_list:
            exists = any(
                p.get("code") == item.get("code") or p.get("name") == item.get("name")
                for p in province_repo._memory_cache
            )
            if not exists:
                province_repo._memory_cache.append(dict(item))
                inserted_count += 1
        return {
            "ok": True,
            "total_provinces": len(vn_list),
            "inserted": inserted_count,
            "updated": 0,
            "skipped": len(vn_list) - inserted_count,
            "total_now": len(province_repo._memory_cache),
            "fallback": True,
        }

    return {"ok": False, "error": "Database not connected"}


