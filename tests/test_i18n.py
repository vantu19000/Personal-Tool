"""Tests for internationalization (i18n) module, routing, and settings screen."""
from fastapi.testclient import TestClient

from app.core.i18n import (
    DEFAULT_LOCALE,
    get_current_locale,
    get_supported_locales,
    is_locale_supported,
    load_translations,
    set_current_locale,
    t,
)
from main import app


def test_i18n_basic_translations():
    load_translations()

    # Test Vietnamese (default)
    set_current_locale("vi")
    assert get_current_locale() == "vi"
    assert t("sidebar.dashboard") == "Tổng quan"
    assert t("topbar.search_placeholder") == "Tìm kiếm công cụ, ví dụ: pdf, srt, hash..."
    assert t("settings.title") == "Cấu hình hệ thống"
    assert t("settings.blocks.system.fields.home_title.label") == "Tiêu đề trang chủ"

    # Test English
    set_current_locale("en")
    assert get_current_locale() == "en"
    assert t("sidebar.dashboard") == "Dashboard"
    assert t("topbar.search_placeholder") == "Search tools, e.g., pdf, srt, hash..."
    assert t("settings.title") == "System Settings"
    assert t("settings.blocks.system.fields.home_title.label") == "Homepage Title"

    # Reset back to default
    set_current_locale("vi")


def test_i18n_fallback_and_formatting():
    # Formatting
    msg = t("settings.save_error", locale="en", error="Invalid input")
    assert "Invalid input" in msg

    # Fallback to default
    assert t("non.existent.key", default="Custom Default") == "Custom Default"
    assert t("non.existent.key") == "non.existent.key"


def test_supported_locales():
    locales = get_supported_locales()
    codes = [l["code"] for l in locales]
    assert "vi" in codes
    assert "en" in codes
    assert is_locale_supported("vi") is True
    assert is_locale_supported("en") is True
    assert is_locale_supported("fr") is False


def test_web_language_detection_and_switch():
    client = TestClient(app)

    # 1. Default request should be Vietnamese
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'lang="vi"' in resp.text
    assert "Tổng quan" in resp.text

    # 2. Switch via query param ?lang=en
    resp_en = client.get("/?lang=en")
    assert resp_en.status_code == 200
    assert 'lang="en"' in resp_en.text
    assert "Dashboard" in resp_en.text
    assert "app_lang=en" in resp_en.headers.get("set-cookie", "")

    # 3. Request with cookie app_lang=en
    client.cookies.set("app_lang", "en")
    resp_cookie = client.get("/")
    assert resp_cookie.status_code == 200
    assert 'lang="en"' in resp_cookie.text
    assert "Dashboard" in resp_cookie.text

    # 4. Set language endpoint API
    switch_resp = client.get("/api/set-language/vi", follow_redirects=False)
    assert switch_resp.status_code == 303
    assert "app_lang=vi" in switch_resp.headers.get("set-cookie", "")


def test_settings_screen_i18n():
    client = TestClient(app)

    # 1. Settings in Vietnamese
    resp_vi = client.get("/settings?lang=vi")
    assert resp_vi.status_code == 200
    assert "Cấu hình hệ thống" in resp_vi.text
    assert "Tiêu đề trang chủ" in resp_vi.text
    assert "Lưu tất cả thay đổi" in resp_vi.text
    assert "Thời gian chờ tối đa (giây)" in resp_vi.text

    # 2. Settings in English
    resp_en = client.get("/settings?lang=en")
    assert resp_en.status_code == 200
    assert "System Settings" in resp_en.text
    assert "Homepage Title" in resp_en.text
    assert "Save All Changes" in resp_en.text
    assert "Max Timeout (seconds)" in resp_en.text


