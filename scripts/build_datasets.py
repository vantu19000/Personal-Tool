import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("app/metadata/data")

with open(DATA_DIR / "administrative_regions.json", encoding="utf-8") as f:
    regions = json.load(f)

with open(DATA_DIR / "administrative_units.json", encoding="utf-8") as f:
    units = json.load(f)

with open(DATA_DIR / "mongo_data_vn_unit.json", encoding="utf-8") as f:
    mongo_vn = json.load(f)

region_map = {r["Id"]: r for r in regions}
unit_map = {u["Id"]: u for u in units}

# Map 34 provinces to region IDs (1..8)
PROVINCE_TO_REGION = {
    # 1: Đông Bắc Bộ
    "04": 1,  # Cao Bằng
    "08": 1,  # Tuyên Quang
    "15": 1,  # Lào Cai
    "19": 1,  # Thái Nguyên
    "20": 1,  # Lạng Sơn
    "22": 1,  # Quảng Ninh
    "25": 1,  # Phú Thọ

    # 2: Tây Bắc Bộ
    "11": 2,  # Điện Biên
    "12": 2,  # Lai Châu
    "14": 2,  # Sơn La

    # 3: Đồng bằng sông Hồng
    "01": 3,  # Hà Nội
    "24": 3,  # Bắc Ninh
    "31": 3,  # Hải Phòng
    "33": 3,  # Hưng Yên
    "37": 3,  # Ninh Bình

    # 4: Bắc Trung Bộ
    "38": 4,  # Thanh Hoá
    "40": 4,  # Nghệ An
    "42": 4,  # Hà Tĩnh
    "44": 4,  # Quảng Trị
    "46": 4,  # Huế

    # 5: Duyên hải Nam Trung Bộ
    "48": 5,  # Đà Nẵng
    "51": 5,  # Quảng Ngãi
    "56": 5,  # Khánh Hoà

    # 6: Tây Nguyên
    "52": 6,  # Gia Lai
    "66": 6,  # Đắk Lắk
    "68": 6,  # Lâm Đồng

    # 7: Đông Nam Bộ
    "75": 7,  # Đồng Nai
    "79": 7,  # Hồ Chí Minh
    "80": 7,  # Tây Ninh

    # 8: Đồng bằng sông Cửu Long
    "82": 8,  # Đồng Tháp
    "86": 8,  # Vĩnh Long
    "91": 8,  # An Giang
    "92": 8,  # Cần Thơ
    "96": 8,  # Cà Mau
}

# Phone area codes
PROVINCE_PHONE_CODES = {
    "01": "024",
    "04": "0206",
    "08": "0207",
    "11": "0215",
    "12": "0213",
    "14": "0212",
    "15": "0214",
    "19": "0208",
    "20": "0205",
    "22": "0203",
    "24": "0222",
    "25": "0210",
    "31": "0225",
    "33": "0221",
    "37": "0229",
    "38": "0237",
    "40": "0238",
    "42": "0239",
    "44": "0233",
    "46": "0234",
    "48": "0236",
    "51": "0255",
    "52": "0269",
    "56": "0258",
    "66": "0262",
    "68": "0263",
    "75": "0251",
    "79": "028",
    "80": "0276",
    "82": "0277",
    "86": "0270",
    "91": "0296",
    "92": "0292",
    "96": "0290",
}

# Merge notes
PROVINCE_MERGED_NOTES = {
    "01": "Giữ nguyên (Thủ đô Hà Nội)",
    "04": "Giữ nguyên (Tỉnh Cao Bằng)",
    "08": "Hợp nhất tỉnh Hà Giang và tỉnh Tuyên Quang",
    "11": "Giữ nguyên (Tỉnh Điện Biên)",
    "12": "Giữ nguyên (Tỉnh Lai Châu)",
    "14": "Giữ nguyên (Tỉnh Sơn La)",
    "15": "Hợp nhất tỉnh Lào Cai và tỉnh Yên Bái",
    "19": "Hợp nhất tỉnh Thái Nguyên và tỉnh Bắc Kạn",
    "20": "Giữ nguyên (Tỉnh Lạng Sơn)",
    "22": "Thành phố trực thuộc Trung ương (Quảng Ninh)",
    "24": "Hợp nhất TP. Bắc Ninh và tỉnh Bắc Giang",
    "25": "Hợp nhất tỉnh Phú Thọ, Vĩnh Phúc và Hòa Bình",
    "31": "Hợp nhất TP. Hải Phòng và tỉnh Hải Dương",
    "33": "Hợp nhất tỉnh Hưng Yên và tỉnh Thái Bình",
    "37": "Hợp nhất tỉnh Ninh Bình, Nam Định và Hà Nam",
    "38": "Giữ nguyên (Tỉnh Thanh Hoá)",
    "40": "Giữ nguyên (Tỉnh Nghệ An)",
    "42": "Giữ nguyên (Tỉnh Hà Tĩnh)",
    "44": "Hợp nhất tỉnh Quảng Bình và tỉnh Quảng Trị",
    "46": "Nâng cấp thành Thành phố trực thuộc Trung ương (Huế)",
    "48": "Hợp nhất TP. Đà Nẵng và tỉnh Quảng Nam",
    "51": "Hợp nhất tỉnh Quảng Ngãi và tỉnh Kon Tum",
    "52": "Hợp nhất tỉnh Gia Lai và tỉnh Bình Định",
    "56": "Hợp nhất tỉnh Khánh Hòa và tỉnh Ninh Thuận",
    "66": "Hợp nhất tỉnh Đắk Lắk và tỉnh Phú Yên",
    "68": "Hợp nhất tỉnh Lâm Đồng, Đắk Nông và Bình Thuận",
    "75": "Hợp nhất TP. Đồng Nai và tỉnh Bình Phước",
    "79": "Hợp nhất TP. Hồ Chí Minh, Bình Dương và Bà Rịa - Vũng Tàu",
    "80": "Hợp nhất tỉnh Tây Ninh và tỉnh Long An",
    "82": "Hợp nhất tỉnh Đồng Tháp và tỉnh Tiền Giang",
    "86": "Hợp nhất tỉnh Vĩnh Long, Bến Tre và Trà Vinh",
    "91": "Hợp nhất tỉnh An Giang và tỉnh Kiên Giang",
    "92": "Hợp nhất TP. Cần Thơ, Sóc Trăng và Hậu Giang",
    "96": "Hợp nhất tỉnh Cà Mau và tỉnh Bạc Liêu",
}

