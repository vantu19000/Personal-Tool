"""Base MongoDB Repository and helper utilities for reusable data access.

This module provides `BaseMongoRepository`, an asynchronous CRUD base class that can
be extended or instantiated for any MongoDB collection in the system (e.g. metadata,
configurations, logs, history, future tools/modules).

Key capabilities:
- Asynchronous CRUD (find_all, find_by_id, find_one, insert, update, delete, count)
- Auto-incrementing integer or custom ID support
- Automatic `created_at` and `updated_at` management
- Index creation helper
- Initial data seeding helper (`seed_if_empty`)
- Graceful in-memory fallback cache when MongoDB is unreachable (dev/offline resiliency)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.database import get_mongo_database
from app.core.pagination import PaginationMeta

logger = logging.getLogger(__name__)


def current_timestamp_str() -> str:
    """Return standard formatted timestamp with second precision for accurate chronological sorting."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class BaseMongoRepository:
    """Generic async repository for MongoDB collections with built-in fallback."""

    def __init__(
        self,
        collection_name: str,
        id_field: str = "id",
        enable_fallback: bool = True,
    ) -> None:
        self.collection_name = collection_name
        self.id_field = id_field
        self.enable_fallback = enable_fallback
        self._memory_cache: List[Dict[str, Any]] = []
        self._initialized = False

    def get_collection(self, db: Optional[Any] = None) -> Optional[Any]:
        """Return the Motor collection instance if connected."""
        target_db = db if db is not None else get_mongo_database()
        if target_db is not None:
            try:
                return target_db[self.collection_name]
            except Exception as exc:
                logger.warning(f"Failed to access collection {self.collection_name}: {exc}")
        return None

    async def is_connected(self, db: Optional[Any] = None) -> bool:
        """Check if MongoDB connection is currently alive."""
        col = self.get_collection(db)
        if col is None:
            return False
        try:
            # Quick ping/count to ensure socket is operational
            await col.database.command("ping")
            return True
        except Exception:
            return False

    async def ensure_indexes(
        self,
        index_specs: List[Union[str, Tuple[str, bool]]],
        db: Optional[Any] = None,
    ) -> None:
        """Ensure indexes on collection.

        Args:
            index_specs: List of field names or tuples of (field_name, unique_bool).
                         e.g. ["name", ("code", True), ("id", True)]
        """
        col = self.get_collection(db)
        if col is None:
            return

        for spec in index_specs:
            try:
                if isinstance(spec, tuple):
                    field_name, is_unique = spec
                    await col.create_index(field_name, unique=is_unique)
                else:
                    await col.create_index(spec)
            except Exception as exc:
                logger.debug(f"Index creation notice for '{spec}' on '{self.collection_name}': {exc}")

    async def seed_if_empty(
        self,
        default_items: List[Dict[str, Any]],
        index_specs: Optional[List[Union[str, Tuple[str, bool]]]] = None,
        db: Optional[Any] = None,
    ) -> bool:
        """Populate collection with default items if empty, and sync memory cache."""
        # Always keep fallback cache up to date
        if not self._memory_cache:
            self._memory_cache = [dict(item) for item in default_items]

        col = self.get_collection(db)
        if col is None:
            return False

        try:
            count = await col.count_documents({})
            if count == 0:
                logger.info(f"Collection '{self.collection_name}' is empty. Seeding {len(default_items)} records...")
                docs = [dict(item) for item in default_items]
                await col.insert_many(docs)
                logger.info(f"Seeded '{self.collection_name}' successfully.")

            if index_specs:
                await self.ensure_indexes(index_specs, db=db)

            self._initialized = True
            return True
        except Exception as exc:
            logger.warning(f"Could not seed collection '{self.collection_name}': {exc}")
            return False

    async def find_all(
        self,
        query: Optional[Dict[str, Any]] = None,
        sort_field: Optional[str] = None,
        sort_dir: int = 1,
        skip: int = 0,
        limit: int = 1000,
        projection: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch records matching query. Returns (items, is_db_connected)."""
        col = self.get_collection(db)
        if col is not None:
            try:
                proj = projection if projection is not None else {"_id": 0}
                cursor = col.find(query or {}, proj)
                if sort_field:
                    if sort_field != self.id_field:
                        cursor = cursor.sort([(sort_field, sort_dir), (self.id_field, sort_dir)])
                    else:
                        cursor = cursor.sort(self.id_field, sort_dir)
                else:
                    cursor = cursor.sort(self.id_field, -1)

                if skip > 0:
                    cursor = cursor.skip(skip)
                if limit > 0:
                    cursor = cursor.limit(limit)

                items = await cursor.to_list(length=limit if limit > 0 else 1000)
                # Keep memory cache synced with latest data
                if not query:
                    self._memory_cache = [dict(it) for it in items]
                return items, True
            except Exception as exc:
                logger.warning(f"MongoDB find_all on '{self.collection_name}' failed: {exc}")

        # Fallback to in-memory cache
        items = list(self._memory_cache)
        if sort_field:
            items.sort(
                key=lambda x: (str(x.get(sort_field) or ""), x.get(self.id_field) or 0),
                reverse=(sort_dir == -1),
            )
        else:
            items.sort(key=lambda x: x.get(self.id_field) or 0, reverse=True)
        return items, False

    async def find_paginated(
        self,
        query: Optional[Dict[str, Any]] = None,
        sort_field: Optional[str] = None,
        sort_dir: int = 1,
        page: int = 1,
        page_size: int = 25,
        projection: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None,
    ) -> Tuple[List[Dict[str, Any]], PaginationMeta, bool]:
        """Fetch a paginated slice of records from MongoDB with total counting.

        Returns:
            (items, pagination_meta, is_db_connected)
        """
        col = self.get_collection(db)
        if col is not None:
            try:
                clean_query = query or {}
                total_items = await col.count_documents(clean_query)
                meta = PaginationMeta.create(page=page, page_size=page_size, total_items=total_items)

                skip = (meta.page - 1) * meta.page_size
                proj = projection if projection is not None else {"_id": 0}
                cursor = col.find(clean_query, proj)
                if sort_field:
                    if sort_field != self.id_field:
                        cursor = cursor.sort([(sort_field, sort_dir), (self.id_field, sort_dir)])
                    else:
                        cursor = cursor.sort(self.id_field, sort_dir)
                else:
                    cursor = cursor.sort(self.id_field, -1)

                cursor = cursor.skip(skip).limit(meta.page_size)
                items = await cursor.to_list(length=meta.page_size)
                return items, meta, True
            except Exception as exc:
                logger.warning(f"MongoDB find_paginated on '{self.collection_name}' failed: {exc}")

        # Fallback to in-memory cache
        filtered = list(self._memory_cache)
        if sort_field:
            filtered.sort(
                key=lambda x: (str(x.get(sort_field) or ""), x.get(self.id_field) or 0),
                reverse=(sort_dir == -1),
            )
        else:
            filtered.sort(key=lambda x: x.get(self.id_field) or 0, reverse=True)

        total_items = len(filtered)
        meta = PaginationMeta.create(page=page, page_size=page_size, total_items=total_items)
        start = (meta.page - 1) * meta.page_size
        end = start + meta.page_size
        items = filtered[start:end]
        return items, meta, False

    async def find_by_id(
        self,
        id_val: Any,
        projection: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find single record by id_field."""
        col = self.get_collection(db)
        if col is not None:
            try:
                proj = projection if projection is not None else {"_id": 0}
                doc = await col.find_one({self.id_field: id_val}, proj)
                if doc is not None:
                    return doc
            except Exception as exc:
                logger.warning(f"MongoDB find_by_id on '{self.collection_name}' failed: {exc}")

        # Fallback
        for item in self._memory_cache:
            if str(item.get(self.id_field)) == str(id_val):
                return dict(item)
        return None

    async def find_one(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Tuple[str, int]]] = None,
        db: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find single record matching filter query."""
        col = self.get_collection(db)
        if col is not None:
            try:
                proj = projection if projection is not None else {"_id": 0}
                doc = await col.find_one(query, proj, sort=sort)
                if doc is not None:
                    return doc
            except Exception as exc:
                logger.warning(f"MongoDB find_one on '{self.collection_name}' failed: {exc}")

        # Fallback to in-memory cache
        for item in self._memory_cache:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return dict(item)

        return None

    async def get_next_id(self, db: Optional[Any] = None) -> int:
        """Calculate next autoincrement integer ID."""
        col = self.get_collection(db)
        if col is not None:
            try:
                last_doc = await col.find_one(sort=[(self.id_field, -1)])
                if last_doc and isinstance(last_doc.get(self.id_field), int):
                    return last_doc[self.id_field] + 1
            except Exception:
                pass
        # Fallback to cache max
        return max([c.get(self.id_field, 0) for c in self._memory_cache if isinstance(c.get(self.id_field), int)], default=0) + 1

    async def insert(
        self,
        doc_data: Dict[str, Any],
        auto_id: bool = True,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Insert a document with auto timestamp and optional auto integer ID."""
        new_doc = dict(doc_data)
        now_ts = current_timestamp_str()

        if auto_id and (self.id_field not in new_doc or new_doc[self.id_field] is None):
            new_doc[self.id_field] = await self.get_next_id(db=db)

        if "created_at" not in new_doc or not new_doc["created_at"]:
            new_doc["created_at"] = now_ts
        if "updated_at" not in new_doc or not new_doc["updated_at"]:
            new_doc["updated_at"] = now_ts

        col = self.get_collection(db)
        if col is not None:
            try:
                # Remove _id if accidentally passed as None
                clean_doc = dict(new_doc)
                clean_doc.pop("_id", None)
                await col.insert_one(clean_doc)
                clean_doc.pop("_id", None)
                # Keep cache in sync
                self._memory_cache.append(clean_doc)
                return clean_doc
            except Exception as exc:
                logger.warning(f"MongoDB insert on '{self.collection_name}' failed: {exc}")

        # Fallback cache
        self._memory_cache.append(new_doc)
        return new_doc

    async def update(
        self,
        id_val: Any,
        update_data: Dict[str, Any],
        db: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update document by id_field."""
        clean_update = dict(update_data)
        clean_update.pop("_id", None)
        clean_update.pop(self.id_field, None)
        clean_update["updated_at"] = update_data.get("updated_at") or current_timestamp_str()

        col = self.get_collection(db)
        if col is not None:
            try:
                res = await col.find_one_and_update(
                    {self.id_field: id_val},
                    {"$set": clean_update},
                    projection={"_id": 0},
                    return_document=True,
                )
                if res:
                    for item in self._memory_cache:
                        if item.get(self.id_field) == id_val:
                            item.update(res)
                    return res
            except Exception as exc:
                logger.warning(f"MongoDB update on '{self.collection_name}' failed: {exc}")

        # Fallback
        for item in self._memory_cache:
            if str(item.get(self.id_field)) == str(id_val):
                item.update(clean_update)
                return item
        return None

    async def delete(
        self,
        id_val: Any,
        db: Optional[Any] = None,
    ) -> bool:
        """Delete document by id_field."""
        col = self.get_collection(db)
        if col is not None:
            try:
                res = await col.delete_one({self.id_field: id_val})
                if res.deleted_count > 0:
                    self._memory_cache = [c for c in self._memory_cache if c.get(self.id_field) != id_val]
                    return True
            except Exception as exc:
                logger.warning(f"MongoDB delete on '{self.collection_name}' failed: {exc}")

        # Fallback
        init_len = len(self._memory_cache)
        self._memory_cache = [c for c in self._memory_cache if str(c.get(self.id_field)) != str(id_val)]
        return len(self._memory_cache) < init_len

    async def count(
        self,
        query: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None,
    ) -> int:
        """Count documents matching query."""
        col = self.get_collection(db)
        if col is not None:
            try:
                return await col.count_documents(query or {})
            except Exception as exc:
                logger.warning(f"MongoDB count on '{self.collection_name}' failed: {exc}")

        return len(self._memory_cache)
