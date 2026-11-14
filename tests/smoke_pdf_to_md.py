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

    # 4. Upload scanned PDF with ocr_images="false" -> returns zip containing scan image
    pdf_scan = _create_sample_pdf(is_scanned=True)
    res_upload_scan = client.post(
        "/tools/pdf-to-md/convert",
        files={"file": ("scan_doc.pdf", pdf_scan, "application/pdf")},
        data={"pages_per_file": 10, "ocr_images": "false"},
    )
    assert res_upload_scan.status_code == 200
    with zipfile.ZipFile(io.BytesIO(res_upload_scan.content)) as zf:
        assert any("_scan.png" in name for name in zf.namelist())

    print("test_api_routes passed")


def test_ocr_images_toggle():
    """Verify that when ocr_images=False, scanned images are kept as scan images;
    when ocr_images=True, OCR is triggered to convert image to text."""
    from unittest.mock import patch

    pdf_scanned = _create_sample_pdf(is_scanned=True)

    # 1. ocr_images=False (Unticked): must keep scan image, no OCR called
    with patch.object(services, "_ocr_with_gemini") as mock_gemini, patch.object(
        services, "_ocr_with_ollama"
    ) as mock_ollama:
        res_unticked = services.convert_pdf_bytes(
            pdf_scanned,
            pages_per_file=10,
            source_name="test_scan.pdf",
            ocr_images=False,
            ocr_mode="auto",
        )
        # OCR was never called
        assert not mock_gemini.called
        assert not mock_ollama.called
        # Scan image was preserved
        assert len(res_unticked.images) >= 1
        assert any("_scan.png" in k for k in res_unticked.images.keys())
        assert "Bản scan trang 1" in res_unticked.parts[0]["content"]

    # 2. ocr_images=True (Ticked): calls OCR and converts to text
    with patch.object(
        services, "_ocr_with_gemini", return_value="Van ban OCR thanh cong tu anh scan"
    ) as mock_gemini:
        res_ticked = services.convert_pdf_bytes(
            pdf_scanned,
            pages_per_file=10,
            source_name="test_scan.pdf",
            ocr_images=True,
            ocr_mode="gemini",
            gemini_api_key="fake-key",
        )
        assert mock_gemini.called
        assert "Van ban OCR thanh cong tu anh scan" in res_ticked.parts[0]["content"]

    print("test_ocr_images_toggle passed")


def test_page_range_export():
    """Verify page range selection (start_page to end_page)."""
    import pytest

    # Create a 5-page PDF
    doc = fitz.open()
    for i in range(1, 6):
        page = doc.new_page(width=400, height=400)
        page.insert_text((50, 50), f"Noi dung dac biet cua trang thu {i}")
    pdf_5_pages = doc.tobytes()
    doc.close()

    # 1. Export range 2 to 4
    res_2_4 = services.convert_pdf_bytes(
        pdf_5_pages,
        pages_per_file=10,
        source_name="cuon_sach.pdf",
        start_page=2,
        end_page=4,
    )
    assert res_2_4.total_pages == 3
    assert len(res_2_4.parts) == 1
    content = res_2_4.parts[0]["content"]
    assert res_2_4.parts[0]["name"] == "cuon_sach_trang-2-4.md"
    assert "Noi dung dac biet cua trang thu 1" not in content
    assert "Noi dung dac biet cua trang thu 2" in content
    assert "Noi dung dac biet cua trang thu 3" in content
    assert "Noi dung dac biet cua trang thu 4" in content
    assert "Noi dung dac biet cua trang thu 5" not in content

    # 2. Export single page (page 3 to 3)
    res_3_3 = services.convert_pdf_bytes(
        pdf_5_pages,
        pages_per_file=10,
        source_name="cuon_sach.pdf",
        start_page=3,
        end_page=3,
    )
    assert res_3_3.total_pages == 1
    assert res_3_3.parts[0]["name"] == "cuon_sach_trang-3.md"
    content_3 = res_3_3.parts[0]["content"]
    assert "Noi dung dac biet cua trang thu 3" in content_3
    assert "Noi dung dac biet cua trang thu 2" not in content_3

    # 3. Invalid ranges
    try:
        services.convert_pdf_bytes(pdf_5_pages, start_page=10, end_page=12)
        assert False, "Should raise for start_page > total_pages"
    except services.PdfConversionError:
        pass

    try:
        services.convert_pdf_bytes(pdf_5_pages, start_page=4, end_page=2)
        assert False, "Should raise for start_page > end_page"
    except services.PdfConversionError:
        pass

    # 4. API endpoint with page range
    client = TestClient(app)
    res_api = client.post(
        "/tools/pdf-to-md/convert",
        files={"file": ("cuon_sach.pdf", pdf_5_pages, "application/pdf")},
        data={"start_page": 2, "end_page": 3},
    )
    assert res_api.status_code == 200
    assert "Noi dung dac biet cua trang thu 2" in res_api.text
    assert "Noi dung dac biet cua trang thu 3" in res_api.text
    assert "Noi dung dac biet cua trang thu 1" not in res_api.text

    print("test_page_range_export passed")


if __name__ == "__main__":
    test_pure_text_pdf()
    test_mixed_text_and_image_pdf()
    test_scanned_pdf_fallback()
    test_base64_embed_mode()
    test_batch_convert_folder()
    test_api_routes()
    test_ocr_images_toggle()
    test_page_range_export()
    print("ALL PDF-TO-MD TESTS PASSED SUCCESSFULLY!")
