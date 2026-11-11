"""Services for Metadata management with MongoDB.

Covers:
1. ISO Countries (249 standard countries)
2. Administrative Regions (8 vùng hành chính kinh tế - xã hội của Việt Nam)
3. Administrative Units (5 cấp đơn vị hành chính: Cấp tỉnh/TP.TW, Phường, Xã, Đặc khu hải đảo)
4. Vietnam Provinces / Municipalities (34 Tỉnh / Thành phố trực thuộc trung ương)
5. Vietnam Wards / Communes / Special Zones (3.321 Xã / Phường / Đặc khu hải đảo)

Built on top of `BaseMongoRepository` from `app.core.mongo_base` to provide
standardized data access, auto indexing, seeding, and fallback support.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository

logger = logging.getLogger(__name__)

# Data directory path
DATA_DIR = Path(__file__).resolve().parent / "data"

# ============================================================================
# 1. Country Metadata Management
# ============================================================================

COLLECTION_NAME = "metadata_countries"

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
        "name": "Nga",
        "country_code": "RU",
        "phone_code": "+7",
        "native_name": "Россия (Rossiya)",
        "flag_emoji": "🇷🇺",
        "currency_code": "RUB",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 14,
        "name": "Ấn Độ",
        "country_code": "IN",
        "phone_code": "+91",
        "native_name": "भारत (Bharat)",
        "flag_emoji": "🇮🇳",
        "currency_code": "INR",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 15,
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
        "id": 16,
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
    {
        "id": 17,
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
        "id": 18,
        "name": "Philippines",
        "country_code": "PH",
        "phone_code": "+63",
        "native_name": "Pilipinas",
        "flag_emoji": "🇵🇭",
        "currency_code": "PHP",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 19,
        "name": "Thụy Sĩ",
        "country_code": "CH",
        "phone_code": "+41",
        "native_name": "Schweiz",
        "flag_emoji": "🇨🇭",
        "currency_code": "CHF",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
    {
        "id": 20,
        "name": "Hà Lan",
        "country_code": "NL",
        "phone_code": "+31",
        "native_name": "Nederland",
        "flag_emoji": "🇳🇱",
        "currency_code": "EUR",
        "status": "active",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:00",
    },
]

country_repo = BaseMongoRepository(collection_name=COLLECTION_NAME, id_field="id")


async def ensure_collection_and_seed(db: Any = None) -> bool:
    """Ensure countries collection exists with index and seed data if empty."""
    index_specs = [
        ("id", True),
        ("country_code", False),
        "name",
        "phone_code",
    ]
    return await country_repo.seed_if_empty(DEFAULT_COUNTRIES, index_specs=index_specs, db=db)


async def list_countries(
    db: Any = None,
    search: str = "",
    status_filter: str = "all",
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """Retrieve countries from MongoDB with optional search and pagination."""
    await ensure_collection_and_seed(db=db)

    query: Dict[str, Any] = {}
    if search:
        regex_pattern = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"name": regex_pattern},
            {"country_code": regex_pattern},
            {"phone_code": regex_pattern},
            {"native_name": regex_pattern},
            {"currency_code": regex_pattern},
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

    active_count = 0
    total_count = pagination.total_items

    if db_connected:
        col = country_repo.get_collection(db)
        if col is not None:
            try:
                active_count = await col.count_documents({"status": "active"})
            except Exception:
                active_count = sum(1 for c in items if c.get("status") == "active")
    else:
        active_count = sum(1 for c in items if c.get("status") == "active")

    return {
        "items": items,
        "total": total_count,
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
        raise ValueError("Tên quốc gia, Mã ISO và Mã điện thoại là bắt buộc.")

    doc = {
        "name": name,
        "country_code": country_code,
        "phone_code": phone_code if phone_code.startswith("+") else f"+{phone_code}",
        "native_name": str(data.get("native_name", "")).strip() or None,
        "flag_emoji": str(data.get("flag_emoji", "🌐")).strip() or "🌐",
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
    """Load pre-built 249 ISO countries dataset from data/iso_countries.json."""
    data_path = DATA_DIR / "iso_countries.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return []


async def migrate_iso_countries(
    db: Any = None,
    overwrite: bool = False,
    reset: bool = False,
) -> Dict[str, Any]:
    """Import / Migrate 249 ISO 3166-1 countries into MongoDB."""
    iso_list = load_iso_countries_json()
    if not iso_list:
        return {"ok": False, "error": "ISO countries dataset file not found."}

    await ensure_collection_and_seed(db=db)
    col = country_repo.get_collection(db)

    if col is not None:
        try:
            if reset:
                await col.delete_many({})
                docs_to_insert = [dict(item) for item in iso_list]
                await col.insert_many(docs_to_insert)
                country_repo._memory_cache = [dict(item) for item in iso_list]
                total_now = await col.count_documents({})
                return {
                    "ok": True,
                    "total_iso": len(iso_list),
                    "inserted": len(iso_list),
                    "updated": 0,
                    "skipped": 0,
                    "total_now": total_now,
                    "reset": True,
                }

            existing_docs = await col.find({}, {"country_code": 1, "id": 1, "_id": 0}).to_list(length=1000)
            existing_code_map = {str(doc.get("country_code", "")).strip().upper(): doc.get("id") for doc in existing_docs}

            next_id = await country_repo.get_next_id(db=db)
            inserted_count = 0
            updated_count = 0
            skipped_count = 0

            for item in iso_list:
                code_key = str(item.get("country_code", "")).strip().upper()
                if not code_key:
                    continue

                if code_key in existing_code_map:
                    if overwrite:
                        target_id = existing_code_map[code_key]
                        update_payload = dict(item)
                        update_payload.pop("id", None)
                        await country_repo.update(target_id, update_payload, db=db)
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    new_doc = dict(item)
                    new_doc["id"] = next_id
                    next_id += 1
                    await country_repo.insert(new_doc, auto_id=False, db=db)
                    existing_code_map[code_key] = new_doc["id"]
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
            if country_repo.enable_fallback:
                country_repo._memory_cache = [dict(item) for item in iso_list]
                return {
                    "ok": True,
                    "total_iso": len(iso_list),
                    "inserted": len(iso_list),
                    "updated": 0,
                    "skipped": 0,
                    "total_now": len(country_repo._memory_cache),
                    "fallback": True,
                }
            return {"ok": False, "error": str(exc)}

    if country_repo.enable_fallback:
        country_repo._memory_cache = [dict(item) for item in iso_list]
        return {
            "ok": True,
            "total_iso": len(iso_list),
            "inserted": len(iso_list),
            "updated": 0,
            "skipped": 0,
            "total_now": len(country_repo._memory_cache),
            "fallback": True,
        }

    return {"ok": False, "error": "Database not connected"}


# ============================================================================
# 2. Administrative Regions (8 Vùng kinh tế - xã hội)
# ============================================================================

REGION_COLLECTION_NAME = "metadata_administrative_regions"
region_repo = BaseMongoRepository(collection_name=REGION_COLLECTION_NAME, id_field="id")


def load_administrative_regions_json() -> List[Dict[str, Any]]:
    """Load 8 administrative regions from data/administrative_regions.json."""
    data_path = DATA_DIR / "administrative_regions.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8-sig") as f:
            raw = json.load(f)
            # Normalize keys to lowercase for internal usage while preserving original
            normalized = []
            for r in raw:
                normalized.append({
                    "id": r.get("Id", r.get("id")),
                    "name": r.get("Name", r.get("name")),
                    "name_en": r.get("NameEn", r.get("name_en")),
                    "code_name": r.get("CodeName", r.get("code_name")),
                    "code_name_en": r.get("CodeNameEn", r.get("code_name_en")),
                    "status": r.get("status", "active"),
                })
            return normalized
    return []


async def ensure_region_collection_and_seed(db: Any = None) -> bool:
    """Ensure the administrative region collection exists and seed."""
    index_specs = [("id", True), "name", "code_name"]
    regions = load_administrative_regions_json()
    return await region_repo.seed_if_empty(regions, index_specs=index_specs, db=db)


async def list_administrative_regions(db: Any = None) -> List[Dict[str, Any]]:
    """Retrieve all 8 administrative regions."""
    await ensure_region_collection_and_seed(db=db)
    items, _ = await region_repo.find_all(sort_field="id", sort_dir=1, db=db)
    return items


# ============================================================================
# 3. Administrative Units (5 Cấp đơn vị hành chính)
# ============================================================================

UNIT_COLLECTION_NAME = "metadata_administrative_units"
unit_repo = BaseMongoRepository(collection_name=UNIT_COLLECTION_NAME, id_field="id")


def load_administrative_units_json() -> List[Dict[str, Any]]:
    """Load 5 administrative unit classifications from data/administrative_units.json."""
    data_path = DATA_DIR / "administrative_units.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8-sig") as f:
            raw = json.load(f)
            normalized = []
            for u in raw:
                normalized.append({
                    "id": u.get("Id", u.get("id")),
                    "full_name": u.get("FullName", u.get("full_name")),
                    "full_name_en": u.get("FullNameEn", u.get("full_name_en")),
                    "short_name": u.get("ShortName", u.get("short_name")),
                    "short_name_en": u.get("ShortNameEn", u.get("short_name_en")),
                    "code_name": u.get("CodeName", u.get("code_name")),
                    "code_name_en": u.get("CodeNameEn", u.get("code_name_en")),
                    "status": u.get("status", "active"),
                })
            return normalized
    return []


async def ensure_unit_collection_and_seed(db: Any = None) -> bool:
    """Ensure the administrative unit collection exists and seed."""
    index_specs = [("id", True), "code_name", "short_name"]
    units = load_administrative_units_json()
    return await unit_repo.seed_if_empty(units, index_specs=index_specs, db=db)


async def list_administrative_units(db: Any = None) -> List[Dict[str, Any]]:
    """Retrieve all 5 administrative unit classifications."""
    await ensure_unit_collection_and_seed(db=db)
    items, _ = await unit_repo.find_all(sort_field="id", sort_dir=1, db=db)
    return items


# ============================================================================
# 4. Province / City (Tỉnh / Thành phố) Metadata Management (34 Provinces)
# ============================================================================

PROVINCE_COLLECTION_NAME = "metadata_provinces"
province_repo = BaseMongoRepository(collection_name=PROVINCE_COLLECTION_NAME, id_field="id")


def load_vn_provinces_json() -> List[Dict[str, Any]]:
    """Load the 34 Vietnam provinces/cities dataset from data/vn_provinces.json."""
    data_path = DATA_DIR / "vn_provinces.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return []


async def ensure_province_collection_and_seed(db: Any = None) -> bool:
    """Ensure the province collection exists and seed with Vietnam provinces if empty or outdated."""
    index_specs = [
        ("id", True),
        ("code", False),
        "name",
        "code_name",
        "region",
        "administrative_unit_id",
        "type",
    ]
    vn_list = load_vn_provinces_json()
    col = province_repo.get_collection(db)
    if col is not None:
        try:
            total_count = await col.count_documents({})
            if total_count == 0:
                return await province_repo.seed_if_empty(vn_list, index_specs=index_specs, db=db)
            
            # Check if existing documents have the new administrative fields
            sample = await col.find_one({})
            if sample and ("administrative_unit_id" not in sample or "code_name" not in sample):
                logger.info("Migrating existing metadata_provinces to new administrative schema...")
                await col.delete_many({})
                docs = [dict(item) for item in vn_list]
                await col.insert_many(docs)
                province_repo._memory_cache = docs
                return True
        except Exception as exc:
            logger.warning(f"Error checking province collection: {exc}")

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
            {"full_name": regex_pattern},
            {"name_en": regex_pattern},
            {"code": regex_pattern},
            {"code_name": regex_pattern},
            {"phone_code": regex_pattern},
            {"postal_code_prefix": regex_pattern},
            {"postal_code": regex_pattern},
            {"region": regex_pattern},
        ]

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    if region_filter and region_filter != "all":
        # Can filter by region name or region id
        if region_filter.isdigit():
            query["administrative_region_id"] = int(region_filter)
        else:
            query["region"] = region_filter

    if type_filter and type_filter != "all":
        if type_filter.isdigit():
            query["administrative_unit_id"] = int(type_filter)
        elif "Trung ương" in type_filter or type_filter == "municipality":
            query["administrative_unit_id"] = 1
        elif type_filter == "Tỉnh" or type_filter == "province":
            query["administrative_unit_id"] = 2
        else:
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
    provinces_count = 0
    total_wards_count = 0

    if db_connected:
        col = province_repo.get_collection(db)
        if col is not None:
            try:
                active_count = await col.count_documents({"status": "active"})
                central_cities_count = await col.count_documents({
                    "$or": [
                        {"administrative_unit_id": 1},
                        {"type": {"$regex": "Trung ương", "$options": "i"}},
                    ]
                })
                provinces_count = await col.count_documents({
                    "$or": [
                        {"administrative_unit_id": 2},
                        {"type": "Tỉnh"},
                    ]
                })
                # Sum wards_count
                pipeline = [{"$group": {"_id": None, "total_wards": {"$sum": "$wards_count"}}}]
                agg = await col.aggregate(pipeline).to_list(1)
                if agg:
                    total_wards_count = agg[0].get("total_wards", 3321)
                else:
                    total_wards_count = 3321
            except Exception:
                active_count = sum(1 for c in items if c.get("status") == "active")
                central_cities_count = sum(1 for c in items if c.get("administrative_unit_id") == 1 or "Trung ương" in c.get("type", ""))
                provinces_count = sum(1 for c in items if c.get("administrative_unit_id") == 2 or c.get("type") == "Tỉnh")
                total_wards_count = sum(c.get("wards_count", 0) for c in items)
    else:
        active_count = sum(1 for c in items if c.get("status") == "active")
        central_cities_count = sum(1 for c in items if c.get("administrative_unit_id") == 1 or "Trung ương" in c.get("type", ""))
        provinces_count = sum(1 for c in items if c.get("administrative_unit_id") == 2 or c.get("type") == "Tỉnh")
        total_wards_count = sum(c.get("wards_count", 0) for c in items)

    # Load regions and units for filters
    regions_list = await list_administrative_regions(db=db)
    units_list = [u for u in await list_administrative_units(db=db) if u.get("id") in (1, 2)]

    return {
        "items": items,
        "total": total_count,
        "active_count": active_count,
        "central_cities_count": central_cities_count,
        "provinces_count": provinces_count,
        "total_wards_count": total_wards_count,
        "regions_list": regions_list,
        "units_list": units_list,
        "db_connected": db_connected,
        "pagination": pagination,
    }


async def create_province(db: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new province / city record in MongoDB."""
    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip()

    if not name or not code:
        raise ValueError("Tên tỉnh/thành phố và mã hành chính là bắt buộc.")

    unit_id = int(data.get("administrative_unit_id") or (1 if "Trung ương" in str(data.get("type", "")) else 2))
    type_str = "Thành phố trực thuộc trung ương" if unit_id == 1 else "Tỉnh"

    doc = {
        "name": name,
        "code": code,
        "name_en": str(data.get("name_en", "")).strip() or None,
        "full_name": str(data.get("full_name", "")).strip() or f"{type_str} {name}",
        "full_name_en": str(data.get("full_name_en", "")).strip() or None,
        "code_name": str(data.get("code_name", "")).strip() or None,
        "administrative_unit_id": unit_id,
        "administrative_unit_name": type_str,
        "administrative_region_id": int(data.get("administrative_region_id")) if data.get("administrative_region_id") else None,
        "type": str(data.get("type", type_str)).strip() or type_str,
        "region": str(data.get("region", "")).strip() or None,
        "region_en": str(data.get("region_en", "")).strip() or None,
        "country_code": str(data.get("country_code", "VN")).strip().upper() or "VN",
        "phone_code": str(data.get("phone_code", "")).strip() or None,
        "postal_code_prefix": str(data.get("postal_code_prefix", "")).strip() or None,
        "postal_code": str(data.get("postal_code", "")).strip() or None,
        "merged_from": str(data.get("merged_from", "")).strip() or None,
        "wards_count": int(data.get("wards_count") or 0),
        "status": str(data.get("status", "active")),
    }

    return await province_repo.insert(doc, auto_id=True, db=db)


