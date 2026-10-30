"""Tests for internationalization (i18n) module and routing."""
from fastapi.testclient import TestClient

from app.core.i18n import (
    DEFAULT_LOCALE,
    get_current_locale,
    get_supported_locales,
    is_locale_supported,
    set_current_locale,
    t,
)
from main import app


def test_i18n_basic_translations():
    # Test Vietnamese (default)
    set_current_locale("vi")
    assert get_current_locale() == "vi"
    assert t("sidebar.dashboard") == "Tổng quan"
    assert t("topbar.search_placeholder") == "Tìm kiếm công cụ, ví dụ: pdf, srt, hash..."

    # Test English
    set_current_locale("en")
    assert get_current_locale() == "en"
    assert t("sidebar.dashboard") == "Dashboard"
    assert t("topbar.search_placeholder") == "Search tools, e.g., pdf, srt, hash..."

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


if __name__ == "__main__":
    test_i18n_basic_translations()
    test_i18n_fallback_and_formatting()
    test_supported_locales()
    test_web_language_detection_and_switch()
    print("All i18n tests passed successfully!")
