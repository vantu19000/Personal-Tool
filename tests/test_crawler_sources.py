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
async def test_toggle_status_and_trigger_scan(monkeypatch):
    """Verify toggling active/paused and triggering instant scan."""
    from app.sources import crawler

    async def mock_api(url, limit=10):
        return [{
            "title": "Chỉ số xuất nhập khẩu tháng này đạt mức cao",
            "summary": "Báo cáo số liệu giao thương...",
            "content": "Báo cáo chi tiết...",
            "url": "https://example.com/api/indicator-q1",
        }]

    monkeypatch.setattr(crawler, "fetch_api_content", mock_api)

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
    assert "new_count" in res_scan.json()
    assert "duplicate_count" in res_scan.json()

    # 7. Delete Source
    res_delete = client.post(
        f"/api/sources/{created_id}/delete",
        headers={"Accept": "application/json"},
    )
    assert res_delete.status_code == 200
    assert res_delete.json()["ok"] is True


def test_normalize_url_and_deduplication_helpers():
    """Verify URL normalization strips tracking params, trailing slashes, and anchors."""
    from app.sources.crawler import normalize_title, normalize_url

    u1 = "https://vnexpress.net/bat-dong-san/tin-thi-truong-van-phong-2026/"
    u2 = "https://vnexpress.net/bat-dong-san/tin-thi-truong-van-phong-2026?utm_source=facebook&utm_medium=cpc"
    u3 = "https://vnexpress.net/bat-dong-san/tin-thi-truong-van-phong-2026#comment-section"

    assert normalize_url(u1) == normalize_url(u2)
    assert normalize_url(u2) == normalize_url(u3)
    assert normalize_url(u1) == "https://vnexpress.net/bat-dong-san/tin-thi-truong-van-phong-2026"

    t1 = "  Hướng Dẫn SMB Tự Setup AI Agent ! "
    t2 = "hướng dẫn smb tự setup ai agent"
    assert normalize_title(t1) == normalize_title(t2)


@pytest.mark.anyio
async def test_crawl_saves_to_articles_and_deduplicates(monkeypatch):
    """Verify crawl saves into crawled_articles and strictly prevents duplicates on subsequent runs."""
    from app.articles import services as article_services
    from app.sources import crawler
    from app.sources.crawler import crawl_source_and_save

    async def mock_rss(url, limit=10):
        return [
            {
                "title": "Quy hoạch phân khu đô thị Hà Nội mới nhất 2026",
                "summary": "Thông tin chi tiết bản đồ quy hoạch xây dựng thủ đô đến năm 2030...",
                "content": "Nội dung phân tích quy hoạch các trục hướng tâm và vành đai...",
                "url": "https://example.com/quy-hoach-ha-noi-2026",
            },
            {
                "title": "Thị trường BĐS công nghiệp phía Bắc bứt phá mạnh",
                "summary": "Nhu cầu thuê nhà xưởng tiêu chuẩn cao tăng trưởng 2 con số...",
                "content": "Báo cáo chi tiết dòng vốn FDI đổ vào các khu công nghiệp...",
                "url": "https://example.com/bds-cong-nghiep-phia-bac",
            },
        ]

    monkeypatch.setattr(crawler, "fetch_rss_feed", mock_rss)

    await services.reset_demo_sources(db=None)
    await article_services.reset_demo_articles(db=None)

    articles_before = await article_services.list_articles(db=None, page=1, page_size=100)
    count_before = articles_before["total"]

    # --- Run 1: Crawl Source ID 2 (RSS) ---
    res1 = await crawl_source_and_save(source_id=2, db=None)
    assert res1["ok"] is True
    assert res1["scanned_count"] == 2
    assert res1["new_count"] == 2

    articles_after_run1 = await article_services.list_articles(db=None, page=1, page_size=100)
    count_after_run1 = articles_after_run1["total"]
    assert count_after_run1 == count_before + 2

    # Verify newly saved articles belong to Source 2
    new_titles = [a["title"] for a in res1["new_articles"]]
    assert any("Quy hoạch" in t for t in new_titles)

    # --- Run 2: Crawl Source ID 2 again (Exact same source & content) ---
    # MUST DEDUPLICATE: 0 new articles, duplicate_count > 0!
    res2 = await crawl_source_and_save(source_id=2, db=None)
    assert res2["ok"] is True
    assert res2["new_count"] == 0, "Duplicate articles should NOT be saved again!"
    assert res2["duplicate_count"] == 2, "All previously crawled articles must be detected as duplicates"
    assert "không lưu thêm bài trùng" in res2["message"]

    articles_after_run2 = await article_services.list_articles(db=None, page=1, page_size=100)
    count_after_run2 = articles_after_run2["total"]
    assert count_after_run2 == count_after_run1, "Total articles count in DB must NOT increase on duplicate crawl!"