async def update_province(db: Any, province_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing province / city in MongoDB."""
    update_fields: Dict[str, Any] = {}

    for field in (
        "name",
        "code",
        "name_en",
        "full_name",
        "full_name_en",
        "code_name",
        "type",
        "region",
        "region_en",
        "phone_code",
        "postal_code_prefix",
        "postal_code",
        "merged_from",
        "status",
    ):
        if field in data and data[field] is not None:
            update_fields[field] = str(data[field]).strip()

    if "country_code" in data:
        update_fields["country_code"] = str(data["country_code"]).strip().upper() or "VN"

    if "administrative_unit_id" in data and data["administrative_unit_id"]:
        try:
            uid = int(data["administrative_unit_id"])
            update_fields["administrative_unit_id"] = uid
            update_fields["administrative_unit_name"] = "Thành phố trực thuộc trung ương" if uid == 1 else "Tỉnh"
            if "type" not in update_fields:
                update_fields["type"] = update_fields["administrative_unit_name"]
        except (ValueError, TypeError):
            pass

    if "administrative_region_id" in data and data["administrative_region_id"]:
        try:
            update_fields["administrative_region_id"] = int(data["administrative_region_id"])
        except (ValueError, TypeError):
            pass

    if "wards_count" in data:
        try:
            update_fields["wards_count"] = int(data["wards_count"])
        except (ValueError, TypeError):
            pass

    return await province_repo.update(province_id, update_fields, db=db)


async def delete_province(db: Any, province_id: int) -> bool:
    """Delete a province / city record from MongoDB."""
    return await province_repo.delete(province_id, db=db)


async def migrate_vn_provinces(
    db: Any = None,
    overwrite: bool = True,
    reset: bool = True,
) -> Dict[str, Any]:
    """Import / Migrate 34 Vietnam provinces/cities into MongoDB.

    - If reset=True: replaces old dataset with the 34 official provinces from mongo_data_vn_unit.json.
    - If reset=False: smart upsert.
    """
    vn_list = load_vn_provinces_json()
    if not vn_list:
        return {"ok": False, "error": "Vietnam provinces dataset file not found."}

    await ensure_province_collection_and_seed(db=db)
    col = province_repo.get_collection(db)

    if col is not None:
        try:
            if reset:
                await col.delete_many({})
                docs_to_insert = [dict(item) for item in vn_list]
                await col.insert_many(docs_to_insert)
                province_repo._memory_cache = [dict(item) for item in vn_list]
                total_now = await col.count_documents({})
                return {
                    "ok": True,
                    "total_provinces": len(vn_list),
                    "inserted": len(vn_list),
                    "updated": 0,
                    "skipped": 0,
                    "total_now": total_now,
                    "reset": True,
                }

            existing_docs = await col.find({}, {"code": 1, "name": 1, "id": 1, "_id": 0}).to_list(length=1000)
            existing_code_map = {str(doc.get("code", "")).strip().upper(): doc.get("id") for doc in existing_docs if doc.get("code")}
            existing_name_map = {str(doc.get("name", "")).strip().lower(): doc.get("id") for doc in existing_docs if doc.get("name")}

            next_id = await province_repo.get_next_id(db=db)
            inserted_count = 0
            updated_count = 0
            skipped_count = 0

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
                province_repo._memory_cache = [dict(item) for item in vn_list]
                return {
                    "ok": True,
                    "total_provinces": len(vn_list),
                    "inserted": len(vn_list),
                    "updated": 0,
                    "skipped": 0,
                    "total_now": len(province_repo._memory_cache),
                    "fallback": True,
                }
            return {"ok": False, "error": str(exc)}

    if province_repo.enable_fallback:
        province_repo._memory_cache = [dict(item) for item in vn_list]
        return {
            "ok": True,
            "total_provinces": len(vn_list),
            "inserted": len(vn_list),
            "updated": 0,
            "skipped": 0,
            "total_now": len(province_repo._memory_cache),
            "fallback": True,
        }

    return {"ok": False, "error": "Database not connected"}


# ============================================================================
# 5. Ward / Commune (Xã / Phường / Đặc khu) Metadata Management (3.321 Wards)
# ============================================================================

WARD_COLLECTION_NAME = "metadata_wards"
ward_repo = BaseMongoRepository(collection_name=WARD_COLLECTION_NAME, id_field="id")

# Mapping of former 63 administrative provinces to 34 post-merger provinces
OLD_TO_NEW_PROVINCE_CODE: Dict[str, str] = {
    "Thành phố Hà Nội": "01",
    "Hà Nội": "01",
    "Thành phố Hải Phòng": "31",
    "Hải Phòng": "31",
    "Tỉnh Hải Dương": "31",
    "Hải Dương": "31",
    "Thành phố Huế": "46",
    "Huế": "46",
    "Tỉnh Thừa Thiên Huế": "46",
    "Thừa Thiên Huế": "46",
    "Thành phố Đà Nẵng": "48",
    "Đà Nẵng": "48",
    "Tỉnh Quảng Nam": "48",
    "Quảng Nam": "48",
    "Thành phố Hồ Chí Minh": "79",
    "Hồ Chí Minh": "79",
    "TP. Hồ Chí Minh": "79",
    "Tỉnh Bình Dương": "79",
    "Bình Dương": "79",
    "Tỉnh Bà Rịa - Vũng Tàu": "79",
    "Bà Rịa - Vũng Tàu": "79",
    "Thành phố Cần Thơ": "92",
    "Cần Thơ": "92",
    "Tỉnh Sóc Trăng": "92",
    "Sóc Trăng": "92",
    "Tỉnh Hậu Giang": "92",
    "Hậu Giang": "92",
    "Tỉnh Cao Bằng": "04",
    "Cao Bằng": "04",
    "Tỉnh Lạng Sơn": "20",
    "Lạng Sơn": "20",
    "Tỉnh Lai Châu": "12",
    "Lai Châu": "12",
    "Tỉnh Điện Biên": "11",
    "Điện Biên": "11",
    "Tỉnh Sơn La": "14",
    "Sơn La": "14",
    "Thành phố Quảng Ninh": "22",
    "Tỉnh Quảng Ninh": "22",
    "Quảng Ninh": "22",
    "Tỉnh Thanh Hóa": "38",
    "Tỉnh Thanh Hoá": "38",
    "Thanh Hóa": "38",
    "Thanh Hoá": "38",
    "Tỉnh Nghệ An": "40",
    "Nghệ An": "40",
    "Tỉnh Hà Tĩnh": "42",
    "Hà Tĩnh": "42",
    "Tỉnh Hà Giang": "08",
    "Hà Giang": "08",
    "Tỉnh Tuyên Quang": "08",
    "Tuyên Quang": "08",
    "Tỉnh Lào Cai": "15",
    "Lào Cai": "15",
    "Tỉnh Yên Bái": "15",
    "Yên Bái": "15",
    "Tỉnh Bắc Kạn": "19",
    "Bắc Kạn": "19",
    "Tỉnh Thái Nguyên": "19",
    "Thái Nguyên": "19",
    "Tỉnh Phú Thọ": "25",
    "Phú Thọ": "25",
    "Tỉnh Vĩnh Phúc": "25",
    "Vĩnh Phúc": "25",
    "Tỉnh Hòa Bình": "25",
    "Tỉnh Hoà Bình": "25",
    "Hòa Bình": "25",
    "Thành phố Bắc Ninh": "24",
    "Tỉnh Bắc Ninh": "24",
    "Bắc Ninh": "24",
    "Tỉnh Bắc Giang": "24",
    "Bắc Giang": "24",
    "Tỉnh Hưng Yên": "33",
    "Hưng Yên": "33",
    "Tỉnh Thái Bình": "33",
    "Thái Bình": "33",
    "Tỉnh Ninh Bình": "37",
    "Ninh Bình": "37",
    "Tỉnh Nam Định": "37",
    "Nam Định": "37",
    "Tỉnh Hà Nam": "37",
    "Hà Nam": "37",
    "Tỉnh Quảng Bình": "44",
    "Quảng Bình": "44",
    "Tỉnh Quảng Trị": "44",
    "Quảng Trị": "44",
    "Tỉnh Quảng Ngãi": "51",
    "Quảng Ngãi": "51",
    "Tỉnh Kon Tum": "51",
    "Kon Tum": "51",
    "Tỉnh Gia Lai": "52",
    "Gia Lai": "52",
    "Tỉnh Bình Định": "52",
    "Bình Định": "52",
    "Tỉnh Khánh Hòa": "56",
    "Tỉnh Khánh Hoà": "56",
    "Khánh Hòa": "56",
    "Khánh Hoà": "56",
    "Tỉnh Ninh Thuận": "56",
    "Ninh Thuận": "56",
    "Tỉnh Đắk Lắk": "66",
    "Tỉnh Đắc Lắc": "66",
    "Đắk Lắk": "66",
    "Tỉnh Phú Yên": "66",
    "Phú Yên": "66",
    "Tỉnh Lâm Đồng": "68",
    "Lâm Đồng": "68",
    "Tỉnh Đắk Nông": "68",
    "Tỉnh Đắc Nông": "68",
    "Đắk Nông": "68",
    "Tỉnh Bình Thuận": "68",
    "Bình Thuận": "68",
    "Thành phố Đồng Nai": "75",
    "Tỉnh Đồng Nai": "75",
    "Đồng Nai": "75",
    "Tỉnh Bình Phước": "75",
    "Bình Phước": "75",
    "Tỉnh Tây Ninh": "80",
    "Tây Ninh": "80",
    "Tỉnh Long An": "80",
    "Long An": "80",
    "Tỉnh Đồng Tháp": "82",
    "Đồng Tháp": "82",
    "Tỉnh Tiền Giang": "82",
    "Tiền Giang": "82",
    "Tỉnh Vĩnh Long": "86",
    "Vĩnh Long": "86",
    "Tỉnh Bến Tre": "86",
    "Bến Tre": "86",
    "Tỉnh Trà Vinh": "86",
    "Trà Vinh": "86",
    "Tỉnh An Giang": "91",
    "An Giang": "91",
    "Tỉnh Kiên Giang": "91",
    "Kiên Giang": "91",
    "Tỉnh Cà Mau": "96",
    "Cà Mau": "96",
    "Tỉnh Bạc Liêu": "96",
    "Bạc Liêu": "96",
}


async def get_provinces_for_select(db: Any = None) -> List[Dict[str, Any]]:
    """Retrieve province list from MongoDB metadata_provinces collection for dropdown selectors."""
    await ensure_province_collection_and_seed(db=db)
    items, _ = await province_repo.find_all(sort_field="id", sort_dir=1, db=db)
    return [
        {
            "id": p.get("id"),
            "code": str(p.get("code", "")),
            "name": p.get("name", ""),
            "full_name": p.get("full_name") or p.get("name", ""),
            "name_en": p.get("name_en", ""),
            "type": p.get("type", "Tỉnh"),
            "administrative_unit_id": p.get("administrative_unit_id", 2),
            "region": p.get("region", ""),
        }
        for p in items
    ]


async def resolve_province_mapping(
    province_id: Optional[int] = None,
    province_code: Optional[str] = None,
    province_name: Optional[str] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """Map any province identifier to canonical province_id, province_code, province_name from metadata_provinces."""
    await ensure_province_collection_and_seed(db=db)
    provinces, _ = await province_repo.find_all(db=db)

    # 1. Match by id
    if province_id is not None:
        try:
            pid = int(province_id)
            for p in provinces:
                if p.get("id") == pid:
                    return {
                        "province_id": p.get("id"),
                        "province_code": str(p.get("code")),
                        "province_name": p.get("name"),
                        "province_full_name": p.get("full_name") or p.get("name"),
                        "old_province_name": None,
                    }
        except (ValueError, TypeError):
            pass

    # 2. Match by code
    if province_code:
        pcode = str(province_code).strip()
        for p in provinces:
            if str(p.get("code", "")).strip() == pcode:
                return {
                    "province_id": p.get("id"),
                    "province_code": str(p.get("code")),
                    "province_name": p.get("name"),
                    "province_full_name": p.get("full_name") or p.get("name"),
                    "old_province_name": None,
                }

    # 3. Match by name
    if province_name:
        pname = str(province_name).strip()
        # Direct match in 34 provinces
        for p in provinces:
            if (
                p.get("name") == pname
                or p.get("full_name") == pname
                or pname.lower() == str(p.get("name", "")).lower()
                or pname.lower() == str(p.get("full_name", "")).lower()
            ):
                return {
                    "province_id": p.get("id"),
                    "province_code": str(p.get("code")),
                    "province_name": p.get("name"),
                    "province_full_name": p.get("full_name") or p.get("name"),
                    "old_province_name": None,
                }

        # Check old 63-province mapping
        mapped_code = OLD_TO_NEW_PROVINCE_CODE.get(pname)
        if mapped_code:
            for p in provinces:
                if str(p.get("code", "")).strip() == mapped_code:
                    return {
                        "province_id": p.get("id"),
                        "province_code": str(p.get("code")),
                        "province_name": p.get("name"),
                        "province_full_name": p.get("full_name") or p.get("name"),
                        "old_province_name": pname,
                    }

    return {
        "province_id": province_id,
        "province_code": province_code,
        "province_name": province_name,
        "province_full_name": province_name,
        "old_province_name": None,
    }


def load_vn_wards_json(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load the Vietnam wards dataset from data/vn_wards.json (3,321 wards)."""
    data_path = DATA_DIR / "vn_wards.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8-sig") as f:
            items = json.load(f)
            if limit is not None:
                return items[:limit]
            return items
    return []