def test_image_to_prompt_screen_i18n():
    client = TestClient(app)

    # 1. Image to prompt in Vietnamese
    resp_vi = client.get("/tools/image-to-prompt?lang=vi")
    assert resp_vi.status_code == 200
    assert "Dịch hàng loạt thư mục" in resp_vi.text
    assert "Thử nghiệm 1 ảnh" in resp_vi.text
    assert "Cấu hình dịch ngược ảnh trong thư mục" in resp_vi.text
    assert "Bắt đầu dịch ngược ảnh → Prompt" in resp_vi.text

    # 2. Image to prompt in English
    resp_en = client.get("/tools/image-to-prompt?lang=en")
    assert resp_en.status_code == 200
    assert "Batch Folder Processing" in resp_en.text
    assert "Single Image Test" in resp_en.text
    assert "Batch Folder Reverse-Prompt Configuration" in resp_en.text
    assert "Start Reverse Prompting Image → Prompt" in resp_en.text


def test_srt_translator_screen_i18n():
    client = TestClient(app)

    # 1. SRT Translator in Vietnamese
    resp_vi = client.get("/tools/srt-translator?lang=vi")
    assert resp_vi.status_code == 200
    assert "Dịch từng file phụ đề" in resp_vi.text
    assert "Dịch hàng loạt (toàn bộ thư mục)" in resp_vi.text
    assert "Thư mục nguồn (chứa file .srt)" in resp_vi.text
    assert "Dịch phụ đề ↓" in resp_vi.text

    # 2. SRT Translator in English
    resp_en = client.get("/tools/srt-translator?lang=en")
    assert resp_en.status_code == 200
    assert "Single Subtitle File Translation" in resp_en.text
    assert "Batch Translation (Entire Folder)" in resp_en.text
    assert "Source Folder (containing .srt files)" in resp_en.text
    assert "Translate Subtitles ↓" in resp_en.text


def test_pdf_to_md_screen_i18n():
    client = TestClient(app)

    # 1. PDF to Markdown in Vietnamese
    resp_vi = client.get("/tools/pdf-to-md?lang=vi")
    assert resp_vi.status_code == 200
    assert "Chuyển đổi từng file PDF" in resp_vi.text
    assert "Chuyển đổi theo thư mục (hàng loạt)" in resp_vi.text
    assert "Số trang mỗi file Markdown" in resp_vi.text
    assert "Chuyển đổi sang Markdown" in resp_vi.text

    # 2. PDF to Markdown in English
    resp_en = client.get("/tools/pdf-to-md?lang=en")
    assert resp_en.status_code == 200
    assert "Single PDF Conversion" in resp_en.text
    assert "Batch Folder Conversion" in resp_en.text
    assert "Pages per Markdown file" in resp_en.text
    assert "Convert to Markdown" in resp_en.text


def test_image_compressor_screen_i18n():
    client = TestClient(app)

    # 1. Image Compressor in Vietnamese
    resp_vi = client.get("/tools/image-compressor?lang=vi")
    assert resp_vi.status_code == 200
    assert "Nén Ảnh Tối Ưu" in resp_vi.text
    assert "Tỷ lệ chất lượng nén ảnh" in resp_vi.text
    assert "Tab 1: Tải lên nhiều file" in resp_vi.text
    assert "Tab 2: Nén theo thư mục" in resp_vi.text
    assert "Bắt đầu nén ảnh" in resp_vi.text
    assert "Chọn thư mục…" in resp_vi.text

    # 2. Image Compressor in English
    resp_en = client.get("/tools/image-compressor?lang=en")
    assert resp_en.status_code == 200
    assert "Smart Image Compressor" in resp_en.text
    assert "Compression Quality Ratio" in resp_en.text
    assert "Tab 1: Upload Multiple Files" in resp_en.text
    assert "Tab 2: Batch Folder Compression" in resp_en.text
    assert "Start Compression" in resp_en.text
    assert "Browse folder…" in resp_en.text


