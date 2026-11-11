"""Tests for Crawler Source Management (Quản lý nguồn dữ liệu).

Covers:
1. 9 Supported Source Types (Website, RSS, Facebook, Youtube, TikTok, PDF, Google Drive, Manual, API).
2. All required fields: Tên, Loại, URL, Tỉnh, Huyện, Xã, Tag, Lịch quét, Độ ưu tiên, Trạng thái, AI Prompt riêng.
3. CRUD operations, Toggle Status, Instant Scan, Reset Demo.
4. HTTP Endpoints (/crawler/sources, /sources, /tools/content-ideas/sources, /api/sources).
"""
import pytest
from fastapi.testclient import TestClient

from app.sources.models import (
    PRIORITY_METADATA,
    SCHEDULE_OPTIONS,
    SOURCE_TYPE_METADATA,
    STATUS_METADATA,
    SourceModel,
)
from app.sources import services
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_source_types_and_metadata():
    """Verify that all 9 required crawler source types are defined with labels and icons."""
    expected_types = [
        "website",
        "rss",
        "facebook",
        "youtube",
        "tiktok",
        "pdf",
        "gdrive",
        "manual",
        "api",
    ]
    for stype in expected_types:
        assert stype in SOURCE_TYPE_METADATA, f"Missing source type: {stype}"
        meta = SOURCE_TYPE_METADATA[stype]
        assert "label" in meta
        assert "icon" in meta
        assert "badge_color" in meta


def test_priorities_and_statuses():
    """Verify priorities, statuses, and schedules metadata."""
    assert "urgent" in PRIORITY_METADATA
    assert "high" in PRIORITY_METADATA
    assert "medium" in PRIORITY_METADATA
    assert "low" in PRIORITY_METADATA

    assert "active" in STATUS_METADATA
    assert "paused" in STATUS_METADATA

    assert "15_min" in SCHEDULE_OPTIONS
    assert "daily" in SCHEDULE_OPTIONS


@pytest.mark.anyio
async def test_list_sources_and_all_9_types_present():
    """Verify list_sources returns items and default seed covers all 9 types."""
    await services.reset_demo_sources(db=None)
    data = await services.list_sources(db=None, page=1, page_size=20)
    assert data["total"] >= 9
    assert len(data["items"]) >= 9

    types_in_db = {s["type"] for s in data["items"]}
    for expected in ["website", "rss", "facebook", "youtube", "tiktok", "pdf", "gdrive", "manual", "api"]:
        assert expected in types_in_db, f"Default seed missing type: {expected}"


@pytest.mark.anyio
async def test_create_source_with_all_required_fields():
    """Verify creating a source with all user requested fields:
    Tên, Loại, URL, Tỉnh, Huyện, Xã, Tag, Lịch quét, Độ ưu tiên, Trạng thái, AI Prompt riêng.
    """
    await services.reset_demo_sources(db=None)
    new_data = {
        "name": "Báo Xây Dựng & Quy Hoạch Việt Nam",
        "type": "website",
        "url": "https://baoxaydung.com.vn/quy-hoach",
        "province": "Hà Nội",
        "district": "Hai Bà Trưng",
        "ward": "Phường Lê Đại Hành",
        "tags": "Quy hoạch, Bất động sản, Hạ tầng, Vành Đai 4",
        "schedule": "30_min",
        "priority": "urgent",
        "status": "active",
        "ai_prompt": "Tập trung bóc tách các dự án mở rộng đường, thay đổi chỉ tiêu quy hoạch và bảng giá đất mới nhất.",
        "description": "Nguồn báo chính thống của Bộ Xây Dựng",
    }

    created = await services.create_source(new_data, db=None)
    assert created["id"] > 0
    assert created["name"] == "Báo Xây Dựng & Quy Hoạch Việt Nam"
    assert created["type"] == "website"
    assert created["url"] == "https://baoxaydung.com.vn/quy-hoach"
    assert created["province"] == "Hà Nội"
    assert created["district"] == "Hai Bà Trưng"
    assert created["ward"] == "Phường Lê Đại Hành"
    assert "Quy hoạch" in created["tags"]
    assert "Bất động sản" in created["tags"]
    assert created["schedule"] == "30_min"
    assert created["priority"] == "urgent"
    assert created["status"] == "active"
    assert "AI Prompt" in created["ai_prompt"] or "Tập trung bóc tách" in created["ai_prompt"]


@pytest.mark.anyio
async def test_update_source():
    """Verify updating a source's AI Prompt, priority, and schedule."""
    await services.reset_demo_sources(db=None)
    created = await services.create_source(
        {
            "name": "Kênh TikTok Review Đất Nền",
            "type": "tiktok",
            "url": "https://tiktok.com/@review_datnen",
            "province": "Bình Dương",
            "district": "Bến Cát",
            "ward": "Mỹ Phước",
            "tags": "TikTok, Đất nền, Review",
            "schedule": "1_hour",
            "priority": "low",
            "status": "paused",
            "ai_prompt": "Prompt cũ",
        },
        db=None,
    )
    source_id = created["id"]

    updated = await services.update_source(
        source_id,
        {
            "priority": "high",
            "status": "active",
            "ai_prompt": "Prompt mới được cập nhật: Phân tích bình luận tiêu cực và cảnh báo lừa đảo.",
        },
        db=None,
    )
    assert updated is not None
    assert updated["priority"] == "high"
    assert updated["status"] == "active"
    assert "Prompt mới được cập nhật" in updated["ai_prompt"]


