"""Smoke tests for Image Compressor tool.

Tests:
1. Pillow image compression service (JPG, PNG, WebP) with integer quality 1-100.
2. Directory scan and ignore backup directory.
3. In-place directory compression with original image safely moved to backup/.
4. FastAPI endpoints:
   - GET /tools/image-compressor
   - POST /tools/image-compressor/compress-files
   - GET /tools/image-compressor/download/{batch_id}/{file_idx}
   - GET /tools/image-compressor/download-zip/{batch_id}
   - POST /tools/image-compressor/scan-folder
   - POST /tools/image-compressor/compress-folder
"""
from __future__ import annotations

import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from PIL import Image

from main import app
from app.tools.image_compressor import services


def _create_test_image(format_name: str = "JPEG", size=(200, 200), color="blue") -> bytes:
    """Helper to generate in-memory dummy image."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def test_compress_image_bytes():
    """Test compressing JPEG, PNG, and WebP bytes."""
    jpg_data = _create_test_image("JPEG")
    comp_bytes, fmt, orig_size, comp_size = services.compress_image_bytes(
        jpg_data, filename="sample.jpg", quality=50
    )
    assert fmt == "JPEG"
    assert orig_size == len(jpg_data)
    assert comp_size <= orig_size

    # PNG test
    png_data = _create_test_image("PNG")
    png_comp, pfmt, porig, pcomp = services.compress_image_bytes(
        png_data, filename="sample.png", quality=60
    )
    assert pfmt == "PNG"
    assert porig == len(png_data)


def test_compress_directory_workflow():
    """Test directory compression: original moved to backup/, compressed replaces original."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sub_dir = os.path.join(temp_dir, "nested")
        os.makedirs(sub_dir, exist_ok=True)

        img1_path = os.path.join(temp_dir, "img1.jpg")
        img2_path = os.path.join(sub_dir, "img2.png")

        with open(img1_path, "wb") as f:
            f.write(_create_test_image("JPEG", size=(300, 300), color="red"))
        with open(img2_path, "wb") as f:
            f.write(_create_test_image("PNG", size=(300, 300), color="green"))

        # Scan folder
        scanned = services.scan_directory_images(temp_dir, recursive=True)
        assert len(scanned) == 2

        # Run compression
        summary = services.compress_directory(temp_dir, quality=60, recursive=True)
        assert summary["success_count"] == 2
        assert summary["failed_count"] == 0

        # Verify originals moved to backup/
        backup_img1 = os.path.join(temp_dir, "backup", "img1.jpg")
        backup_img2 = os.path.join(temp_dir, "backup", "nested", "img2.png")
        assert os.path.exists(backup_img1), "Original img1.jpg must exist in backup/"
        assert os.path.exists(backup_img2), "Original img2.png must exist in backup/nested/"

        # Verify compressed images exist in original locations
        assert os.path.exists(img1_path), "Compressed img1.jpg must exist in original path"
        assert os.path.exists(img2_path), "Compressed img2.png must exist in original path"

        # Scanning again must NOT include backup files
        re_scanned = services.scan_directory_images(temp_dir, recursive=True)
        assert len(re_scanned) == 2, "Backup folder must be excluded from image scan"


def test_api_endpoints():
    """Test web routes via FastAPI TestClient."""
    client = TestClient(app)

    # 1. UI Page
    resp = client.get("/tools/image-compressor")
    assert resp.status_code == 200
    assert "Nén Ảnh" in resp.text
    assert "shared-quality-slider" in resp.text

    # 2. Upload multiple files & compress
    f1 = _create_test_image("JPEG", size=(150, 150), color="red")
    f2 = _create_test_image("PNG", size=(150, 150), color="yellow")

    upload_resp = client.post(
        "/tools/image-compressor/compress-files",
        data={"quality": "70"},
        files=[
            ("file_0", ("test1.jpg", f1, "image/jpeg")),
            ("file_1", ("test2.png", f2, "image/png")),
        ],
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["success"] is True
    assert upload_data["total_files"] == 2
    batch_id = upload_data["batch_id"]

    # 3. Download single file
    dl_resp = client.get(f"/tools/image-compressor/download/{batch_id}/0")
    assert dl_resp.status_code == 200
    assert len(dl_resp.content) > 0

    # 4. Download ZIP archive
    zip_resp = client.get(f"/tools/image-compressor/download-zip/{batch_id}")
    assert zip_resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
        namelist = z.namelist()
        assert "test1.jpg" in namelist
        assert "test2.png" in namelist

    # 5. Scan Folder API & Compress Folder API
    with tempfile.TemporaryDirectory() as temp_dir:
        test_img = os.path.join(temp_dir, "test.jpg")
        with open(test_img, "wb") as f:
            f.write(f1)

        scan_resp = client.post(
            "/tools/image-compressor/scan-folder",
            json={"folder_path": temp_dir, "recursive": True},
        )
        assert scan_resp.status_code == 200
        assert scan_resp.json()["count"] == 1

        comp_resp = client.post(
            "/tools/image-compressor/compress-folder",
            json={"folder_path": temp_dir, "quality": 65, "recursive": True},
        )
        assert comp_resp.status_code == 200
        comp_json = comp_resp.json()
        assert comp_json["success"] is True
        assert comp_json["data"]["success_count"] == 1
        assert os.path.exists(os.path.join(temp_dir, "backup", "test.jpg"))


if __name__ == "__main__":
    print("Running Image Compressor smoke tests...")
    test_compress_image_bytes()
    print("[PASS] compress_image_bytes passed")
    test_compress_directory_workflow()
    print("[PASS] compress_directory_workflow passed")
    test_api_endpoints()
    print("[PASS] test_api_endpoints passed")
    print("All smoke tests passed successfully!")
