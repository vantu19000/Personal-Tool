"""Tests for My Products & Publishing Channels Management (Quản lý Sản phẩm / Kênh của tôi).

Covers:
1. All Supported Platforms (YouTube, TikTok, Web Blog, Facebook, Instagram, Pinterest, Threads, X/Twitter, LinkedIn, Podcast, Other).
2. Product & Channel fields: Tên, Nền tảng, URL/Handle, Ngách nội dung, Đối tượng mục tiêu, Định dạng, Tần suất, Tone giọng, AI Prompt riêng.
3. CRUD operations, Toggle Status, Reset Demo.
4. HTTP Endpoints (/products, /tools/content-ideas/products, /api/products).
"""
import pytest
from fastapi.testclient import TestClient

from app.products.models import (
    PLATFORM_METADATA,
    PRODUCT_STATUS_METADATA,
    ProductModel,
)
from app.products import services
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_platform_metadata():
    """Verify that all key publishing platforms are defined with icons and labels."""
    expected = [
        "youtube",
        "tiktok",
        "web_blog",
        "facebook",
        "instagram",
        "pinterest",
        "threads",
        "twitter_x",
        "linkedin",
        "podcast",
    ]
    for plat in expected:
        assert plat in PLATFORM_METADATA, f"Missing platform: {plat}"
        meta = PLATFORM_METADATA[plat]
        assert "label" in meta
        assert "icon" in meta
        assert "badge_color" in meta
        assert "default_format" in meta


def test_product_statuses():
    """Verify product status definitions."""
    assert "active" in PRODUCT_STATUS_METADATA
    assert "paused" in PRODUCT_STATUS_METADATA
    assert "planning" in PRODUCT_STATUS_METADATA


@pytest.mark.anyio
async def test_list_products_and_seed_coverage():
    """Verify list_products returns default seed covering YouTube, TikTok, Web Blog, Facebook, Instagram, Pinterest."""
    await services.reset_demo_products(db=None)
    data = await services.list_products(db=None, page=1, page_size=20)
    assert data["total"] >= 6
    assert len(data["items"]) >= 6

    platforms_in_db = {p["platform"] for p in data["items"]}
    for expected in ["youtube", "tiktok", "web_blog", "facebook", "instagram", "pinterest"]:
        assert expected in platforms_in_db, f"Default seed missing platform: {expected}"


@pytest.mark.anyio
async def test_create_product_full_fields():
    """Verify creating a product with all custom fields and AI Prompt."""
    await services.reset_demo_products(db=None)
    new_data = {
        "name": "Kênh TikTok Review Đồ Gia Dụng Thông Minh",
        "platform": "tiktok",
        "code": "tiktok-giadung-smart",
        "url": "https://tiktok.com/@giadung_smart",
        "niche": "Gia dụng & Thiết bị tiện ích",
        "target_audience": "Gia đình trẻ, người độc thân thích sống gọn gàng (22-40 tuổi)",
        "content_format": "Video trải nghiệm thực tế 45s, quay cận cảnh công năng",
        "posting_frequency": "2 video/ngày",
        "brand_voice": "Chân thật, không quảng cáo lố, nói rõ ưu nhược điểm",
        "ai_system_prompt": "Kịch bản video TikTok dạng bóc phốt hoặc giải quyết vấn đề khó chịu trong nhà bếp. Câu mở đầu: 'Đừng mua món này nếu bạn chưa biết...'",
        "tags": "TikTok, Gia dụng, Review, Smart Home",
        "status": "active",
        "followers_metric": "65.8K Followers",
        "description": "Kênh liên kết affiliate và bán sản phẩm tiện ích thông minh.",
    }

    created = await services.create_product(new_data, db=None)
    assert created["id"] > 0
    assert created["name"] == "Kênh TikTok Review Đồ Gia Dụng Thông Minh"
    assert created["platform"] == "tiktok"
    assert created["code"] == "tiktok-giadung-smart"
    assert created["niche"] == "Gia dụng & Thiết bị tiện ích"
    assert "Đừng mua món này" in created["ai_system_prompt"]
    assert "Gia dụng" in created["tags"]
    assert created["status"] == "active"


