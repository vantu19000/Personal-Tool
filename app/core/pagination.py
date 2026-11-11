"""Standard Pagination helper and metadata generator for reusable usage across all screens.

Provides:
- `PaginationMeta`: Data model and generator for calculating page ranges, ellipses,
  boundaries, and navigation flags.
- `build_page_url`: URL generator preserving current query parameters (search, filter, etc.)
  while swapping `page` and/or `page_size`.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Metadata describing a paginated collection."""

    page: int = 1
    page_size: int = 25
    total_items: int = 0
    total_pages: int = 1
    start_index: int = 0
    end_index: int = 0
    has_prev: bool = False
    has_next: bool = False
    prev_page: Optional[int] = None
    next_page: Optional[int] = None
    page_range: List[Union[int, str]] = Field(default_factory=list)
    page_size_options: List[int] = Field(default_factory=lambda: [10, 25, 50, 100])

    @classmethod
    def create(
        cls,
        page: int,
        page_size: int,
        total_items: int,
        delta: int = 2,
        page_size_options: Optional[List[int]] = None,
    ) -> PaginationMeta:
        """Create a PaginationMeta instance with calculated windowing and page range."""
        page_size = max(1, page_size)
        total_pages = max(1, math.ceil(total_items / page_size)) if total_items > 0 else 1
        page = max(1, min(page, total_pages))

        start_index = (page - 1) * page_size + 1 if total_items > 0 else 0
        end_index = min(page * page_size, total_items) if total_items > 0 else 0

        has_prev = page > 1
        has_next = page < total_pages
        prev_page = page - 1 if has_prev else None
        next_page = page + 1 if has_next else None

        # Calculate sliding page window: e.g. [1, '...', 4, 5, 6, '...', 10]
        page_range: List[Union[int, str]] = []
        left = max(1, page - delta)
        right = min(total_pages, page + delta)

        if left > 1:
            page_range.append(1)
            if left > 2:
                page_range.append("...")

        for p in range(left, right + 1):
            page_range.append(p)

        if right < total_pages:
            if right < total_pages - 1:
                page_range.append("...")
            page_range.append(total_pages)

        opts = page_size_options or [10, 25, 50, 100]

        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            start_index=start_index,
            end_index=end_index,
            has_prev=has_prev,
            has_next=has_next,
            prev_page=prev_page,
            next_page=next_page,
            page_range=page_range,
            page_size_options=opts,
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def build_page_url(request: Any, page: int, page_size: Optional[int] = None) -> str:
    """Build a URL preserving current query parameters while setting page and/or page_size."""
    if not request or not hasattr(request, "query_params"):
        qs = f"page={page}"
        if page_size:
            qs += f"&page_size={page_size}"
        return f"?{qs}"

    params = dict(request.query_params)
    params["page"] = str(page)
    if page_size:
        params["page_size"] = str(page_size)

    path = request.url.path if hasattr(request, "url") else ""
    return f"{path}?{urlencode(params)}"