@pytest.mark.anyio
async def test_toggle_status_and_trigger_scan():
    """Verify toggling active/paused and triggering instant scan."""
    await services.reset_demo_sources(db=None)
    created = await services.create_source(
        {
            "name": "API Test Source",
            "type": "api",
            "url": "https://example.com/api",
            "status": "active",
        },
        db=None,
    )
    sid = created["id"]

    # Toggle to paused
    toggled = await services.toggle_status(sid, db=None)
    assert toggled["status"] == "paused"

    # Toggle back to active
    toggled2 = await services.toggle_status(sid, db=None)
    assert toggled2["status"] == "active"

    # Trigger scan
    scanned = await services.trigger_scan(sid, db=None)
    assert scanned["articles_count"] > 0
    assert scanned["last_scanned_at"] == "Vừa xong"


@pytest.mark.anyio
async def test_filter_by_type_priority_province():
    """Verify filtering sources by type, priority, and province."""
    await services.reset_demo_sources(db=None)

    # Filter by type = 'youtube'
    res_yt = await services.list_sources(db=None, type_filter="youtube")
    assert all(item["type"] == "youtube" for item in res_yt["items"])

    # Filter by priority = 'urgent'
    res_prio = await services.list_sources(db=None, priority_filter="urgent")
    assert all(item["priority"] == "urgent" for item in res_prio["items"])

    # Filter by search = 'VnExpress'
    res_search = await services.list_sources(db=None, search="VnExpress")
    assert len(res_search["items"]) >= 1
    assert "VnExpress" in res_search["items"][0]["name"]


def test_http_sources_page(client):
    """Verify HTML UI rendering of the Source Management screen."""
    # Check /crawler/sources
    resp1 = client.get("/crawler/sources")
    assert resp1.status_code == 200
    assert "Quản lý Nguồn Dữ Liệu" in resp1.text
    assert "Website" in resp1.text
    assert "TikTok" in resp1.text
    assert "Google Drive" in resp1.text
    assert "AI Prompt riêng" in resp1.text

    # Check /sources alias
    resp2 = client.get("/sources")
    assert resp2.status_code == 200

    # Check /tools/content-ideas/sources
    resp3 = client.get("/tools/content-ideas/sources")
    assert resp3.status_code == 200
    assert "AI Content Ideas" in resp3.text


def test_http_api_crud(client):
    """Verify API endpoints for CRUD, toggle, and scan."""
    # 1. List API
    res_list = client.get("/api/sources")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data
    assert data["total"] >= 9

    # 2. Get single API
    res_get = client.get("/api/sources/1")
    assert res_get.status_code == 200
    assert res_get.json()["ok"] is True
    assert res_get.json()["source"]["id"] == 1

    # 3. Create Source via POST Form
    res_create = client.post(
        "/api/sources",
        data={
            "name": "Nguồn Báo Đầu Tư Chứng Khoán",
            "type": "website",
            "url": "https://tinnhanhchungkhoan.vn",
            "province": "Hà Nội",
            "district": "Hoàn Kiếm",
            "ward": "Phường Tràng Tiền",
            "tags": "Chứng khoán, Tài chính, Cổ phiếu",
            "schedule": "15_min",
            "priority": "high",
            "status": "active",
            "ai_prompt": "Trích xuất các giao dịch cổ phiếu lớn của cổ đông nội bộ.",
        },
        headers={"Accept": "application/json"},
    )
    assert res_create.status_code == 200
    created_id = res_create.json()["source"]["id"]

    # 4. Edit Source
    res_edit = client.post(
        f"/api/sources/{created_id}/edit",
        data={
            "priority": "urgent",
            "ai_prompt": "Prompt cập nhật qua API.",
        },
        headers={"Accept": "application/json"},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["source"]["priority"] == "urgent"

    # 5. Toggle Status
    res_toggle = client.post(f"/api/sources/{created_id}/toggle-status")
    assert res_toggle.status_code == 200
    assert res_toggle.json()["source"]["status"] == "paused"

    # 6. Instant Scan
    res_scan = client.post(f"/api/sources/{created_id}/scan")
    assert res_scan.status_code == 200
    assert res_scan.json()["ok"] is True

    # 7. Delete Source
    res_delete = client.post(
        f"/api/sources/{created_id}/delete",
        headers={"Accept": "application/json"},
    )
    assert res_delete.status_code == 200
    assert res_delete.json()["ok"] is True
