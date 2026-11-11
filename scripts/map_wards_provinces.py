"""Map all 10,599 wards in vn_wards.json to the 34 provinces in vn_provinces.json."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "metadata" / "data"
PROVINCES_FILE = DATA_DIR / "vn_provinces.json"
WARDS_FILE = DATA_DIR / "vn_wards.json"

OLD_TO_NEW_PROVINCE_CODE = {
    'Thành phố Hà Nội': '01',
    'Thành phố Hải Phòng': '31',
    'Tỉnh Hải Dương': '31',
    'Tỉnh Thừa Thiên Huế': '46',
    'Thành phố Đà Nẵng': '48',
    'Tỉnh Quảng Nam': '48',
    'Thành phố Hồ Chí Minh': '79',
    'Tỉnh Bình Dương': '79',
    'Tỉnh Bà Rịa - Vũng Tàu': '79',
    'Thành phố Cần Thơ': '92',
    'Tỉnh Sóc Trăng': '92',
    'Tỉnh Hậu Giang': '92',
    'Tỉnh Cao Bằng': '04',
    'Tỉnh Lạng Sơn': '20',
    'Tỉnh Lai Châu': '12',
    'Tỉnh Điện Biên': '11',
    'Tỉnh Sơn La': '14',
    'Tỉnh Quảng Ninh': '22',
    'Tỉnh Thanh Hóa': '38',
    'Tỉnh Nghệ An': '40',
    'Tỉnh Hà Tĩnh': '42',
    'Tỉnh Hà Giang': '08',
    'Tỉnh Tuyên Quang': '08',
    'Tỉnh Lào Cai': '10',
    'Tỉnh Yên Bái': '10',
    'Tỉnh Bắc Kạn': '19',
    'Tỉnh Thái Nguyên': '19',
    'Tỉnh Phú Thọ': '25',
    'Tỉnh Vĩnh Phúc': '25',
    'Tỉnh Hòa Bình': '25',
    'Tỉnh Hoà Bình': '25',
    'Tỉnh Bắc Ninh': '27',
    'Tỉnh Bắc Giang': '27',
    'Tỉnh Hưng Yên': '33',
    'Tỉnh Thái Bình': '33',
    'Tỉnh Ninh Bình': '37',
    'Tỉnh Nam Định': '37',
    'Tỉnh Hà Nam': '37',
    'Tỉnh Quảng Bình': '45',
    'Tỉnh Quảng Trị': '45',
    'Tỉnh Quảng Ngãi': '51',
    'Tỉnh Kon Tum': '51',
    'Tỉnh Gia Lai': '64',
    'Tỉnh Bình Định': '64',
    'Tỉnh Khánh Hòa': '56',
    'Tỉnh Khánh Hoà': '56',
    'Tỉnh Ninh Thuận': '56',
    'Tỉnh Đắk Lắk': '66',
    'Tỉnh Đắc Lắc': '66',
    'Tỉnh Phú Yên': '66',
    'Tỉnh Lâm Đồng': '68',
    'Tỉnh Đắk Nông': '68',
    'Tỉnh Đắc Nông': '68',
    'Tỉnh Bình Thuận': '68',
    'Tỉnh Đồng Nai': '75',
    'Tỉnh Bình Phước': '75',
    'Tỉnh Tây Ninh': '72',
    'Tỉnh Long An': '72',
    'Tỉnh Đồng Tháp': '87',
    'Tỉnh Tiền Giang': '87',
    'Tỉnh Vĩnh Long': '86',
    'Tỉnh Bến Tre': '86',
    'Tỉnh Trà Vinh': '86',
    'Tỉnh An Giang': '89',
    'Tỉnh Kiên Giang': '89',
    'Tỉnh Cà Mau': '96',
    'Tỉnh Bạc Liêu': '96'
}


def run():
    with open(PROVINCES_FILE, "r", encoding="utf-8-sig") as f:
        provinces = json.load(f)
    p_by_code = {p["code"]: p for p in provinces}

    with open(WARDS_FILE, "r", encoding="utf-8-sig") as f:
        wards = json.load(f)

    mapped = 0
    for w in wards:
        old_name = w.get("province_name")
        code = OLD_TO_NEW_PROVINCE_CODE.get(old_name)
        if code and code in p_by_code:
            target_prov = p_by_code[code]
            w["province_id"] = target_prov["id"]
            w["province_code"] = target_prov["code"]
            w["old_province_name"] = old_name
            w["province_name"] = target_prov["name"]
            if old_name != target_prov["name"]:
                w["merged_note"] = f"Nguyên thuộc {old_name} -> Sáp nhập vào {target_prov['name']}"
            else:
                w["merged_note"] = "Đơn vị hành chính cấp xã chuẩn hóa"
            mapped += 1
        else:
            print("Not mapped:", old_name)

    print(f"Mapped {mapped} of {len(wards)} wards.")
    with open(WARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(wards, f, ensure_ascii=False, indent=2)
    print("Saved vn_wards.json successfully.")


if __name__ == "__main__":
    run()
