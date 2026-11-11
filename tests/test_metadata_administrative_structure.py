"""Tests for Administrative Regions, Units, 34 Provinces and 3,321 Wards structure."""
import pytest
from fastapi.testclient import TestClient

from app.metadata import services
from app.metadata.models import (
    AdministrativeRegionModel,
    AdministrativeUnitModel,
    ProvinceModel,
    WardModel,
)
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_administrative_models():
    reg = AdministrativeRegionModel(
        id=3,
        name="Đồng bằng sông Hồng",
        name_en="Red River Delta",
        code_name="dong_bang_song_hong",
        code_name_en="red_river_delta",
    )
    assert reg.id == 3
    assert reg.name == "Đồng bằng sông Hồng"

    unit = AdministrativeUnitModel(
        id=5,
        full_name="Đặc khu tại hải đảo",
        short_name="Đặc khu",
        code_name="dac_khu",
    )
    assert unit.id == 5
    assert unit.short_name == "Đặc khu"

    prov = ProvinceModel(
        id=1,
        code="01",
        name="Hà Nội",
        full_name="Thành phố Hà Nội",
        name_en="Hanoi",
        administrative_unit_id=1,
        administrative_region_id=3,
    )
    assert prov.administrative_unit_id == 1
    assert prov.administrative_region_id == 3

    ward = WardModel(
        id=3152,
        code="31078",
        name="Phú Quốc",
        full_name="Đặc khu Phú Quốc",
        type="Đặc khu",
        administrative_unit_id=5,
        province_code="91",
    )
    assert ward.administrative_unit_id == 5
    assert ward.type == "Đặc khu"


def test_dataset_consistency():
    regions = services.load_administrative_regions_json()
    assert len(regions) == 8
    region_ids = {r["id"] for r in regions}
    assert region_ids == {1, 2, 3, 4, 5, 6, 7, 8}

    units = services.load_administrative_units_json()
    assert len(units) == 5
    unit_ids = {u["id"] for u in units}
    assert unit_ids == {1, 2, 3, 4, 5}

    provinces = services.load_vn_provinces_json()
    assert len(provinces) == 34
    for p in provinces:
        assert p["administrative_unit_id"] in (1, 2)
        assert p["administrative_region_id"] in region_ids
        assert len(p["code"]) == 2

    wards = services.load_vn_wards_json()
    assert len(wards) == 3321
    ward_unit_ids = {w["administrative_unit_id"] for w in wards}
    assert ward_unit_ids == {3, 4, 5}

    # Verify special island zones (UnitId: 5)
    island_wards = [w for w in wards if w["administrative_unit_id"] == 5]
    assert len(island_wards) == 13
    island_names = [w["name"] for w in island_wards]
    assert "Trường Sa" in island_names
    assert "Hoàng Sa" in island_names
    assert "Phú Quốc" in island_names
    assert "Côn Đảo" in island_names


def test_api_regions_and_units(client):
    r_res = client.get("/metadata/api/regions")
    assert r_res.status_code == 200
    r_data = r_res.json()
    assert r_data["ok"] is True
    assert len(r_data["items"]) == 8

    u_res = client.get("/metadata/api/units")
    assert u_res.status_code == 200
    u_data = u_res.json()
    assert u_data["ok"] is True
    assert len(u_data["items"]) == 5


def test_provinces_filtering_and_counts(client):
    # Filter by region
    res_region = client.get("/metadata/api/provinces?region=Đồng bằng sông Hồng")
    assert res_region.status_code == 200
    data_region = res_region.json()
    assert data_region["total"] == 5

    # Filter by unit type (1: TP trực thuộc TW)
    res_type = client.get("/metadata/api/provinces?type=1")
    assert res_type.status_code == 200
    data_type = res_type.json()
    assert data_type["total"] == 9


def test_wards_filtering_by_island_and_province(client):
    # Filter by island special zones (UnitId: 5 or type=dac_khu)
    res_island = client.get("/metadata/api/wards?type=5")
    assert res_island.status_code == 200
    data_island = res_island.json()
    assert data_island["total"] == 13

    # Filter by province code 01 (Hà Nội)
    res_hanoi = client.get("/metadata/api/wards?province=01")
    assert res_hanoi.status_code == 200
    data_hanoi = res_hanoi.json()
    assert data_hanoi["total"] == 126
