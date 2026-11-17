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

    # Test trường hợp tiêu đề kèm (Title) và prompt kèm (bằng tiếng Việt)
    sample_user_case = (
        "**Tiêu đề (Title):** Cặp Đôi Cưới Ăn Pizza Trên Bậc Thang\n\n"
        "**Gợi ý prompt (bằng tiếng Việt):**\n\n"
        "Chụp ảnh chân dung đời thường của một cặp đôi đang ngồi trên bậc thang."
    )
    p5 = parse_title_and_prompt(sample_user_case)
    assert p5["title"] == "Cặp Đôi Cưới Ăn Pizza Trên Bậc Thang", f"Title error: {p5['title']}"
    assert "(Title)" not in p5["title"]
    assert "Title" not in p5["title"]
    assert p5["prompt"].startswith("Chụp ảnh chân dung"), f"Prompt error: {p5['prompt']}"
    assert "(bằng tiếng Việt)" not in p5["prompt"]
    assert "tiếng Việt" not in p5["prompt"][:30]

    print("   -> OK! parse_title_and_prompt xử lý sạch sẽ hoàn toàn '(Title):**' và '(bằng tiếng Việt):**'.")

    print("11. Kiểm tra chỉ thị nhân vật dùng ảnh tham chiếu trong prompt...")
    from app.tools.image_to_prompt.services import DEFAULT_SYSTEM_PROMPT
    assert "reference image" in DEFAULT_SYSTEM_PROMPT.lower()
    assert "character" in DEFAULT_SYSTEM_PROMPT.lower()
    print("   -> OK! DEFAULT_SYSTEM_PROMPT chỉ thị rõ ràng nhân vật nam/nữ dùng ảnh tham chiếu.")

    print("12. Kiểm tra hàm nhận diện tỷ lệ khung hình ảnh (detect_image_dimensions_and_ratio)...")
    from app.tools.image_to_prompt.services import detect_image_dimensions_and_ratio
    from PIL import Image
    import io

    # Tạo ảnh 16:9 (1920x1080)
    buf_16_9 = io.BytesIO()
    Image.new("RGB", (1920, 1080), color="blue").save(buf_16_9, format="JPEG")
    w1, h1, ar1 = detect_image_dimensions_and_ratio(buf_16_9.getvalue())
    assert (w1, h1, ar1) == (1920, 1080, "16:9")

    # Tạo ảnh 9:16 (1080x1920)
    buf_9_16 = io.BytesIO()
    Image.new("RGB", (1080, 1920), color="red").save(buf_9_16, format="PNG")
    w2, h2, ar2 = detect_image_dimensions_and_ratio(buf_9_16.getvalue())
    assert (w2, h2, ar2) == (1080, 1920, "9:16")

    # Tạo ảnh vuông 1:1 (512x512)
    buf_1_1 = io.BytesIO()
    Image.new("RGB", (512, 512), color="green").save(buf_1_1, format="PNG")
    w3, h3, ar3 = detect_image_dimensions_and_ratio(buf_1_1.getvalue())
    assert (w3, h3, ar3) == (512, 512, "1:1")
    print(f"   -> OK! Nhận diện chính xác 16:9 ({w1}x{h1}), 9:16 ({w2}x{h2}), 1:1 ({w3}x{h3}).")

    print("13. Kiểm tra gắn thông số tỷ lệ ảnh vào Prompt (apply_aspect_ratio_to_prompt)...")
    from app.tools.image_to_prompt.services import apply_aspect_ratio_to_prompt
    base_p = "A cinematic shot of a dragon."
    mj_p = apply_aspect_ratio_to_prompt(base_p, "16:9", mode="midjourney")
    assert mj_p == "A cinematic shot of a dragon. --ar 16:9"

    both_p = apply_aspect_ratio_to_prompt(base_p, "16:9", mode="both")
    assert "Aspect ratio: 16:9" in both_p
    assert "--ar 16:9" in both_p

    natural_p = apply_aspect_ratio_to_prompt(base_p, "9:16", mode="natural")
    assert "Aspect ratio: 9:16" in natural_p
    assert "--ar" not in natural_p

    none_p = apply_aspect_ratio_to_prompt(base_p, "16:9", mode="none")
    assert none_p == base_p
    print("   -> OK! apply_aspect_ratio_to_prompt hoạt động chuẩn xác theo mọi chế độ.")

    print("14. Kiểm tra endpoint lưu cấu hình mặc định (/save-defaults)...")
    save_data = {
        "model": "qween3.8",
        "language": "vi",
        "prompt": "Custom prompt description for Ollama",
        "character_desc": "nhân vật nam dùng ảnh tham chiếu cho khuôn mặt",
        "aspect_ratio_mode": "both",
    }
    r = client.post("/tools/image-to-prompt/save-defaults", data=save_data)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("   -> OK! Lưu cấu hình mô tả và tỷ lệ cho Ollama vào settings.json thành công.")

finally:
    shutil.rmtree(temp_dir, ignore_errors=True)

print("\n=== TẤT CẢ SMOKE TESTS CHO TOOL IMAGE TO PROMPT ĐỀU THÀNH CÔNG! ===")
