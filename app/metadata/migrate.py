"""CLI Migration tool to import 249 ISO countries into MongoDB.

Usage:
    python -m app.metadata.migrate
    python -m app.metadata.migrate --overwrite
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


async def run_migration(overwrite: bool = False):
    print("=" * 60)
    print("🚀 BẮT ĐẦU MIGRATE 249 QUỐC GIA CHUẨN ISO 3166-1 VÀO MONGODB")
    print("=" * 60)

    # 1. Check connection
    conn = await check_db_connection()
    if not conn.get("connected"):
        print(f"❌ Không thể kết nối tới MongoDB: {conn.get('error')}")
        print("Vui lòng đảm bảo Docker container 'personal_tool_mongodb' đang chạy.")
        return 1

    print(f"✅ Kết nối MongoDB thành công: {conn.get('database')} @ {conn.get('host')}:{conn.get('port')}")
    db = get_mongo_database()

    # 2. Run migration
    print(f"⏳ Đang xử lý import dữ liệu (chế độ overwrite = {overwrite})...")
    res = await services.migrate_iso_countries(db=db, overwrite=overwrite)

    if not res.get("ok"):
        print(f"❌ Lỗi khi migrate: {res.get('error')}")
        return 1

    print("\n" + "=" * 60)
    print("🎉 KẾT QUẢ MIGRATION:")
    print(f" • Tổng số quốc gia chuẩn ISO: {res.get('total_iso')}")
    print(f" • Thêm mới thành công        : {res.get('inserted')}")
    print(f" • Cập nhật                  : {res.get('updated')}")
    print(f" • Bỏ qua (đã tồn tại)       : {res.get('skipped')}")
    print(f" • Tổng số quốc gia hiện tại : {res.get('total_now')}")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Migrate 249 ISO countries into MongoDB")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ghi đè thông tin các quốc gia đã tồn tại bằng dữ liệu chuẩn ISO",
    )
    args = parser.parse_args()
    code = asyncio.run(run_migration(overwrite=args.overwrite))
    sys.exit(code)


if __name__ == "__main__":
    main()
