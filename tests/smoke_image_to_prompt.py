"""Smoke test for the Image to Prompt tool (run with: python tests/smoke_image_to_prompt.py)."""
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

print("1. Kiểm tra trang giao diện Image to Prompt render thành công...")
r = client.get("/tools/image-to-prompt")
assert r.status_code == 200, f"Status code: {r.status_code}"
assert "Image to Prompt" in r.text
assert "qween3.8" in r.text
assert "ollama-status-pill" in r.text
assert "ollama-offline-banner" in r.text
print("   -> OK!")

print("2. Kiểm tra Dashboard và Sidebar hiển thị công cụ...")
r = client.get("/")
assert r.status_code == 200
assert "/tools/image-to-prompt" in r.text
print("   -> OK!")

print("3. Kiểm tra endpoint lấy danh sách model (/models)...")
r = client.get("/tools/image-to-prompt/models")
assert r.status_code == 200
body = r.json()
assert "online" in body
assert "models" in body
assert body["default"] == "qween3.8"
print(f"   -> OK! (online={body['online']}, models={len(body['models'])})")

print("4. Kiểm tra quét thư mục ảnh (/scan)...")
temp_dir = Path(tempfile.mkdtemp(prefix="test_img_prompt_"))
try:
    # Tạo ảnh giả lập
    img1 = temp_dir / "image1.jpg"
    img1.write_bytes(b"\xFF\xD8\xFF\xE0dummy_jpg_1")
    img2 = temp_dir / "image2.png"
    img2.write_bytes(b"\x89PNGdummy_png_2")
    # Tạo sẵn 1 file txt
    txt1 = temp_dir / "image1.txt"
    txt1.write_text("existing prompt 1", encoding="utf-8")

    r = client.get(f"/tools/image-to-prompt/scan?folder={temp_dir}")
    assert r.status_code == 200
    scan_body = r.json()
    assert scan_body["count"] == 2
    assert scan_body["existing_txt_count"] == 1
    files = {f["name"]: f for f in scan_body["files"]}
    assert files["image1.jpg"]["has_txt"] is True
    assert files["image2.png"]["has_txt"] is False
    print("   -> OK! Đã phát hiện 2 file ảnh và 1 file .txt sẵn có.")

    print("5. Kiểm tra xử lý batch ảnh (Mock Ollama)...")
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = "A hyper-realistic photo of a majestic mountain, golden hour lighting"

        data = {
            "folder": str(temp_dir),
            "model": "qween3.8",
            "prompt": "Test prompt",
            "overwrite": "false",
            "recursive": "false",
        }
        r = client.post("/tools/image-to-prompt/process", data=data)
        assert r.status_code == 200
        lines = [line.strip() for line in r.text.strip().split("\n") if line.strip()]
        assert len(lines) >= 3

        # Kiểm tra file txt của image2 đã được tạo
        txt2 = temp_dir / "image2.txt"
        assert txt2.exists()
        assert "majestic mountain" in txt2.read_text(encoding="utf-8")

        # image1 không bị ghi đè vì overwrite=False
        assert txt1.read_text(encoding="utf-8") == "existing prompt 1"
        print("   -> OK! image2.txt đã được lưu và image1.txt được giữ nguyên (không ghi đè).")

    print("6. Kiểm tra xử lý đơn lẻ 1 ảnh (/single)...")
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = "Cyberpunk city street at night, neon reflections"
        files = {"file": ("test.png", b"\x89PNGdummy", "image/png")}
        r = client.post("/tools/image-to-prompt/single", files=files, data={"model": "qween3.8"})
        assert r.status_code == 200
        single_body = r.json()
        assert "Cyberpunk" in single_body["prompt"]
        print("   -> OK! Prompt đơn lẻ trả về chính xác.")

    print("7. Kiểm tra trích xuất nguyên bản lỗi từ Ollama (extract_ollama_error)...")
    from app.tools.image_to_prompt.services import extract_ollama_error, ImageToPromptError
    raw_ollama_json = '{"error": "Multimodal data provided, but model does not support multimodal requests."}'
    extracted = extract_ollama_error(raw_ollama_json)
    assert extracted == "Multimodal data provided, but model does not support multimodal requests."
    print("   -> OK! Lấy nguyên bản lỗi từ JSON Ollama chính xác.")

    print("8. Kiểm tra báo lỗi khi gọi API /single...")
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.side_effect = ImageToPromptError("Multimodal data provided, but model does not support multimodal requests.")
        files = {"file": ("test.png", b"\x89PNGdummy", "image/png")}
        r = client.post("/tools/image-to-prompt/single", files=files, data={"model": "llama3:latest"})
        assert r.status_code == 400
        err_json = r.json()
        assert err_json["detail"] == "Multimodal data provided, but model does not support multimodal requests."
        print(f"   -> OK! Status 400 trả đúng nguyên bản lỗi: {err_json['detail']}")

finally:
    shutil.rmtree(temp_dir, ignore_errors=True)

print("\n=== TẤT CẢ SMOKE TESTS CHO TOOL IMAGE TO PROMPT ĐỀU THÀNH CÔNG! ===")
