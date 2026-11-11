"""Tests for AI Content Ideas Management (Kho Ý Tưởng AI từ Database).

Covers:
1. Idea model validation, status metadata, recommended formats.
2. Default seed data coverage in MongoDB / in-memory fallback.
3. CRUD operations, assign product, workflow status transition, generate from article.
4. Pagination: services pagination & HTML UI pagination controls.
5. HTTP Endpoints (/ideas, /tools/content-ideas/ideas, /api/ideas).
"""
import pytest
from fastapi.testclient import TestClient

from app.ideas.models import (
    IDEA_STATUS_METADATA,
    RECOMMENDED_FORMATS,
    AIIdeaModel,
)
from app.ideas import services
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_idea_metadata():
    """Verify status metadata and format options definitions."""
    assert "ready" in IDEA_STATUS_METADATA
    assert "drafting" in IDEA_STATUS_METADATA
    assert "reviewing" in IDEA_STATUS_METADATA
    assert "published" in IDEA_STATUS_METADATA
    assert "archived" in IDEA_STATUS_METADATA

    format_vals = [f["value"] for f in RECOMMENDED_FORMATS]
    assert any("Blog" in v for v in format_vals)
    assert any("TikTok" in v for v in format_vals)
    assert any("Carousel" in v for v in format_vals)


@pytest.mark.anyio
async def test_list_ideas_and_seed_coverage():
    """Verify list_ideas returns default seed data with >= 8 items."""
    await services.reset_demo_ideas(db=None)
    data = await services.list_ideas(db=None, page=1, page_size=20)
    assert data["total"] >= 8
    assert len(data["items"]) >= 8

    titles = [i["title"] for i in data["items"]]
    assert any("SMB" in t for t in titles)
    assert any("Carousel" in t for t in titles)
    assert any("Livestream AI" in t for t in titles)


@pytest.mark.anyio
async def test_create_idea_full_fields():
    """Verify creating a new AI Idea with full metadata."""
    await services.reset_demo_ideas(db=None)
    new_data = {
        "title": "5 bước bảo mật dữ liệu doanh nghiệp khi dùng AI cục bộ",
        "angle": "Cảnh báo rủi ro an ninh mạng và giải pháp phần cứng an toàn",
        "target_audience": "Giám đốc CNTT, Chủ doanh nghiệp SMB, Lập trình viên",
        "recommended_format": "Bài viết dài (Blog / Website)",
        "viral_score": 93,
        "status": "ready",
        "keywords": ["An ninh mạng", "Local AI", "Bảo mật", "SMB"],
        "outline": "1. Mở đầu\n2. 5 lỗ hổng thường gặp\n3. Biện pháp cô lập mạng\n4. Kết luận",
        "target_product_id": 3,
        "target_product_name": "Web Blog Công Nghệ AI & Tự Động Hóa",
        "notes": "Ưu tiên viết trong tuần này",
    }

    created = await services.create_idea(new_data, db=None)
    assert created["id"] > 0
    assert "5 bước" in created["title"]
    assert created["viral_score"] == 93
    assert created["status"] == "ready"
    assert created["target_product_id"] == 3
    assert "An ninh mạng" in created["keywords"]


@pytest.mark.anyio
async def test_update_and_assign_product():
    """Verify updating idea fields and assigning target product/channel."""
    await services.reset_demo_ideas(db=None)
    created = await services.create_idea(
        {
            "title": "Ý tưởng test chỉnh sửa",
            "angle": "Góc nhìn test",
            "status": "ready",
        },
        db=None,
    )
    idea_id = created["id"]

    # 1. Update fields
    updated = await services.update_idea(
        idea_id,
        {
            "viral_score": 97,
            "angle": "Góc nhìn chuyên sâu cập nhật",
            "status": "drafting",
        },
        db=None,
    )
    assert updated is not None
    assert updated["viral_score"] == 97
    assert updated["angle"] == "Góc nhìn chuyên sâu cập nhật"
    assert updated["status"] == "drafting"

    # 2. Assign product
    assigned = await services.assign_product_to_idea(
        idea_id=idea_id,
        product_id=2,
        product_name="TikTok GenZ Đầu Tư & Tài Chính Cá Nhân",
        platform="tiktok",
        db=None,
    )
    assert assigned is not None
    assert assigned["target_product_id"] == 2
    assert "TikTok GenZ" in assigned["target_product_name"]
    assert assigned["target_platform"] == "tiktok"


@pytest.mark.anyio
async def test_workflow_status_transitions():
    """Verify transitioning status (ready -> drafting -> reviewing -> published)."""
    await services.reset_demo_ideas(db=None)
    created = await services.create_idea(
        {"title": "Test Workflow Transitions", "status": "ready"},
        db=None,
    )
    idea_id = created["id"]

    # Step 1: Draft
    s1 = await services.update_idea_status(idea_id, "drafting", db=None)
    assert s1["status"] == "drafting"

    # Step 2: Review
    s2 = await services.update_idea_status(idea_id, "reviewing", db=None)
    assert s2["status"] == "reviewing"

    # Step 3: Publish
    s3 = await services.update_idea_status(idea_id, "published", db=None)
    assert s3["status"] == "published"


