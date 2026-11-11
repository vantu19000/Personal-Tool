"""Services for Country Metadata management with MongoDB.

Interacts with MongoDB database via Motor async client.
Provides automatic collection creation, initial data seeding, and fallback support
if the MongoDB Docker container is temporarily offline.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

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

# In-memory storage for offline / dev demo fallback
_IN_MEMORY_CACHE: List[Dict[str, Any]] = [dict(c) for c in DEFAULT_COUNTRIES]


async def ensure_collection_and_seed(db: Any) -> bool:
    """Ensure the collection exists in MongoDB and seed default countries if empty."""
    if db is None:
        return False
    try:
        col = db[COLLECTION_NAME]
        count = await col.count_documents({})
        if count == 0:
            logger.info("MongoDB collection 'metadata_countries' is empty. Seeding initial countries...")
            docs = [dict(c) for c in DEFAULT_COUNTRIES]
            await col.insert_many(docs)
            try:
                await col.create_index("id", unique=True)
                await col.create_index("country_code", unique=True)
                await col.create_index("name")
            except Exception:
                pass
            logger.info(f"Seeded {len(DEFAULT_COUNTRIES)} countries to MongoDB successfully.")
        return True
    except Exception as exc:
        logger.warning(f"Could not connect to MongoDB or seed collection: {exc}")
        return False


async def list_countries(
    db: Any,
    search: str = "",
    status_filter: str = "",
) -> Dict[str, Any]:
    """Retrieve countries from MongoDB, with automatic fallback to memory cache if DB is offline."""
    db_connected = False
    items: List[Dict[str, Any]] = []

    if db is not None:
        try:
            await ensure_collection_and_seed(db)
            col = db[COLLECTION_NAME]

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

            cursor = col.find(query, {"_id": 0}).sort("id", 1)
            items = await cursor.to_list(length=1000)
            db_connected = True
        except Exception as exc:
            logger.warning(f"MongoDB query failed, using in-memory fallback: {exc}")
            db_connected = False

    if not db_connected:
        filtered = list(_IN_MEMORY_CACHE)
        if search:
            st = search.strip().lower()
            filtered = [
                c for c in filtered
                if st in c["name"].lower()
                or st in c["country_code"].lower()
                or st in c["phone_code"].lower()
                or st in c.get("native_name", "").lower()
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

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    if db is not None:
        try:
            col = db[COLLECTION_NAME]
            # Find max id
            last_item = await col.find_one(sort=[("id", -1)])
            new_id = (last_item.get("id", 0) + 1) if last_item else 1

            new_doc = {
                "id": new_id,
                "name": name,
                "country_code": country_code,
                "phone_code": phone_code,
                "native_name": str(data.get("native_name", "")).strip() or None,
                "flag_emoji": str(data.get("flag_emoji", "")).strip() or "🌐",
                "currency_code": str(data.get("currency_code", "")).strip().upper() or None,
                "status": str(data.get("status", "active")),
                "created_at": now_str,
                "updated_at": now_str,
            }
            await col.insert_one(dict(new_doc))
            # Also keep memory sync
            _IN_MEMORY_CACHE.append(new_doc)
            return new_doc
        except Exception as exc:
            logger.warning(f"MongoDB insert failed, saving to in-memory fallback: {exc}")

    # Fallback to memory
    new_id = max([c["id"] for c in _IN_MEMORY_CACHE], default=0) + 1
    new_doc = {
        "id": new_id,
        "name": name,
        "country_code": country_code,
        "phone_code": phone_code,
        "native_name": str(data.get("native_name", "")).strip() or None,
        "flag_emoji": str(data.get("flag_emoji", "")).strip() or "🌐",
        "currency_code": str(data.get("currency_code", "")).strip().upper() or None,
        "status": str(data.get("status", "active")),
        "created_at": now_str,
        "updated_at": now_str,
    }
    _IN_MEMORY_CACHE.append(new_doc)
    return new_doc


async def update_country(db: Any, country_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing country in MongoDB."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    update_fields: Dict[str, Any] = {"updated_at": now_str}

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

    if db is not None:
        try:
            col = db[COLLECTION_NAME]
            res = await col.find_one_and_update(
                {"id": country_id},
                {"$set": update_fields},
                projection={"_id": 0},
                return_document=True,
            )
            if res:
                # Update memory
                for c in _IN_MEMORY_CACHE:
                    if c["id"] == country_id:
                        c.update(res)
                return res
        except Exception as exc:
            logger.warning(f"MongoDB update failed: {exc}")

    # Fallback to memory
    for c in _IN_MEMORY_CACHE:
        if c["id"] == country_id:
            c.update(update_fields)
            return c
    return None


async def delete_country(db: Any, country_id: int) -> bool:
    """Delete a country record from MongoDB."""
    if db is not None:
        try:
            col = db[COLLECTION_NAME]
            res = await col.delete_one({"id": country_id})
            if res.deleted_count > 0:
                global _IN_MEMORY_CACHE
                _IN_MEMORY_CACHE = [c for c in _IN_MEMORY_CACHE if c["id"] != country_id]
                return True
        except Exception as exc:
            logger.warning(f"MongoDB delete failed: {exc}")

    # Fallback
    initial_len = len(_IN_MEMORY_CACHE)
    _IN_MEMORY_CACHE = [c for c in _IN_MEMORY_CACHE if c["id"] != country_id]
    return len(_IN_MEMORY_CACHE) < initial_len