@pytest.mark.anyio
async def test_update_product():
    """Verify updating a product's AI prompt, posting frequency, and status."""
    await services.reset_demo_products(db=None)
    created = await services.create_product(
        {
            "name": "Kênh Pinterest Mẫu Nhà Cấp 4",
            "platform": "pinterest",
            "niche": "Nhà cấp 4 đẹp",
            "status": "planning",
            "ai_system_prompt": "Prompt ban đầu",
        },
        db=None,
    )
    pid = created["id"]

    updated = await services.update_product(
        pid,
        {
            "status": "active",
            "posting_frequency": "5 pins/ngày",
            "ai_system_prompt": "Prompt cập nhật: Tạo mô tả Pin chuẩn SEO Pinterest chứa từ khóa giá rẻ và bản vẽ mặt bằng.",
        },
        db=None,
    )
    assert updated is not None
    assert updated["status"] == "active"
    assert updated["posting_frequency"] == "5 pins/ngày"
    assert "chuẩn SEO Pinterest" in updated["ai_system_prompt"]


@pytest.mark.anyio
async def test_toggle_product_status():
    """Verify toggling product status between active and paused."""
    await services.reset_demo_products(db=None)
    created = await services.create_product(
        {"name": "Podcast Góc Nhìn Cuộc Sống", "platform": "podcast", "status": "active"},
        db=None,
    )
    pid = created["id"]

    toggled = await services.toggle_product_status(pid, db=None)
    assert toggled["status"] == "paused"

    toggled2 = await services.toggle_product_status(pid, db=None)
    assert toggled2["status"] == "active"


@pytest.mark.anyio
async def test_filter_products_by_platform_and_search():
    """Verify filtering products by platform and search keywords."""
    await services.reset_demo_products(db=None)

    # Filter platform = youtube
    res_yt = await services.list_products(db=None, platform_filter="youtube")
    assert all(p["platform"] == "youtube" for p in res_yt["items"])

    # Search keyword
    res_search = await services.list_products(db=None, search="TikTok")
    assert len(res_search["items"]) >= 1
    assert any("tiktok" in p["name"].lower() or "tiktok" in p["platform"].lower() for p in res_search["items"])


def test_http_products_pages(client):
    """Verify HTML UI rendering of My Products screen."""
    # Check /products
    resp1 = client.get("/products")
    assert resp1.status_code == 200
    assert "Quản lý Sản phẩm & Kênh của Tôi" in resp1.text
    assert "YouTube" in resp1.text
    assert "TikTok" in resp1.text
    assert "Web Blog" in resp1.text
    assert "Instagram" in resp1.text
    assert "Pinterest" in resp1.text
    assert "AI Prompt riêng" in resp1.text

    # Check /tools/content-ideas/products
    resp2 = client.get("/tools/content-ideas/products")
    assert resp2.status_code == 200
    assert "AI Content Ideas" in resp2.text


def test_http_products_api_crud(client):
    """Verify API endpoints for products CRUD and toggling."""
    # 1. List API
    res_list = client.get("/api/products")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data
    assert data["total"] >= 6

    # 2. Get single API
    res_get = client.get("/api/products/1")
    assert res_get.status_code == 200
    assert res_get.json()["ok"] is True
    assert res_get.json()["product"]["id"] == 1

    # 3. Create Product via POST
    res_create = client.post(
        "/api/products",
        data={
            "name": "Kênh Threads Đời Sống Văn Phòng",
            "platform": "threads",
            "code": "threads-office-life",
            "url": "https://threads.net/@office_life",
            "niche": "Đời sống công sở & Drama văn phòng",
            "target_audience": "Dân văn phòng 22-35 tuổi",
            "content_format": "Chuỗi Thread ngắn 3-5 post",
            "brand_voice": "Châm biếm hài hước nhẹ nhàng",
            "ai_system_prompt": "Viết thread ngắn nói lên nỗi lòng dân văn phòng ngày thứ Hai.",
            "status": "active",
        },
        headers={"Accept": "application/json"},
    )
    assert res_create.status_code == 200
    created_id = res_create.json()["product"]["id"]

    # 4. Edit Product
    res_edit = client.post(
        f"/api/products/{created_id}/edit",
        data={"posting_frequency": "3 post/ngày", "brand_voice": "Hài hước tích cực"},
        headers={"Accept": "application/json"},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["product"]["posting_frequency"] == "3 post/ngày"

    # 5. Toggle Status
    res_toggle = client.post(f"/api/products/{created_id}/toggle-status")
    assert res_toggle.status_code == 200
    assert res_toggle.json()["product"]["status"] == "paused"

    # 6. Delete Product
    res_del = client.post(
        f"/api/products/{created_id}/delete",
        headers={"Accept": "application/json"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["ok"] is True
