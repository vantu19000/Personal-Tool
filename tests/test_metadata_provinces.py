"""Tests for Metadata Province / City management module (MongoDB & in-memory fallback)."""
import pytest
from fastapi.testclient import TestClient

from app.metadata import services
from app.metadata.models import ProvinceModel
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_province_model_validation():
    p = ProvinceModel(
        id=1,
        name="TP. Hà Nội",
        code="01",
        type="Thành phố Trung ương",
        region="Miền Bắc",
        country_code="VN",
        phone_code="024",
        postal_code="100000",
        status="active",
    )
    assert p.id == 1
    assert p.name == "TP. Hà Nội"
    assert p.code == "01"
    assert p.region == "Miền Bắc"
    assert p.country_code == "VN"
    assert p.status == "active"
    d = p.to_dict()
    assert d["code"] == "01"


def test_load_vn_provinces_json():
    provinces = services.load_vn_provinces_json()
    assert isinstance(provinces, list)
    assert len(provinces) == 34

    # Check key centrally-governed cities and provinces according to official administrative dataset
    names = [p["name"] for p in provinces]
    assert "Hà Nội" in names or "TP. Hà Nội" in names
    assert "Hải Phòng" in names or "TP. Hải Phòng" in names
    assert "Huế" in names or "TP. Huế" in names
    assert "Đà Nẵng" in names or "TP. Đà Nẵng" in names
    assert "Hồ Chí Minh" in names or "TP. Hồ Chí Minh" in names
    assert "Cần Thơ" in names or "TP. Cần Thơ" in names
    assert "Bắc Ninh" in names or "Tỉnh Bắc Ninh" in names
    assert "Đồng Nai" in names or "Tỉnh Đồng Nai" in names


@pytest.mark.anyio
async def test_province_service_crud():
    # 1. Create a test province
    new_data = {
        "name": "Test Province",
        "code": "TP99",
        "type": "Tỉnh",
        "region": "Miền Bắc",
        "country_code": "VN",
        "phone_code": "0200",
        "postal_code": "999999",
        "status": "active",
    }
    created = await services.create_province(db=None, data=new_data)
    assert created is not None
    prov_id = created["id"]
    assert created["name"] == "Test Province"
    assert created["code"] == "TP99"

    # 2. List provinces and find created one
    res = await services.list_provinces(db=None, search="Test Province")
    items = res["items"]
    found = any(p["id"] == prov_id for p in items)
    assert found is True

    # 3. Update province
    updated = await services.update_province(
        db=None,
        province_id=prov_id,
        data={"name": "Updated Test Province", "status": "inactive"},
    )
    assert updated is not None
    assert updated["name"] == "Updated Test Province"
    assert updated["status"] == "inactive"

    # 4. Delete province
    deleted = await services.delete_province(db=None, province_id=prov_id)
    assert deleted is True


def test_provinces_page_render(client):
    response = client.get("/metadata/provinces")
    assert response.status_code == 200
    assert "Quản lý Tỉnh / Thành phố" in response.text
    assert ("Bộ nhớ Cục bộ" in response.text) or ("metadata_provinces" in response.text)
    assert "34 Tỉnh/Thành" in response.text


def test_api_list_provinces(client):
    response = client.get("/metadata/api/provinces?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "active_count" in data
    assert "pagination" in data
    assert len(data["items"]) <= 10


def test_api_create_and_delete_province(client):
    # Create
    create_res = client.post(
        "/metadata/api/provinces",
        data={
            "name": "Thành phố Mẫu",
            "code": "TPM",
            "type": "Thành phố",
            "region": "Miền Nam",
            "country_code": "VN",
            "phone_code": "0299",
            "postal_code": "777777",
            "status": "active",
        },
        headers={"Accept": "application/json"},
    )
    assert create_res.status_code == 200
    create_json = create_res.json()
    assert create_json.get("ok") is True
    prov_id = create_json["province"]["id"]

    # Edit
    edit_res = client.post(
        f"/metadata/api/provinces/{prov_id}/edit",
        data={
            "name": "Thành phố Mẫu Đã Đổi Tên",
            "status": "inactive",
        },
        headers={"Accept": "application/json"},
    )
    assert edit_res.status_code == 200
    edit_json = edit_res.json()
    assert edit_json.get("ok") is True
    assert edit_json["province"]["name"] == "Thành phố Mẫu Đã Đổi Tên"
    assert edit_json["province"]["status"] == "inactive"

    # Delete
    del_res = client.post(
        f"/metadata/api/provinces/{prov_id}/delete",
        headers={"Accept": "application/json"},
    )
    assert del_res.status_code == 200
    assert del_res.json().get("ok") is True


def test_api_import_vn_provinces(client):
    response = client.post(
        "/metadata/api/provinces/import-vn",
        data={"overwrite": "true", "reset": "true"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("ok") is True
    assert data.get("total_provinces") == 34
