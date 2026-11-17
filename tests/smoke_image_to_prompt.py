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
        mock_generate.return_value = {
            "title": "Majestic Mountain at Sunset",
            "prompt": "A hyper-realistic photo of a majestic mountain, golden hour lighting",
        }

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

        # Kiểm tra file txt của image2 đã được tạo có cả Title và Prompt
        txt2 = temp_dir / "image2.txt"
        assert txt2.exists()
        txt2_content = txt2.read_text(encoding="utf-8")
        assert "Title: Majestic Mountain at Sunset" in txt2_content
        assert "Prompt:" in txt2_content
        assert "majestic mountain" in txt2_content

        # image1 không bị ghi đè vì overwrite=False
        assert txt1.read_text(encoding="utf-8") == "existing prompt 1"
        print("   -> OK! image2.txt đã được lưu đầy đủ Title + Prompt và image1.txt được giữ nguyên (không ghi đè).")

    print("6. Kiểm tra xử lý đơn lẻ 1 ảnh (/single)...")
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = {
            "title": "Neon Cyberpunk City",
            "prompt": "Cyberpunk city street at night, neon reflections",
        }
        files = {"file": ("test.png", b"\x89PNGdummy", "image/png")}
        r = client.post("/tools/image-to-prompt/single", files=files, data={"model": "qween3.8"})
        assert r.status_code == 200
        single_body = r.json()
        assert single_body["title"] == "Neon Cyberpunk City"
        assert "Cyberpunk" in single_body["prompt"]
        print(f"   -> OK! Title: '{single_body['title']}', Prompt: '{single_body['prompt'][:20]}...'")

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

    print("9. Kiểm tra tùy chọn ngôn ngữ đầu ra (prepare_prompt)...")
    from app.tools.image_to_prompt.services import prepare_prompt, parse_title_and_prompt
    tpl = "Describe in {output_language}."
    assert prepare_prompt(tpl, "en") == "Describe in English."
    assert "Vietnamese (Tiếng Việt)" in prepare_prompt(tpl, "vi")
    custom_p = "A custom prompt without placeholders."
    assert "Vietnamese" in prepare_prompt(custom_p, "vi")
    assert prepare_prompt(custom_p, "en") == custom_p
    print("   -> OK! Ngôn ngữ và prompt tùy chỉnh hoạt động chính xác.")

    print("10. Kiểm tra hàm bóc tách Tiêu đề & Prompt (parse_title_and_prompt)...")
    sample_md = "# Image Title\nHoàng Hôn Núi Tuyết\n\n# Prompt\nẢnh chụp góc rộng ngọn núi tuyết rực rỡ lúc hoàng hôn."
    p1 = parse_title_and_prompt(sample_md)
    assert p1["title"] == "Hoàng Hôn Núi Tuyết"
    assert "ngọn núi tuyết" in p1["prompt"]

    sample_kv = "Title: Golden Sunset\n\nPrompt:\nA cinematic sunset view over calm sea."
    p2 = parse_title_and_prompt(sample_kv)
    assert p2["title"] == "Golden Sunset"
    assert "cinematic sunset" in p2["prompt"]

    sample_json = '{"title": "Cat in Space", "prompt": "A cute cat wearing a tiny space helmet"}'
    p3 = parse_title_and_prompt(sample_json)
    assert p3["title"] == "Cat in Space"
    assert "cute cat" in p3["prompt"]

    sample_bold = "**Image Title:** Vintage Car in Rain\n**Prompt:** A black classic car on wet cobblestone."
    p4 = parse_title_and_prompt(sample_bold)
    assert p4["title"] == "Vintage Car in Rain"
    assert "classic car" in p4["prompt"]
    print("   -> OK! parse_title_and_prompt xử lý chính xác tất cả định dạng (Markdown header, Key-Value, JSON, Bold).")

    print("11. Kiểm tra chỉ thị nhân vật dùng ảnh tham chiếu trong prompt...")
    from app.tools.image_to_prompt.services import DEFAULT_SYSTEM_PROMPT
    assert "reference image" in DEFAULT_SYSTEM_PROMPT.lower()
    assert "character" in DEFAULT_SYSTEM_PROMPT.lower()
    print("   -> OK! DEFAULT_SYSTEM_PROMPT chỉ thị rõ ràng nhân vật nam/nữ dùng ảnh tham chiếu.")

finally:
    shutil.rmtree(temp_dir, ignore_errors=True)

print("\n=== TẤT CẢ SMOKE TESTS CHO TOOL IMAGE TO PROMPT ĐỀU THÀNH CÔNG! ===")