async def ensure_ward_collection_and_seed(db: Any = None) -> bool:
    """Ensure the ward collection exists and seed with wards if empty."""
    index_specs = [
        ("id", True),
        "code",
        "name",
        "code_name",
        "type",
        "administrative_unit_id",
        "province_id",
        "province_code",
        "province_name",
        "status",
    ]
    wards = load_vn_wards_json()
    col = ward_repo.get_collection(db)
    if col is not None:
        try:
            total_count = await col.count_documents({})
            if total_count == 0:
                # Seed all wards
                return await ward_repo.seed_if_empty(wards, index_specs=index_specs, db=db)

            # Check if collection has outdated count (e.g. 152 legacy records)
            if total_count < 1000 or total_count > 4000:
                logger.info(f"Replacing legacy ward dataset (count: {total_count}) with standard 3,321 wards...")
                await col.delete_many({})
                docs = [dict(w) for w in wards]
                await col.insert_many(docs)
                ward_repo._memory_cache = docs
                return True
        except Exception as exc:
            logger.warning(f"Error checking ward collection: {exc}")

    return await ward_repo.seed_if_empty(wards, index_specs=index_specs, db=db)


async def get_distinct_ward_provinces(db: Any = None) -> List[str]:
    """Retrieve distinct province names present in the ward collection."""
    await ensure_ward_collection_and_seed(db=db)
    col = ward_repo.get_collection(db)
    if col is not None:
        try:
            provs = await col.distinct("province_name")
            return sorted([p for p in provs if p])
        except Exception:
            pass
    provinces = {w.get("province_name") for w in ward_repo._memory_cache if w.get("province_name")}
    return sorted(list(provinces))


