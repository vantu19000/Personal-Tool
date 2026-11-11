"""Tests for Crawled Articles Management (Kho Bài Viết Thu Thập từ DB).

Covers:
1. Article model validation, sentiment metadata, status metadata.
2. Default seed data coverage in MongoDB / in-memory fallback.
3. CRUD operations, assign product, generate idea mark, reset demo.
4. HTTP Endpoints (/articles, /tools/content-ideas/articles, /api/articles).
"""
import pytest
from fastapi.testclient import TestClient

from app.articles.models import (
    ARTICLE_STATUS_METADATA,
    SENTIMENT_METADATA,
    CrawledArticleModel,
)
from app.articles import services
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_article_metadata():
    """Verify sentiment and status definitions."""
    assert "Tích cực" in SENTIMENT_METADATA
    assert "Sôi nổi" in SENTIMENT_METADATA
    assert "Cảnh báo" in SENTIMENT_METADATA
    assert "new" in ARTICLE_STATUS_METADATA
    assert "has_idea" in ARTICLE_STATUS_METADATA


@pytest.mark.anyio
async def test_list_articles_and_seed_coverage():
    """Verify list_articles returns items from DB with default seed data."""
    await services.reset_demo_articles(db=None)
    data = await services.list_articles(db=None, page=1, page_size=20)
    assert data["total"] >= 9
    assert len(data["items"]) >= 9

    sources_in_db = {a["source"] for a in data["items"]}
    assert any("VnExpress" in s for s in sources_in_db)
    assert any("Tuổi Trẻ" in s for s in sources_in_db)
    assert any("TikTok" in s for s in sources_in_db)


@pytest.mark.anyio
async def test_create_article_full_fields():
    """Verify creating a crawled article in database with full fields."""
    await services.reset_demo_articles(db=None)
    new_data = {
        "title": "Hạ tầng giao thông kết nối sân bay Long Thành: Động lực bứt phá vùng kinh tế trọng điểm phía Nam",
        "summary": "Hàng loạt tuyến cao tốc và đường vành đai đang được gấp rút thi công để hoàn thành đồng bộ trước ngày sân bay quốc tế Long Thành vận hành thương mại...",
        "content": "Toàn văn bài phân tích chi tiết tiến độ thi công cao tốc Biên Hòa - Vũng Tàu, đường Vành Đai 3 TP.HCM...",
        "url": "https://baogiaothong.vn/ha-tang-long-thanh-2026",
        "source": "Báo Giao Thông",
        "source_type": "website",
        "location": "Đồng Nai",
        "category": "Hạ tầng & Đô thị",
        "tags": "Sân bay Long Thành, Cao tốc, Hạ tầng, BĐS Đồng Nai",
        "sentiment": "Tích cực",
        "viral_potential": 90,
        "target_product_id": 1,
        "target_product_name": "Kênh YouTube BĐS & Quy Hoạch Thủ Đô",
        "status": "new",
    }

    created = await services.create_article(new_data, db=None)
    assert created["id"] > 0
    assert "Long Thành" in created["title"]
    assert created["location"] == "Đồng Nai"
    assert created["category"] == "Hạ tầng & Đô thị"
    assert created["viral_potential"] == 90
    assert created["target_product_id"] == 1
    assert "Cao tốc" in created["tags"]


@pytest.mark.anyio
async def test_update_and_assign_product():
    """Verify updating article and assigning to a target product."""
    await services.reset_demo_articles(db=None)
    created = await services.create_article(
        {
            "title": "Bài viết test cập nhật",
            "summary": "Tóm tắt test",
            "source": "Báo Mới",
        },
        db=None,
    )
    art_id = created["id"]

    # 1. Update article
    updated = await services.update_article(
        art_id,
        {
            "sentiment": "Sôi nổi",
            "viral_potential": 95,
        },
        db=None,
    )
    assert updated is not None
    assert updated["sentiment"] == "Sôi nổi"
    assert updated["viral_potential"] == 95

    # 2. Assign target product
    assigned = await services.assign_product_to_article(
        article_id=art_id,
        product_id=2,
        product_name="TikTok GenZ Đầu Tư & Tài Chính Cá Nhân",
        db=None,
    )
    assert assigned is not None
    assert assigned["target_product_id"] == 2
    assert "TikTok GenZ" in assigned["target_product_name"]


@pytest.mark.anyio
async def test_mark_as_has_idea():
    """Verify marking article as having generated AI idea."""
    await services.reset_demo_articles(db=None)
    created = await services.create_article(
        {"title": "Test AI Idea Trigger", "summary": "Tóm tắt", "status": "new"},
        db=None,
    )
    art_id = created["id"]

    marked = await services.mark_as_has_idea(art_id, db=None)
    assert marked["has_ai_idea"] is True
    assert marked["status"] == "has_idea"


