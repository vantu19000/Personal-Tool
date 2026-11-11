"""CLI Migration tool to import ISO countries and Vietnam Administrative units into MongoDB.

Usage:
    python -m app.metadata.migrate --all
    python -m app.metadata.migrate --vn-units
    python -m app.metadata.migrate --countries --overwrite
    python -m app.metadata.migrate --provinces
    python -m app.metadata.migrate --wards
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.core.database import check_db_connection, get_mongo_database
from app.metadata import services


async def run_vn_units_migration(reset: bool = True):
    print("=" * 60)
    print("🚀 BẮT ĐẦU MIGRATE HỆ THỐNG ĐƠN VỊ HÀNH CHÍNH VIỆT NAM VÀO MONGODB")
    print("  • 8 Vùng kinh tế - xã hội (administrative_regions.json)")
    print("  • 5 Cấp đơn vị hành chính (administrative_units.json)")
    print("  • 34 Tỉnh / Thành phố mới (mongo_data_vn_unit.json)")
    print("  • 3.321 Xã / Phường / Đặc khu hải đảo")
    print("=" * 60)

    conn = await check_db_connection()
    if not conn.get("connected"):
        print(f"❌ Không thể kết nối tới MongoDB: {conn.get('error')}")
        return 1

    print(f"✅ Kết nối MongoDB: {conn.get('database')} @ {conn.get('host')}:{conn.get('port')}")
    db = get_mongo_database()

    print("\n⏳ Đang nạp và đồng bộ hóa toàn bộ dữ liệu...")
    res = await services.migrate_all_vn_units(db=db, reset=reset)

    if not res.get("ok"):
        print(f"❌ Lỗi khi migrate: {res.get('error')}")
        return 1

    print("\n" + "=" * 60)
    print("🎉 KẾT QUẢ MIGRATION ĐƠN VỊ HÀNH CHÍNH VN:")
    print(f" • 8 Vùng kinh tế - xã hội    : {res.get('regions')}")
    print(f" • 5 Cấp đơn vị hành chính   : {res.get('units')}")
    p_info = res.get("provinces", {})
    print(f" • 34 Tỉnh / Thành phố       : {p_info.get('inserted') or p_info.get('total_now')}")
    w_info = res.get("wards", {})
    print(f" • 3.321 Xã / Phường / Đặc khu: {w_info.get('total_imported') or w_info.get('total_now')}")
    print("=" * 60)
    return 0


async def run_countries_migration(overwrite: bool = False, reset: bool = False):
    print("=" * 60)
    print("🚀 BẮT ĐẦU MIGRATE 249 QUỐC GIA CHUẨN ISO 3166-1 VÀO MONGODB")
    print("=" * 60)

    conn = await check_db_connection()
    if not conn.get("connected"):
        print(f"❌ Không thể kết nối tới MongoDB: {conn.get('error')}")
        return 1

    print(f"✅ Kết nối MongoDB: {conn.get('database')} @ {conn.get('host')}:{conn.get('port')}")
    db = get_mongo_database()

    print(f"⏳ Đang xử lý import dữ liệu (overwrite={overwrite}, reset={reset})...")
    res = await services.migrate_iso_countries(db=db, overwrite=overwrite, reset=reset)

    if not res.get("ok"):
        print(f"❌ Lỗi khi migrate: {res.get('error')}")
        return 1

    print("\n" + "=" * 60)
    print("🎉 KẾT QUẢ MIGRATION QUỐC GIA:")
    print(f" • Tổng số quốc gia chuẩn ISO: {res.get('total_iso')}")
    print(f" • Thêm mới thành công        : {res.get('inserted')}")
    print(f" • Cập nhật                  : {res.get('updated')}")
    print(f" • Bỏ qua (đã tồn tại)       : {res.get('skipped')}")
    print(f" • Tổng số quốc gia hiện tại : {res.get('total_now')}")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Migrate Metadata collections into MongoDB")
    parser.add_argument(
        "--countries",
        action="store_true",
        help="Migrate 249 ISO countries",
    )
    parser.add_argument(
        "--vn-units",
        action="store_true",
        help="Migrate Vietnam administrative units (regions, units, 34 provinces, 3,321 wards)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Migrate everything (countries + VN administrative units)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ghi đè thông tin đã tồn tại",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=True,
        help="Xóa dữ liệu cũ và nạp mới toàn bộ",
    )
    args = parser.parse_args()

    # If no flags specified, default to migrating VN units
    if not args.countries and not args.vn_units and not args.all:
        args.vn_units = True

    async def runner():
        code = 0
        if args.all or args.countries:
            c_code = await run_countries_migration(overwrite=args.overwrite, reset=args.reset)
            if c_code != 0:
                code = c_code
        if args.all or args.vn_units:
            v_code = await run_vn_units_migration(reset=args.reset)
            if v_code != 0:
                code = v_code
        return code

    exit_code = asyncio.run(runner())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