async def list_wards(
    db: Any = None,
    search: str = "",
    province_filter: str = "all",
    type_filter: str = "all",
    status_filter: str = "all",
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """Retrieve wards from MongoDB with search, filters, pagination, and KPI counts."""
    await ensure_ward_collection_and_seed(db=db)

    query: Dict[str, Any] = {}
    if search:
        regex_pattern = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"name": regex_pattern},
            {"full_name": regex_pattern},
            {"name_en": regex_pattern},
            {"code": regex_pattern},
            {"code_name": regex_pattern},
            {"postal_code": regex_pattern},
            {"province_name": regex_pattern},
            {"province_full_name": regex_pattern},
            {"province_code": regex_pattern},
            {"old_province_name": regex_pattern},
            {"district_name": regex_pattern},
            {"merged_note": regex_pattern},
        ]

    if province_filter and province_filter != "all":
        query["$or"] = [
            {"province_code": province_filter},
            {"province_name": province_filter},
            {"province_full_name": province_filter},
            {"old_province_name": province_filter},
        ]

    if type_filter and type_filter != "all":
        if type_filter.isdigit():
            query["administrative_unit_id"] = int(type_filter)
        elif type_filter == "phuong":
            query["administrative_unit_id"] = 3
        elif type_filter == "xa":
            query["administrative_unit_id"] = 4
        elif type_filter == "dac_khu":
            query["administrative_unit_id"] = 5
        else:
            query["type"] = type_filter

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    items, pagination, db_connected = await ward_repo.find_paginated(
        query=query,
        sort_field="id",
        sort_dir=1,
        page=page,
        page_size=page_size,
        db=db,
    )

    # Compute quick stats
    active_count = 0
    phuong_count = 0
    xa_count = 0
    dackhu_count = 0
    thitran_count = 0

    if db_connected:
        col = ward_repo.get_collection(db)
        if col is not None:
            try:
                active_count = await col.count_documents({"status": "active"})
                phuong_count = await col.count_documents({
                    "$or": [{"administrative_unit_id": 3}, {"type": "Phường"}]
                })
                xa_count = await col.count_documents({
                    "$or": [{"administrative_unit_id": 4}, {"type": "Xã"}]
                })
                dackhu_count = await col.count_documents({
                    "$or": [
                        {"administrative_unit_id": 5},
                        {"type": {"$regex": "Đặc khu", "$options": "i"}},
                    ]
                })
            except Exception:
                active_count = sum(1 for w in items if w.get("status") == "active")
                phuong_count = sum(1 for w in items if w.get("administrative_unit_id") == 3 or w.get("type") == "Phường")
                xa_count = sum(1 for w in items if w.get("administrative_unit_id") == 4 or w.get("type") == "Xã")
                dackhu_count = sum(1 for w in items if w.get("administrative_unit_id") == 5 or "Đặc khu" in w.get("type", ""))
    else:
        active_count = sum(1 for w in items if w.get("status") == "active")
        phuong_count = sum(1 for w in items if w.get("administrative_unit_id") == 3 or w.get("type") == "Phường")
        xa_count = sum(1 for w in items if w.get("administrative_unit_id") == 4 or w.get("type") == "Xã")
        dackhu_count = sum(1 for w in items if w.get("administrative_unit_id") == 5 or "Đặc khu" in w.get("type", ""))

    provinces_list = await get_provinces_for_select(db=db)
    distinct_provinces = await get_distinct_ward_provinces(db=db)

    return {
        "items": items,
        "total": pagination.total_items,
        "active_count": active_count,
        "phuong_count": phuong_count,
        "xa_count": xa_count,
        "dackhu_count": dackhu_count,
        "thitran_count": thitran_count,  # backward compatibility
        "provinces_list": provinces_list,
        "distinct_provinces": distinct_provinces,
        "db_connected": db_connected,
        "pagination": pagination,
    }