def test_http_scan_api_and_scan_all(client):
    """Verify HTTP API for single source scan and bulk scan-all with deduplication."""
    # 1. First scan
    resp1 = client.post("/api/sources/2/scan")
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["ok"] is True
    assert d1["scanned_count"] > 0

    # 2. Immediate second scan of source 2 -> new_count must be 0
    resp2 = client.post("/api/sources/2/scan")
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["ok"] is True
    assert d2["new_count"] == 0
    assert d2["duplicate_count"] > 0

    # 3. Bulk scan all active sources
    resp_all = client.post("/api/sources/scan-all")
    assert resp_all.status_code == 200
    d_all = resp_all.json()
    assert d_all["ok"] is True
    assert d_all["sources_count"] >= 1
    assert "total_scanned" in d_all
    assert "total_duplicates" in d_all


def test_extract_articles_from_website_html():
    """Verify HTML parser extracts article list from headlines, cards, and relative URLs."""
    from app.sources.crawler import extract_articles_from_html

    sample_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Chuyên trang Kinh Tế Đô Thị</title></head>
    <body>
        <div class="header-nav">
            <a href="/">Trang chủ</a>
            <a href="/category/kinh-doanh">Kinh doanh</a>
            <a href="/lien-he">Liên hệ</a>
            <a href="/login">Đăng nhập</a>
        </div>
        <main>
            <!-- Article 1: Heading with link -->
            <article class="item-news">
                <h2 class="title-news">
                    <a href="/tin-tuc/bat-dong-san-thu-do-tang-truong-2026.html" title="Thị trường bất động sản thủ đô bứt phá năm 2026">
                        Thị trường bất động sản thủ đô bứt phá năm 2026
                    </a>
                </h2>
                <p class="description">Dòng tiền đầu tư đang chảy mạnh vào các dự án căn hộ và đất nền vùng ven...</p>
            </article>

            <!-- Article 2: Card container -->
            <div class="story-item">
                <h3 class="story-title">
                    <a href="/tin-tuc/cong-nghe-ai-agent-doanh-nghiep.html">
                        Ứng dụng AI Agent tự động hóa vận hành doanh nghiệp vừa và nhỏ
                    </a>
                </h3>
                <div class="lead">Nhiều công ty đã cắt giảm 50% chi phí chăm sóc khách hàng nhờ áp dụng Agent AI.</div>
            </div>

            <!-- Article 3: Relative path article -->
            <div class="post-card">
                <h4>
                    <a href="chung-khoan-khoi-ngoai-mua-rong.html">
                        Thị trường chứng khoán: Khối ngoại mua ròng kỷ lục phiên đầu tuần
                    </a>
                </h4>
                <p class="summary">Giá trị mua ròng toàn sàn vượt mức 1.500 tỷ đồng tập trung nhóm ngân hàng...</p>
            </div>
        </main>
    </body>
    </html>
    """
    extracted = extract_articles_from_html(sample_html, base_url="https://kinhte.vn/tin-tuc", limit=10)

    assert len(extracted) == 3
    assert extracted[0]["title"] == "Thị trường bất động sản thủ đô bứt phá năm 2026"
    assert extracted[0]["url"] == "https://kinhte.vn/tin-tuc/bat-dong-san-thu-do-tang-truong-2026.html"
    assert "Dòng tiền đầu tư" in extracted[0]["summary"]
    assert extracted[0]["category"] == "Bất động sản"

    assert extracted[1]["title"] == "Ứng dụng AI Agent tự động hóa vận hành doanh nghiệp vừa và nhỏ"
    assert extracted[1]["category"] == "Công nghệ"

    assert extracted[2]["title"] == "Thị trường chứng khoán: Khối ngoại mua ròng kỷ lục phiên đầu tuần"
    assert extracted[2]["category"] == "Tài chính & Đầu tư"


