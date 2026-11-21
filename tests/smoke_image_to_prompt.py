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
assert "qwen3.8:latest" in r.text or "qwen" in r.text
assert "ollama-status-pill" in r.text
assert "ollama-offline-banner" in r.text
print("   -> OK!")

print("1b. Kiểm tra alias URL /tools/prompt-pronto...")
r_alias = client.get("/tools/prompt-pronto")
assert r_alias.status_code == 200
assert "Prompt Pronto" in r_alias.text
print("   -> OK! Alias /tools/prompt-pronto hoạt động tốt.")

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
assert body["default"] == "qwen3.8:latest"
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
            "model": "qwen3.8:latest",
            "prompt": "Test prompt",
            "auto_rename": "false",
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
        r = client.post("/tools/image-to-prompt/single", files=files, data={"model": "qwen3.8:latest"})
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

    print("11. Kiểm tra DEFAULT_SYSTEM_PROMPT đã được loại bỏ...")
    from app.tools.image_to_prompt.services import DEFAULT_SYSTEM_PROMPT
    assert DEFAULT_SYSTEM_PROMPT == ""
    print("   -> OK! DEFAULT_SYSTEM_PROMPT đã được loại bỏ hoàn toàn (rỗng).")

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
        "model": "qwen3.8:latest",
        "language": "pt-BR",
        "prompt": "Custom prompt description for Ollama",
        "character_desc": "nhân vật nữ dùng ảnh tham chiếu cho khuôn mặt",
        "aspect_ratio_mode": "none",
        "target_aspect_ratio": "4:5",
    }
    r = client.post("/tools/image-to-prompt/save-defaults", data=save_data)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("   -> OK! Lưu cấu hình mô tả và tỷ lệ cho Ollama vào settings.json thành công.")

    print("15. Kiểm tra Step 1: Đổi tên ảnh thành image-1, image-2... (/rename & services)...")
    from app.tools.image_to_prompt.services import rename_images_to_standard_format
    test_rename_dir = Path(tempfile.mkdtemp(prefix="test_rename_"))
    try:
        (test_rename_dir / "zebra.png").write_bytes(b"\x89PNGdummy")
        (test_rename_dir / "apple.jpg").write_bytes(b"\xFF\xD8\xFFdummy")
        (test_rename_dir / "apple.txt").write_text("apple prompt", encoding="utf-8")
        (test_rename_dir / "mango.webp").write_bytes(b"RIFFdummy")

        r_rename = client.post("/tools/image-to-prompt/rename", data={"folder": str(test_rename_dir)})
        assert r_rename.status_code == 200
        rename_res = r_rename.json()
        assert rename_res["status"] == "ok"
        assert rename_res["count"] == 3

        # apple -> image-1.jpg, mango -> image-2.webp, zebra -> image-3.png
        assert (test_rename_dir / "image-1.jpg").exists()
        assert (test_rename_dir / "image-1.txt").exists()
        assert (test_rename_dir / "image-1.txt").read_text(encoding="utf-8") == "apple prompt"
        assert (test_rename_dir / "image-2.webp").exists()
        assert (test_rename_dir / "image-3.png").exists()
        print("   -> OK! Đã đổi tên thành công thành image-1.jpg, image-2.webp, image-3.png và di chuyển file txt tương ứng.")
    finally:
        shutil.rmtree(test_rename_dir, ignore_errors=True)

    print("16. Kiểm tra parse 5 gợi ý tiêu đề SEO tiếng Brazil & format Title: <list title> Prompt: <prompt>...")
    sample_5_titles_output = (
        "Title:\n"
        "1. Retrato de uma mulher elegante olhando suavemente para a câmera em iluminação dourada\n"
        "2. Foto Editorial de uma mulher feminina com olhar lateral pensativo em cenário urbano\n"
        "3. Foto Executiva de uma mulher elegante com postura confiante em escritório contemporâneo\n"
        "4. Retrato de uma mulher feminina em close-up com luz suave e sombras dramáticas\n"
        "5. Foto Editorial de uma mulher elegante com vestido sofisticado e fundo desfocado\n\n"
        "Prompt:\n"
        "Uma fotografia profissional de altíssima resolução com proporção 4:5. O rosto e os traços faciais devem ser estritamente baseados na imagem de referência anexada.\n"
        "Aspect ratio: 4:5. --ar 4:5"
    )
    p_5 = parse_title_and_prompt(sample_5_titles_output)
    assert "Retrato de uma mulher elegante" in p_5["title"]
    assert "5. Foto Editorial de uma mulher elegante" in p_5["title"]
    assert p_5["title"].count("\n") == 4  # 5 lines
    assert "imagem de referência anexada" in p_5["prompt"]
    assert "--ar 4:5" in p_5["prompt"]
    print("   -> OK! parse_title_and_prompt bóc tách chính xác 5 tiêu đề SEO chuẩn format và prompt chi tiết.")

    print("17. Kiểm tra ép tỷ lệ ảnh mục tiêu (target_aspect_ratio='4:5') ghi đè tỷ lệ ảnh gốc (2:3)...")
    from app.tools.image_to_prompt.services import apply_aspect_ratio_to_prompt
    raw_prompt = "Foto profissional de alta resolução. Aspect ratio: 2:3. --ar 2:3"
    fixed_prompt = apply_aspect_ratio_to_prompt(raw_prompt, aspect_ratio="4:5", mode="both")
    assert "--ar 4:5" in fixed_prompt
    assert "Aspect ratio: 4:5" in fixed_prompt
    assert "2:3" not in fixed_prompt
    print("   -> OK! Target aspect ratio 4:5 đã thay thế hoàn toàn và ghi đè 2:3 thành công.")

    print("18. Kiểm tra danh sách model và quality tạo ảnh OpenAI (gpt-image)...")
    from app.tools.image_to_prompt.services import (
        DEFAULT_IMAGE_MODEL,
        DEFAULT_IMAGE_QUALITY,
        IMAGE_MODEL_NAMES,
        IMAGE_QUALITY_NAMES,
        save_result_image,
    )
    assert DEFAULT_IMAGE_MODEL == "gpt-image-2.5-flare"
    assert DEFAULT_IMAGE_QUALITY == "medium"
    assert "gpt-image-2.6-flare" in IMAGE_MODEL_NAMES
    assert "gpt-image-2.6-sunburst" in IMAGE_MODEL_NAMES
    assert "gpt-image-2.5-sunburst" in IMAGE_MODEL_NAMES
    assert "low" in IMAGE_QUALITY_NAMES and "high" in IMAGE_QUALITY_NAMES
    print("   -> OK! Model mặc định là gpt-image-2.5-flare, quality mặc định là medium.")

    print("19. Kiểm tra hàm lưu ảnh kết quả (save_result_image) dạng image-1-result.xxx...")
    test_img_path = temp_dir / "image-1.jpg"
    test_img_path.write_bytes(b"\xFF\xD8\xFF\xE0dummy_jpg_1")
    buf_res = io.BytesIO()
    Image.new("RGB", (100, 100), color="purple").save(buf_res, format="JPEG")
    saved_img = save_result_image(buf_res.getvalue(), test_img_path)
    assert saved_img.name == "image-1-result.jpg"
    assert saved_img.exists()
    print("   -> OK! Đã lưu chính xác file ảnh kết quả thành image-1-result.jpg.")

    print("20. Kiểm tra quy trình tạo ảnh qua OpenAI (Mock API) trong process_image_file...")
    import asyncio
    from app.tools.image_to_prompt.services import PromptConfig, process_image_file
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_prompt_gen, patch(
        "app.tools.image_to_prompt.services.generate_image_openai",
        new_callable=AsyncMock,
    ) as mock_img_gen:
        mock_prompt_gen.return_value = {
            "title": "1. Retrato de uma mulher elegante",
            "prompt": "Prompt gerado em português do Brasil",
        }
        mock_img_gen.return_value = buf_res.getvalue()

        cfg_with_img = PromptConfig(
            generate_image=True,
            image_model="gpt-image-2.5-flare",
            image_quality="medium",
            openai_api_key="sk-test-key",
            overwrite=True,
        )
        res_img_proc = asyncio.run(process_image_file(test_img_path, cfg_with_img))
        assert res_img_proc["status"] == "ok"
        assert res_img_proc["result_image"] == "image-1-result.jpg"
        assert (test_img_path.parent / "image-1-result.jpg").exists()
    print("   -> OK! process_image_file với generate_image=True gọi đúng generate_image_openai và lưu image-1-result.")

    print("21. Kiểm tra cấu hình chung hệ thống (/settings) có trường OpenAI API Key và Base URL...")
    r_settings = client.get("/settings")
    assert r_settings.status_code == 200
    assert "system_openai_api_key" in r_settings.text or "openai_api_key" in r_settings.text
    assert "system_openai_base_url" in r_settings.text or "openai_base_url" in r_settings.text

    from app.core import settings_store as ss
    sys_b = ss.get_block("system")
    assert "openai_api_key" in sys_b
    assert "openai_base_url" in sys_b
    print("   -> OK! Cấu hình chung hệ thống (/settings) đã tích hợp đầy đủ OpenAI API Key và OpenAI Base URL.")

    print("22. Kiểm tra màn hình image-to-prompt đã bỏ ô nhập OpenAI API Key và URL, tự động lấy từ config...")
    r_page = client.get("/tools/image-to-prompt")
    assert r_page.status_code == 200
    assert 'id="openai-api-key"' not in r_page.text
    assert 'id="openai-base-url"' not in r_page.text
    assert "OpenAI API Key & Base URL được tự động lấy từ Cấu hình chung hệ thống" in r_page.text
    assert "image_to_prompt_folder" in r_page.text
    assert 'id="image-ref-folder"' in r_page.text
    assert "image_to_prompt_ref_folder" in r_page.text
    print("   -> OK! Màn hình image-to-prompt đã loại bỏ hoàn toàn ô nhập Key/URL, có input thư mục ảnh tham chiếu và lưu localStorage.")

    print("23. Kiểm tra tính năng chọn ngẫu nhiên ảnh tham chiếu từ thư mục khi tạo ảnh OpenAI...")
    from app.tools.image_to_prompt.services import get_random_reference_image
    ref_dir = temp_dir / "face_references"
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / "face1.jpg").write_bytes(buf_res.getvalue())
    (ref_dir / "face2.png").write_bytes(buf_res.getvalue())

    # Test get_random_reference_image
    rand_ref_path, rand_ref_bytes = get_random_reference_image(str(ref_dir))
    assert rand_ref_path.name in ("face1.jpg", "face2.png")
    assert len(rand_ref_bytes) > 0

    # Test process_image_file with reference_folder
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_prompt_gen2, patch(
        "app.tools.image_to_prompt.services.generate_image_openai",
        new_callable=AsyncMock,
    ) as mock_img_gen2:
        mock_prompt_gen2.return_value = {
            "title": "1. Retrato de uma mulher elegante",
            "prompt": "Prompt test random reference",
        }
        mock_img_gen2.return_value = buf_res.getvalue()

        test_img_path2 = temp_dir / "image-2.jpg"
        test_img_path2.write_bytes(buf_res.getvalue())

        cfg_ref = PromptConfig(
            generate_image=True,
            image_model="gpt-image-2.5-flare",
            reference_folder=str(ref_dir),
            openai_api_key="sk-test-key",
            overwrite=True,
        )
        res_ref_proc = asyncio.run(process_image_file(test_img_path2, cfg_ref))
        assert res_ref_proc["status"] == "ok"
        assert res_ref_proc["ref_image"] in ("face1.jpg", "face2.png")
        assert mock_img_gen2.called
        # Check that reference_image_bytes was passed to generate_image_openai
        called_kwargs = mock_img_gen2.call_args.kwargs
        assert called_kwargs.get("reference_image_bytes") is not None
        assert called_kwargs.get("reference_image_filename") in ("face1.jpg", "face2.png")
    print("   -> OK! process_image_file đã tự động lấy ngẫu nhiên 1 ảnh từ thư mục tham chiếu và truyền cho OpenAI API.")

    print("24. Kiểm tra tính năng tạo và trả về slug URL chuẩn SEO...")
    from app.tools.image_to_prompt.services import (
        slugify_text,
        generate_slugs_from_title_text,
        parse_title_and_prompt,
    )
    # Test slugify_text
    assert slugify_text("Retrato de Uma Mulher Elegante") == "retrato-de-uma-mulher-elegante"
    assert slugify_text("Café na Praça São Paulo - Edição Especial!") == "cafe-na-praca-sao-paulo-edicao-especial"
    assert slugify_text("Đường dẫn tĩnh cho ảnh đại diện") == "duong-dan-tinh-cho-anh-dai-dien"

    # Test multiline titles slug generation
    sample_5_titles = (
        "1. Mulher Elegante em Paris\n"
        "2. Retrato Urbano de Moda\n"
        "3. Estilo de Rua Sofisticado\n"
        "4. Ensaio Fotográfico Noturno\n"
        "5. Beleza Natural em Foco"
    )
    slugs_gen = generate_slugs_from_title_text(sample_5_titles)
    slug_lines = slugs_gen.split("\n")
    assert len(slug_lines) == 5
    assert slug_lines[0] == "1. mulher-elegante-em-paris"
    assert slug_lines[1] == "2. retrato-urbano-de-moda"
    assert slug_lines[4] == "5. beleza-natural-em-foco"

    # Test parsing when Slug section is explicitly provided
    ai_output_with_slug = f"Title:\n{sample_5_titles}\n\nSlug:\n{slugs_gen}\n\nPrompt:\nA beautiful portrait photograph."
    parsed_with_slug = parse_title_and_prompt(ai_output_with_slug)
    assert parsed_with_slug["slug"] == slugs_gen
    assert parsed_with_slug["prompt"] == "A beautiful portrait photograph."

    # Test parsing when Slug is missing (fallback auto-generation)
    ai_output_no_slug = f"Title:\n{sample_5_titles}\n\nPrompt:\nA beautiful portrait photograph."
    parsed_no_slug = parse_title_and_prompt(ai_output_no_slug)
    assert parsed_no_slug["slug"] == slugs_gen

    # Test process_image_file saving Slug into .txt and returning slug
    test_img_path3 = temp_dir / "image-3.jpg"
    test_img_path3.write_bytes(buf_res.getvalue())
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_p3:
        mock_p3.return_value = {
            "title": sample_5_titles,
            "slug": slugs_gen,
            "prompt": "Portrait test prompt",
            "aspect_ratio": "4:5",
            "width": 800,
            "height": 1000,
        }
        cfg3 = PromptConfig(overwrite=True)
        res3 = asyncio.run(process_image_file(test_img_path3, cfg3))
        assert res3["status"] == "ok"
        assert res3["slug"] == slugs_gen
        txt3_content = (temp_dir / "image-3.txt").read_text(encoding="utf-8")
        assert "Title:\n" in txt3_content
        assert "Slug:\n" in txt3_content
        assert "Prompt:\n" in txt3_content
        assert "1. mulher-elegante-em-paris" in txt3_content

    # Test /tools/image-to-prompt/single returning slug
    with patch(
        "app.tools.image_to_prompt.services.generate_prompt_for_image_bytes",
        new_callable=AsyncMock,
    ) as mock_p_single:
        mock_p_single.return_value = {
            "title": "Retrato Clássico",
            "slug": "retrato-classico",
            "prompt": "Test prompt single",
            "aspect_ratio": "4:5",
        }
        r_single = client.post(
            "/tools/image-to-prompt/single",
            files={"file": ("test.jpg", buf_res.getvalue(), "image/jpeg")},
        )
        assert r_single.status_code == 200
        single_json = r_single.json()
        assert single_json["title"] == "Retrato Clássico"
        assert single_json["slug"] == "retrato-classico"

    # Test template contains slug UI elements
    r_page_slug = client.get("/tools/image-to-prompt")
    assert r_page_slug.status_code == 200
    assert 'id="single-result-slug"' in r_page_slug.text
    assert 'id="copy-single-slug-btn"' in r_page_slug.text
    assert "Copy Slug" in r_page_slug.text
    print("   -> OK! Đã sinh slug chuẩn SEO, lưu vào file .txt, trả về qua API và hiển thị trên giao diện.")

    print("25. Kiểm tra tính năng cấu trúc Prompt theo từng phần xuống dòng (Subject, Pose, Background...)...")
    from app.tools.image_to_prompt.services import format_prompt_sections
    # Test format_prompt_sections splits sections on one line into separate lines
    single_line_prompt = (
        "Subject: Um homem elegante, traços baseados na imagem de referência anexada. "
        "Pose: Em pé com a mão esquerda no bolso da calça. "
        "Expression: Olhar confiante e sereno olhando diretamente para a câmera. "
        "Clothing: Terno de alfaiataria azul marinho com camisa branca. "
        "Background: Salão moderno com grandes janelas de vidro e bokeh suave. "
        "Lighting: Luz suave natural vinda da lateral com sombras delicadas. "
        "Camera: Plano médio na altura dos olhos com lente de 85mm. "
        "Style: Fotografia profissional e hiper-realista em alta resolução."
    )
    formatted = format_prompt_sections(single_line_prompt)
    lines_fmt = formatted.split("\n")
    assert len(lines_fmt) == 8
    assert lines_fmt[0].startswith("Subject:")
    assert lines_fmt[1].startswith("Pose:")
    assert lines_fmt[2].startswith("Expression:")
    assert lines_fmt[3].startswith("Clothing:")
    assert lines_fmt[4].startswith("Background:")
    assert lines_fmt[5].startswith("Lighting:")
    assert lines_fmt[6].startswith("Camera:")
    assert lines_fmt[7].startswith("Style:")

    # Test DEFAULT_SYSTEM_PROMPT is empty (removed as requested)
    from app.tools.image_to_prompt.services import DEFAULT_SYSTEM_PROMPT
    assert DEFAULT_SYSTEM_PROMPT == ""

    # Test batch template preserves whitespace-pre-wrap for multiline prompts
    assert 'whitespace-pre-wrap leading-relaxed select-all max-h-60 overflow-y-auto' in r_page_slug.text
    print("   -> OK! Prompt đã được cấu trúc rõ ràng theo từng phần xuống dòng (Subject, Pose, Expression, Clothing, Background, Lighting, Camera, Style).")

finally:
    shutil.rmtree(temp_dir, ignore_errors=True)

print("\n=== TẤT CẢ SMOKE TESTS CHO TOOL IMAGE TO PROMPT ĐỀU THÀNH CÔNG! ===")