@pytest.mark.anyio
async def test_filter_articles():
    """Verify filtering articles by category, location, and sentiment."""
    await services.reset_demo_articles(db=None)

    # Filter category = Bất động sản
    res_bds = await services.list_articles(db=None, category_filter="Bất động sản")
    assert all("Bất động sản" in a["category"] for a in res_bds["items"])

    # Filter sentiment = Cảnh báo
    res_sent = await services.list_articles(db=None, sentiment_filter="Cảnh báo")
    assert all(a["sentiment"] == "Cảnh báo" for a in res_sent["items"])

    # Search keyword
    res_search = await services.list_articles(db=None, search="AI Agent")
    assert len(res_search["items"]) >= 1
    assert any("ai agent" in a["title"].lower() or "ai agent" in a["summary"].lower() for a in res_search["items"])


def test_http_articles_pages(client):
    """Verify HTML UI rendering of Crawled Articles screen from database."""
    # Check /articles with page_size=20 so all articles are present
    resp1 = client.get("/articles?page_size=20")
    assert resp1.status_code == 200
    assert "Kho Dữ Liệu Bài Viết Đã Thu Thập" in resp1.text
    assert "AI Agent" in resp1.text
    assert "Bảng giá đất" in resp1.text

    # Check /tools/content-ideas/articles
    resp2 = client.get("/tools/content-ideas/articles")
    assert resp2.status_code == 200
    assert "Kho Dữ Liệu Bài Viết Đã Thu Thập" in resp2.text


def test_http_articles_api_crud(client):
    """Verify API endpoints for articles CRUD, assign product, and generate idea."""
    # 1. List API
    res_list = client.get("/api/articles")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data
    assert data["total"] >= 9

    # 2. Get single API
    res_get = client.get("/api/articles/1")
    assert res_get.status_code == 200
    assert res_get.json()["ok"] is True
    assert res_get.json()["article"]["id"] == 1

    # 3. Create Article via POST
    res_create = client.post(
        "/api/articles",
        data={
            "title": "Mô hình kinh tế số và thuế thương mại điện tử năm 2026",
            "summary": "Tổng cục Thuế triển khai cổng thông tin tự động kết nối dữ liệu sàn TMĐT...",
            "content": "Nội dung chi tiết quy định kê khai thuế cho nhà bán hàng cá nhân...",
            "source": "Báo Đầu Tư",
            "source_type": "website",
            "location": "Hà Nội",
            "category": "Tài chính & Thuế",
            "tags": "Thuế TMĐT, Kinh tế số, Sàn thương mại",
            "sentiment": "Tích cực",
            "viral_potential": 88,
        },
        headers={"Accept": "application/json"},
    )
    assert res_create.status_code == 200
    created_id = res_create.json()["article"]["id"]

    # 4. Edit Article
    res_edit = client.post(
        f"/api/articles/{created_id}/edit",
        data={"viral_potential": 96, "sentiment": "Sôi nổi"},
        headers={"Accept": "application/json"},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["article"]["viral_potential"] == 96

    # 5. Assign Product
    res_assign = client.post(
        f"/api/articles/{created_id}/assign-product",
        data={"product_id": 3, "product_name": "Web Blog Công Nghệ AI"},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["ok"] is True

    # 6. Generate Idea mark
    res_idea = client.post(f"/api/articles/{created_id}/generate-idea")
    assert res_idea.status_code == 200
    assert res_idea.json()["ok"] is True

    # 7. Delete Article
    res_del = client.post(
        f"/api/articles/{created_id}/delete",
        headers={"Accept": "application/json"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["ok"] is True


@pytest.mark.anyio
async def test_articles_pagination_services():
    """Verify services.list_articles correctly slices items and provides pagination metadata."""
    await services.reset_demo_articles(db=None)

    # Page 1 with size 6
    p1 = await services.list_articles(db=None, page=1, page_size=6)
    assert len(p1["items"]) == 6
    assert p1["pagination"].page == 1
    assert p1["pagination"].total_pages >= 2
    assert p1["pagination"].has_next is True
    assert p1["pagination"].has_prev is False
    assert p1["pagination"].start_index == 1
    assert p1["pagination"].end_index == 6

    # Page 2 with size 6
    p2 = await services.list_articles(db=None, page=2, page_size=6)
    assert len(p2["items"]) >= 3
    assert p2["pagination"].page == 2
    assert p2["pagination"].has_prev is True
    assert p2["pagination"].start_index == 7


def test_articles_pagination_ui(client):
    """Verify HTML rendered page includes pagination controls and options."""
    resp = client.get("/articles")
    assert resp.status_code == 200
    # Pagination bar is rendered
    assert "Hiển thị" in resp.text
    assert "bản ghi" in resp.text
    assert "Cỡ trang:" in resp.text
    assert "pagination-page-size" in resp.text

    # Page 2 query
    resp_p2 = client.get("/articles?page=2&page_size=6")
    assert resp_p2.status_code == 200
    assert "Trước" in resp_p2.text