now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

# Build Provinces
provinces = []
prov_code_to_id = {}

# Sort provinces by Code
sorted_mongo_vn = sorted(mongo_vn, key=lambda x: x["Code"])

for idx, p in enumerate(sorted_mongo_vn, start=1):
    code = p["Code"]
    unit_id = p.get("AdministrativeUnitId", 2)
    unit_info = unit_map.get(unit_id, {})
    unit_fullname = unit_info.get("FullName", "Tỉnh")
    
    region_id = PROVINCE_TO_REGION.get(code, 1)
    region_info = region_map.get(region_id, {})
    region_name = region_info.get("Name", "Đồng bằng sông Hồng")
    region_en = region_info.get("NameEn", "Red River Delta")

    first_prefix = (p.get("PostalCodePrefix") or "10").split(",")[0].strip()
    postal_code = f"{first_prefix}000" if len(first_prefix) <= 3 else first_prefix

    wards_in_p = p.get("Wards", [])

    prov_doc = {
        "id": idx,
        "code": code,
        "name": p["Name"],
        "name_en": p.get("NameEn", ""),
        "full_name": p.get("FullName", f"{unit_fullname} {p['Name']}"),
        "full_name_en": p.get("FullNameEn", ""),
        "code_name": p.get("CodeName", ""),
        "administrative_unit_id": unit_id,
        "administrative_unit_name": unit_fullname,
        "administrative_region_id": region_id,
        "type": unit_fullname,
        "region": region_name,
        "region_en": region_en,
        "postal_code_prefix": p.get("PostalCodePrefix", ""),
        "postal_code": postal_code,
        "phone_code": PROVINCE_PHONE_CODES.get(code, ""),
        "merged_from": PROVINCE_MERGED_NOTES.get(code, ""),
        "country_code": "VN",
        "wards_count": len(wards_in_p),
        "status": "active",
        "created_at": now_str,
        "updated_at": now_str,
    }
    provinces.append(prov_doc)
    prov_code_to_id[code] = prov_doc

# Build Wards
wards = []
ward_id_counter = 1

for p in sorted_mongo_vn:
    code = p["Code"]
    prov_doc = prov_code_to_id[code]

    for w in p.get("Wards", []):
        w_unit_id = w.get("AdministrativeUnitId", 4)
        w_unit_info = unit_map.get(w_unit_id, {})
        w_type_name = w_unit_info.get("ShortName", "Xã")
        w_unit_fullname = w_unit_info.get("FullName", "Xã")

        ward_doc = {
            "id": ward_id_counter,
            "code": w["Code"],
            "name": w["Name"],
            "name_en": w.get("NameEn", ""),
            "full_name": w.get("FullName", f"{w_type_name} {w['Name']}"),
            "full_name_en": w.get("FullNameEn", ""),
            "code_name": w.get("CodeName", ""),
            "type": w_type_name,
            "administrative_unit_id": w_unit_id,
            "administrative_unit_name": w_unit_fullname,
            "province_id": prov_doc["id"],
            "province_code": code,
            "province_name": prov_doc["name"],
            "province_full_name": prov_doc["full_name"],
            "postal_code": w.get("PostalCode", ""),
            "status": "active",
            "created_at": now_str,
            "updated_at": now_str,
        }
        wards.append(ward_doc)
        ward_id_counter += 1

print(f"Generated {len(provinces)} provinces and {len(wards)} wards.")

# Write to files
with open(DATA_DIR / "vn_provinces.json", "w", encoding="utf-8") as f:
    json.dump(provinces, f, ensure_ascii=False, indent=2)

with open(DATA_DIR / "vn_wards.json", "w", encoding="utf-8") as f:
    json.dump(wards, f, ensure_ascii=False, indent=2)

print("Saved vn_provinces.json and vn_wards.json successfully.")
