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
) -> Dict[str, Any]:
    """Retrieve countries from MongoDB with optional search and filter."""
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

    items, db_connected = await country_repo.find_all(
        query=query,
        sort_field="id",
        sort_dir=1,
        limit=1000,
        db=db,
    )

    # In-memory search fallback if DB was offline
    if not db_connected and (search or (status_filter and status_filter != "all")):
        filtered = list(items)
        if search:
            st = search.strip().lower()
            filtered = [
                c for c in filtered
                if st in c.get("name", "").lower()
                or st in c.get("country_code", "").lower()
                or st in c.get("phone_code", "").lower()
                or st in (c.get("native_name") or "").lower()
            ]
        if status_filter and status_filter != "all":
            filtered = [c for c in filtered if c.get("status") == status_filter]
        items = filtered

    active_count = sum(1 for c in items if c.get("status") == "active")
    return {
        "items": items,
        "total": len(items),
        "active_count": active_count,
        "db_connected": db_connected,
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
