"""Tests for Ward / Commune metadata management module (MongoDB & in-memory fallback)."""
import pytest
from fastapi.testclient import TestClient

from app.metadata import services
from app.metadata.models import WardModel
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ward_model_validation():
    w = WardModel(
        id=1,
        code="00001",
        name="Phường Phúc Xá",
        type="Phường",
        province_name="Thành phố Hà Nội",
        district_name="Quận Ba Đình",
        merged_note="Đơn vị hành chính cấp xã chuẩn hóa",
        status="active",
    )
    assert w.id == 1
    assert w.name == "Phường Phúc Xá"
    assert w.code == "00001"
    assert w.type == "Phường"
    assert w.province_name == "Thành phố Hà Nội"
    assert w.district_name == "Quận Ba Đình"
    d = w.to_dict()
    assert d["code"] == "00001"


def test_load_vn_wards_json():
    wards = services.load_vn_wards_json(limit=50)
    assert isinstance(wards, list)
    assert len(wards) == 50
    assert "name" in wards[0]
    assert "code" in wards[0]
    assert "province_name" in wards[0]


@pytest.mark.anyio
async def test_ward_service_crud():
    # 1. Create a test ward
    new_data = {
        "name": "Phường Mẫu Thử Nghiệm",
        "code": "TEST999",
        "type": "Phường",
        "province_name": "Thành phố Hà Nội",
        "district_name": "Quận Ba Đình",
        "merged_note": "Sáp nhập thử nghiệm",
        "status": "active",
    }
    created = await services.create_ward(db=None, data=new_data)
    assert created is not None
    ward_id = created["id"]
    assert created["name"] == "Phường Mẫu Thử Nghiệm"

    # 2. List wards and find created one
    res = await services.list_wards(db=None, search="Mẫu Thử Nghiệm")
    items = res["items"]
    found = any(w["id"] == ward_id for w in items)
    assert found is True

    # 3. Update ward
    updated = await services.update_ward(
        db=None,
        ward_id=ward_id,
        data={"name": "Phường Đã Cập Nhật", "status": "inactive"},
    )
    assert updated is not None
    assert updated["name"] == "Phường Đã Cập Nhật"
    assert updated["status"] == "inactive"

    # 4. Delete ward
    deleted = await services.delete_ward(db=None, ward_id=ward_id)
    assert deleted is True


def test_wards_page_render(client):
    response = client.get("/metadata/wards")
    assert response.status_code == 200
    assert "Quản lý Xã / Phường" in response.text
    assert ("Bộ nhớ Cục bộ" in response.text) or ("MongoDB Connected" in response.text)
    assert "Tải từ mạng" in response.text


def test_api_list_wards(client):
    response = client.get("/metadata/api/wards?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "active_count" in data
    assert "pagination" in data
    assert len(data["items"]) <= 10


def test_api_create_and_delete_ward(client):
    # Create
    create_res = client.post(
        "/metadata/api/wards",
        data={
            "name": "Xã Tân Mẫu",
            "code": "XTM01",
            "type": "Xã",
            "province_name": "Thành phố Hà Nội",
            "district_name": "Huyện Gia Lâm",
            "merged_note": "Sáp nhập 2025",
            "status": "active",
        },
        headers={"Accept": "application/json"},
    )
    assert create_res.status_code == 200
    create_json = create_res.json()
    assert create_json.get("ok") is True
    w_id = create_json["ward"]["id"]

    # Edit
    edit_res = client.post(
        f"/metadata/api/wards/{w_id}/edit",
        data={
            "name": "Xã Tân Mẫu Mới",
            "status": "inactive",
        },
        headers={"Accept": "application/json"},
    )
    assert edit_res.status_code == 200
    edit_json = edit_res.json()
    assert edit_json.get("ok") is True
    assert edit_json["ward"]["name"] == "Xã Tân Mẫu Mới"

    # Delete
    del_res = client.post(
        f"/metadata/api/wards/{w_id}/delete",
        headers={"Accept": "application/json"},
    )
    assert del_res.status_code == 200
    assert del_res.json().get("ok") is True


@pytest.mark.anyio
async def test_ward_province_mapping_service():
    # Test resolving province mapping from code
    mapping_by_code = await services.resolve_province_mapping(province_code="01")
    assert mapping_by_code["province_code"] == "01"
    assert "Hà Nội" in mapping_by_code["province_name"]
    assert mapping_by_code["province_id"] == 1

    # Test resolving former province name (e.g. Hải Dương -> TP. Hải Phòng code 31)
    mapping_old = await services.resolve_province_mapping(province_name="Tỉnh Hải Dương")
    assert mapping_old["province_code"] == "31"
    assert "Hải Phòng" in mapping_old["province_name"]
    assert mapping_old["old_province_name"] == "Tỉnh Hải Dương"

    # Test creating ward with mapped province
    created = await services.create_ward(
        None,
        {
            "name": "Xã Hải Dương Thử Nghiệm",
            "province_name": "Tỉnh Hải Dương",
            "type": "Xã",
        },
    )
    assert created["province_code"] == "31"
    assert created["province_name"] in ("Hải Phòng", "TP. Hải Phòng", "Thành phố Hải Phòng")
    assert created["old_province_name"] == "Tỉnh Hải Dương"

