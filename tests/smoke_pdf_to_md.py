"""Smoke tests for the PDF to Markdown tool.

Covers:
1. Pure text PDF conversion.
2. Mixed text & image PDF conversion with image extraction and zip packaging.
3. Scanned PDF page fallback handling.
4. Base64 inline image embedding mode.
5. FastApi endpoint routing (GET /tools/pdf-to-md and POST /tools/pdf-to-md/convert).
"""
import io
from pathlib import Path
import sys
import tempfile
import zipfile

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz  # PyMuPDF
from fastapi.testclient import TestClient

from main import app
from app.tools.pdf_to_md import services


def _create_sample_pdf(with_text: bool = True, with_image: bool = True, is_scanned: bool = False) -> bytes:
    """Helper to generate an in-memory PDF fixture."""
    doc = fitz.open()

    if is_scanned:
        # Page with pure image (no text layer)
        p = doc.new_page(width=400, height=500)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 150, 150), 0)
        p.insert_image(fitz.Rect(50, 50, 200, 200), pixmap=pix)
    else:
        p = doc.new_page(width=500, height=700)
        if with_text:
            p.insert_text((50, 60), "Doan van dau tien cua tai lieu.")
        if with_image:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100), 0)
            p.insert_image(fitz.Rect(50, 80, 150, 180), pixmap=pix)
        if with_text:
            p.insert_text((50, 210), "Doan van thu hai nam sau hinh anh.")

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pure_text_pdf():
    pdf_bytes = _create_sample_pdf(with_text=True, with_image=False)
    result = services.convert_pdf_bytes(
        pdf_bytes, pages_per_file=10, source_name="van_ban_thuan.pdf"
    )
    assert len(result.parts) == 1
    assert len(result.images) == 0
    content = result.parts[0]["content"]
    assert "Doan van dau tien" in content
    print("test_pure_text_pdf passed")


def test_mixed_text_and_image_pdf():
    pdf_bytes = _create_sample_pdf(with_text=True, with_image=True)
    result = services.convert_pdf_bytes(
        pdf_bytes,
        pages_per_file=10,
        source_name="tai_lieu_co_anh.pdf",
        extract_images=True,
        image_embed_mode="folder",
    )
    assert len(result.parts) == 1
    assert len(result.images) >= 1
    # Check that image filename is in markdown
    img_rel_path = next(iter(result.images.keys()))
    assert "images/" in img_rel_path
    content = result.parts[0]["content"]
    assert img_rel_path in content
    # Check ordering: text 1 before image, image before text 2
    pos1 = content.find("Doan van dau tien")
    pos_img = content.find(img_rel_path)
    pos2 = content.find("Doan van thu hai")
    assert pos1 != -1 and pos_img != -1 and pos2 != -1
    assert pos1 < pos_img < pos2, "Image is not placed in proper reading sequence"
    print("test_mixed_text_and_image_pdf passed")


def test_scanned_pdf_fallback():
    pdf_bytes = _create_sample_pdf(is_scanned=True)
    result = services.convert_pdf_bytes(
        pdf_bytes,
        pages_per_file=10,
        source_name="tai_lieu_scan.pdf",
        ocr_mode="off",  # test offline image fallback
    )
    assert len(result.parts) == 1
    assert result.scanned_pages == 1
    content = result.parts[0]["content"]
    assert "Trang scan" in content
    assert len(result.images) >= 1
    print("test_scanned_pdf_fallback passed")


def test_base64_embed_mode():
    pdf_bytes = _create_sample_pdf(with_text=True, with_image=True)
    result = services.convert_pdf_bytes(
        pdf_bytes,
        pages_per_file=10,
        source_name="inline_mode.pdf",
        extract_images=True,
        image_embed_mode="base64",
    )
    assert len(result.parts) == 1
    assert len(result.images) == 0  # Inlined, so no separate images dictionary
    content = result.parts[0]["content"]
    assert "data:image/png;base64," in content
    print("test_base64_embed_mode passed")


def test_batch_convert_folder():
    with tempfile.TemporaryDirectory() as tmp_dir:
        src = Path(tmp_dir) / "src"
        out = Path(tmp_dir) / "out"
        src.mkdir()
        out.mkdir()

        (src / "sample1.pdf").write_bytes(_create_sample_pdf(with_text=True, with_image=True))
        (src / "sample2.pdf").write_bytes(_create_sample_pdf(is_scanned=True))

        summary = services.convert_folder(src, out, pages_per_file=5)
        assert summary["ok"] == 2
        assert summary["failed"] == 0

        # Verify folder structures
        folder1 = out / "sample1"
        assert folder1.exists()
        assert any(folder1.glob("*.md"))
        assert (folder1 / "images").exists()

        folder2 = out / "sample2"
        assert folder2.exists()
        assert any(folder2.glob("*.md"))
        print("test_batch_convert_folder passed")


def test_api_routes():
    client = TestClient(app)

    # 1. Page route
    res = client.get("/tools/pdf-to-md")
    assert res.status_code == 200
    assert "PDF to Markdown" in res.text

    # 2. Upload text-only PDF -> returns .md
    pdf_text = _create_sample_pdf(with_text=True, with_image=False)
    res_upload_text = client.post(
        "/tools/pdf-to-md/convert",
        files={"file": ("text_only.pdf", pdf_text, "application/pdf")},
        data={"pages_per_file": 10, "extract_images": "false"},
    )
    assert res_upload_text.status_code == 200
    assert "text/markdown" in res_upload_text.headers.get("content-type", "")

    # 3. Upload mixed PDF with images -> returns .zip containing .md and images/
    pdf_mixed = _create_sample_pdf(with_text=True, with_image=True)
    res_upload_mixed = client.post(
        "/tools/pdf-to-md/convert",
        files={"file": ("doc_mixed.pdf", pdf_mixed, "application/pdf")},
        data={"pages_per_file": 10, "extract_images": "true", "image_embed_mode": "folder"},
    )
    assert res_upload_mixed.status_code == 200
    assert "application/zip" in res_upload_mixed.headers.get("content-type", "")

    # Inspect zip contents
    with zipfile.ZipFile(io.BytesIO(res_upload_mixed.content)) as zf:
        namelist = zf.namelist()
        assert any(name.endswith(".md") for name in namelist)
        assert any(name.startswith("images/") for name in namelist)

    print("test_api_routes passed")


if __name__ == "__main__":
    test_pure_text_pdf()
    test_mixed_text_and_image_pdf()
    test_scanned_pdf_fallback()
    test_base64_embed_mode()
    test_batch_convert_folder()
    test_api_routes()
    print("ALL PDF-TO-MD TESTS PASSED SUCCESSFULLY!")