@pytest.mark.anyio
async def test_filter_ideas():
    """Verify filtering ideas by status, format, search keyword, and target product."""
    await services.reset_demo_ideas(db=None)

    # Filter status = ready
    res_ready = await services.list_ideas(db=None, status_filter="ready")
    assert all(i["status"] == "ready" for i in res_ready["items"])

    # Filter format = Video ngắn
    res_format = await services.list_ideas(db=None, format_filter="Video ngắn (TikTok / Shorts / Reels)")
    assert all("Video ngắn" in i["recommended_format"] for i in res_format["items"])

    # Search keyword
    res_search = await services.list_ideas(db=None, search="SMB")
    assert len(res_search["items"]) >= 1
    assert any("smb" in i["title"].lower() or "smb" in i["angle"].lower() for i in res_search["items"])


@pytest.mark.anyio
async def test_ideas_pagination_services():
    """Verify pagination slicing and metadata for AI ideas."""
    await services.reset_demo_ideas(db=None)

    # Page 1 with size 6
    p1 = await services.list_ideas(db=None, page=1, page_size=6)
    assert len(p1["items"]) == 6
    assert p1["pagination"].page == 1
    assert p1["pagination"].total_pages >= 2
    assert p1["pagination"].has_next is True
    assert p1["pagination"].start_index == 1
    assert p1["pagination"].end_index == 6

    # Page 2 with size 6
    p2 = await services.list_ideas(db=None, page=2, page_size=6)
    assert len(p2["items"]) >= 2
    assert p2["pagination"].page == 2
    assert p2["pagination"].has_prev is True
    assert p2["pagination"].start_index == 7


def test_http_ideas_pages_and_pagination_ui(client):
    """Verify HTML UI rendering of AI Ideas screen with database integration and pagination."""
    # Check /ideas
    resp1 = client.get("/ideas")
    assert resp1.status_code == 200
    assert "Kho Ý Tưởng Nội Dung Đã Trích Xuất" in resp1.text
    assert "MongoDB: ai_ideas" in resp1.text or "Chế độ Demo" in resp1.text
    # Pagination bar is rendered
    assert "Hiển thị" in resp1.text
    assert "bản ghi" in resp1.text
    assert "pagination-page-size" in resp1.text

    # Check /tools/content-ideas/ideas
    resp2 = client.get("/tools/content-ideas/ideas")
    assert resp2.status_code == 200
    assert "Kho Ý Tưởng Nội Dung Đã Trích Xuất" in resp2.text

    # Check page 2 query
    resp_p2 = client.get("/tools/content-ideas/ideas?page=2&page_size=6")
    assert resp_p2.status_code == 200
    assert "Trước" in resp_p2.text


def test_http_ideas_api_crud(client):
    """Verify REST API endpoints for AI ideas CRUD, assign product, status, and deletion."""
    # 1. List API
    res_list = client.get("/api/ideas")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data
    assert data["total"] >= 8

    # 2. Get single API
    res_get = client.get("/api/ideas/1")
    assert res_get.status_code == 200
    assert res_get.json()["ok"] is True
    assert res_get.json()["idea"]["id"] == 1

    # 3. Create Idea via POST
    res_create = client.post(
        "/api/ideas",
        data={
            "title": "Bí quyết ứng dụng AI phân tích tài chính cá nhân",
            "angle": "Chiến lược phân bổ danh mục đầu tư an toàn",
            "target_audience": "Gen Z đi làm 1-3 năm",
            "recommended_format": "Video ngắn (TikTok / Shorts / Reels)",
            "viral_score": 90,
            "status": "ready",
            "keywords": "AI Tài chính, GenZ, Tiết kiệm",
            "outline": "1. Thực trạng tiêu xài\n2. AI theo dõi chi tiêu\n3. Lời khuyên",
        },
        headers={"Accept": "application/json"},
    )
    assert res_create.status_code == 200
    created_id = res_create.json()["idea"]["id"]

    # 4. Edit Idea
    res_edit = client.post(
        f"/api/ideas/{created_id}/edit",
        data={"viral_score": 95, "angle": "Góc nhìn cập nhật qua API"},
        headers={"Accept": "application/json"},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["idea"]["viral_score"] == 95

    # 5. Assign Product
    res_assign = client.post(
        f"/api/ideas/{created_id}/assign-product",
        data={"product_id": 2, "product_name": "TikTok GenZ Đầu Tư & Tài Chính Cá Nhân"},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["ok"] is True

    # 6. Status change
    res_status = client.post(
        f"/api/ideas/{created_id}/status",
        data={"status": "drafting"},
    )
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "drafting"

    # 7. Delete Idea
    res_del = client.post(
        f"/api/ideas/{created_id}/delete",
        headers={"Accept": "application/json"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["ok"] is True

    # 8. Generate idea from crawled article
    res_gen = client.post("/api/ideas/generate-from-article/1")
    assert res_gen.status_code == 200
    assert res_gen.json()["ok"] is True
    assert "idea" in res_gen.json()
    assert res_gen.json()["idea"]["source_article_id"] == 1