async def create_ward(db: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new ward / commune in MongoDB, mapped with metadata_provinces."""
    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip()

    if not name:
        raise ValueError("Tên xã / phường là bắt buộc.")

    prov_info = await resolve_province_mapping(
        province_id=data.get("province_id"),
        province_code=data.get("province_code"),
        province_name=data.get("province_name"),
        db=db,
    )

    unit_id = int(data.get("administrative_unit_id") or 4)
    if "Phường" in str(data.get("type", "")):
        unit_id = 3
    elif "Đặc khu" in str(data.get("type", "")):
        unit_id = 5

    type_name = "Phường" if unit_id == 3 else ("Đặc khu" if unit_id == 5 else "Xã")
    unit_full_name = "Phường" if unit_id == 3 else ("Đặc khu tại hải đảo" if unit_id == 5 else "Xã")

    doc = {
        "name": name,
        "code": code or str(await ward_repo.get_next_id(db=db)),
        "name_en": str(data.get("name_en", "")).strip() or None,
        "full_name": str(data.get("full_name", "")).strip() or f"{type_name} {name}",
        "full_name_en": str(data.get("full_name_en", "")).strip() or None,
        "code_name": str(data.get("code_name", "")).strip() or None,
        "type": type_name,
        "administrative_unit_id": unit_id,
        "administrative_unit_name": unit_full_name,
        "province_id": prov_info.get("province_id"),
        "province_code": prov_info.get("province_code"),
        "province_name": prov_info.get("province_name") or str(data.get("province_name", "")).strip() or None,
        "province_full_name": prov_info.get("province_full_name") or prov_info.get("province_name"),
        "postal_code": str(data.get("postal_code", "")).strip() or None,
        "old_province_name": prov_info.get("old_province_name") or data.get("old_province_name"),
        "district_name": str(data.get("district_name", "")).strip() or None,
        "merged_note": str(data.get("merged_note", "")).strip() or "Đơn vị hành chính cấp xã chuẩn hóa",
        "status": str(data.get("status", "active")),
    }

    return await ward_repo.insert(doc, auto_id=True, db=db)


async def update_ward(db: Any, ward_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing ward / commune in MongoDB with province mapping."""
    update_fields: Dict[str, Any] = {}

    for f in ("name", "code", "name_en", "full_name", "full_name_en", "code_name", "type", "postal_code", "district_name", "merged_note", "status"):
        if f in data and data[f] is not None:
            update_fields[f] = str(data[f]).strip()

    if "administrative_unit_id" in data and data["administrative_unit_id"]:
        try:
            uid = int(data["administrative_unit_id"])
            update_fields["administrative_unit_id"] = uid
            update_fields["administrative_unit_name"] = "Phường" if uid == 3 else ("Đặc khu tại hải đảo" if uid == 5 else "Xã")
            update_fields["type"] = "Phường" if uid == 3 else ("Đặc khu" if uid == 5 else "Xã")
        except (ValueError, TypeError):
            pass

    # If any province identifier is updated, resolve and sync all province fields
    if any(k in data for k in ("province_id", "province_code", "province_name")):
        prov_info = await resolve_province_mapping(
            province_id=data.get("province_id"),
            province_code=data.get("province_code"),
            province_name=data.get("province_name"),
            db=db,
        )
        if prov_info.get("province_id") is not None:
            update_fields["province_id"] = prov_info["province_id"]
        if prov_info.get("province_code") is not None:
            update_fields["province_code"] = prov_info["province_code"]
        if prov_info.get("province_name") is not None:
            update_fields["province_name"] = prov_info["province_name"]
            update_fields["province_full_name"] = prov_info.get("province_full_name") or prov_info.get("province_name")
        if prov_info.get("old_province_name"):
            update_fields["old_province_name"] = prov_info["old_province_name"]

    return await ward_repo.update(ward_id, update_fields, db=db)


async def delete_ward(db: Any, ward_id: int) -> bool:
    """Delete a ward record from MongoDB."""
    return await ward_repo.delete(ward_id, db=db)


async def import_vn_wards(
    db: Any = None,
    limit: Optional[int] = None,
    reset: bool = False,
) -> Dict[str, Any]:
    """Import wards from local dataset file (vn_wards.json) into MongoDB."""
    ward_list = load_vn_wards_json(limit=limit)
    if not ward_list:
        return {"ok": False, "error": "Ward dataset file not found."}

    await ensure_ward_collection_and_seed(db=db)
    col = ward_repo.get_collection(db)

    if col is not None:
        try:
            if reset:
                await col.delete_many({})
                docs = [dict(item) for item in ward_list]
                await col.insert_many(docs)
                ward_repo._memory_cache = [dict(item) for item in ward_list]
                total = await col.count_documents({})
                return {
                    "ok": True,
                    "total_imported": len(ward_list),
                    "total_now": total,
                    "reset": True,
                }

            existing_codes = {str(d.get("code")) for d in await col.find({}, {"code": 1, "_id": 0}).to_list(30000)}
            to_insert = [dict(item) for item in ward_list if str(item.get("code")) not in existing_codes]
            if to_insert:
                await col.insert_many(to_insert)

            total = await col.count_documents({})
            return {
                "ok": True,
                "total_imported": len(to_insert),
                "total_now": total,
                "reset": False,
            }
        except Exception as exc:
            logger.error(f"Import wards error: {exc}")
            if ward_repo.enable_fallback:
                ward_repo._memory_cache = [dict(item) for item in ward_list]
                return {
                    "ok": True,
                    "total_imported": len(ward_list),
                    "total_now": len(ward_repo._memory_cache),
                    "fallback": True,
                }
            return {"ok": False, "error": str(exc)}

    if ward_repo.enable_fallback:
        ward_repo._memory_cache = [dict(item) for item in ward_list]
        return {
            "ok": True,
            "total_imported": len(ward_list),
            "total_now": len(ward_repo._memory_cache),
            "fallback": True,
        }

    return {"ok": False, "error": "Database not connected"}


async def sync_wards_from_web(
    db: Any = None,
    limit: Optional[int] = 1000,
    reset: bool = False,
) -> Dict[str, Any]:
    """Sync/reload wards dataset into MongoDB."""
    return await import_vn_wards(db=db, limit=limit, reset=reset)


async def migrate_all_vn_units(db: Any = None, reset: bool = True) -> Dict[str, Any]:
    """Master migration: seed/reset Administrative Regions, Administrative Units, Provinces, and Wards.

    According to:
    - administrative_regions.json (8 regions)
    - administrative_units.json (5 unit types)
    - mongo_data_vn_unit.json / vn_provinces.json (34 provinces)
    - mongo_data_vn_unit.json / vn_wards.json (3,321 wards)
    """
    results = {}

    # 1. Regions
    r_list = load_administrative_regions_json()
    r_col = region_repo.get_collection(db)
    if r_col is not None and reset:
        await r_col.delete_many({})
        if r_list:
            await r_col.insert_many([dict(r) for r in r_list])
        results["regions"] = len(r_list)
    else:
        await ensure_region_collection_and_seed(db=db)
        results["regions"] = len(r_list)

    # 2. Units
    u_list = load_administrative_units_json()
    u_col = unit_repo.get_collection(db)
    if u_col is not None and reset:
        await u_col.delete_many({})
        if u_list:
            await u_col.insert_many([dict(u) for u in u_list])
        results["units"] = len(u_list)
    else:
        await ensure_unit_collection_and_seed(db=db)
        results["units"] = len(u_list)

    # 3. Provinces
    p_res = await migrate_vn_provinces(db=db, overwrite=True, reset=reset)
    results["provinces"] = p_res

    # 4. Wards
    w_res = await import_vn_wards(db=db, reset=reset)
    results["wards"] = w_res

    results["ok"] = True
    return results