def test_slufy_screen_i18n():
    client = TestClient(app)

    # 1. Slufy in Vietnamese
    resp_vi = client.get("/tools/slufy?lang=vi")
    assert resp_vi.status_code == 200
    assert "Slufy" in resp_vi.text
    assert "Văn bản cần tạo slug" in resp_vi.text
    assert "Kết quả Slug" in resp_vi.text
    assert "Slug được tự động tạo ngay khi bạn gõ phím" in resp_vi.text

    # 2. Slufy in English
    resp_en = client.get("/tools/slufy?lang=en")
    assert resp_en.status_code == 200
    assert "Slufy" in resp_en.text
    assert "Text to slugify" in resp_en.text
    assert "Slug Result" in resp_en.text
    assert "Slug is generated automatically in real time as you type" in resp_en.text


def test_guid_generator_screen_i18n():
    client = TestClient(app)

    # 1. GUID Generator in Vietnamese
    resp_vi = client.get("/tools/guid-generator?lang=vi")
    assert resp_vi.status_code == 200
    assert "GUID Generator" in resp_vi.text
    assert "Số lượng chuỗi GUID" in resp_vi.text
    assert "Tạo GUID" in resp_vi.text
    assert "Sao chép tất cả" in resp_vi.text

    # 2. GUID Generator in English
    resp_en = client.get("/tools/guid-generator?lang=en")
    assert resp_en.status_code == 200
    assert "GUID Generator" in resp_en.text
    assert "Quantity of GUID strings" in resp_en.text
    assert "Generate GUID" in resp_en.text
    assert "Copy All" in resp_en.text


def test_hash_calculator_screen_i18n():
    client = TestClient(app)

    # 1. Hash Calculator in Vietnamese
    resp_vi = client.get("/tools/hash-calculator?lang=vi")
    assert resp_vi.status_code == 200
    assert "Hash Calculator" in resp_vi.text
    assert "Chuỗi văn bản" in resp_vi.text
    assert "Thuật toán băm" in resp_vi.text
    assert "Tính mã băm" in resp_vi.text
    assert "Sao chép tất cả" in resp_vi.text

    # 2. Hash Calculator in English
    resp_en = client.get("/tools/hash-calculator?lang=en")
    assert resp_en.status_code == 200
    assert "Hash Calculator" in resp_en.text
    assert "Text strings" in resp_en.text
    assert "Hash Algorithms" in resp_en.text
    assert "Compute Hashes" in resp_en.text
    assert "Copy All" in resp_en.text


def test_text_counter_screen_i18n():
    client = TestClient(app)

    # 1. Text Counter in Vietnamese
    resp_vi = client.get("/tools/text-counter?lang=vi")
    assert resp_vi.status_code == 200
    assert "Text Counter" in resp_vi.text
    assert "Số từ" in resp_vi.text
    assert "Số câu" in resp_vi.text
    assert "Số ký tự" in resp_vi.text
    assert "Số đoạn văn" in resp_vi.text
    assert "Xoá hết" in resp_vi.text

    # 2. Text Counter in English
    resp_en = client.get("/tools/text-counter?lang=en")
    assert resp_en.status_code == 200
    assert "Text Counter" in resp_en.text
    assert "Words" in resp_en.text
    assert "Sentences" in resp_en.text
    assert "Characters" in resp_en.text
    assert "Paragraphs" in resp_en.text
    assert "Clear all" in resp_en.text


if __name__ == "__main__":
    test_i18n_basic_translations()
    test_i18n_fallback_and_formatting()
    test_supported_locales()
    test_web_language_detection_and_switch()
    test_settings_screen_i18n()
    test_image_to_prompt_screen_i18n()
    test_srt_translator_screen_i18n()
    test_pdf_to_md_screen_i18n()
    test_image_compressor_screen_i18n()
    test_slufy_screen_i18n()
    test_guid_generator_screen_i18n()
    test_hash_calculator_screen_i18n()
    test_text_counter_screen_i18n()
    print("All i18n tests passed successfully!")
