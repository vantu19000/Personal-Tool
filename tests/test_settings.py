"""Unit tests for Settings validation and persistence."""
import pytest
from fastapi.testclient import TestClient

from app.core import settings_store
from main import app


def test_settings_timeout_seconds_allows_12000():
    # Save 12000 for image_to_prompt
    res = settings_store.save_blocks({
        "image_to_prompt": {
            "timeout_seconds": 12000
        }
    })
    assert res["image_to_prompt"]["timeout_seconds"] == 12000
    assert settings_store.get_field("image_to_prompt", "timeout_seconds") == 12000

    # Reset back to default
    settings_store.save_blocks({
        "image_to_prompt": {
            "timeout_seconds": 1200
        }
    })


def test_settings_validation_error_format():
    with pytest.raises(settings_store.SettingsValidationError) as exc_info:
        settings_store.save_blocks({
            "image_to_prompt": {
                "timeout_seconds": 100000  # > 86400
            }
        })
    error_msg = str(exc_info.value)
    assert "Image to Prompt" in error_msg
    assert "timeout_seconds" in error_msg
    assert "86400" in error_msg


def test_settings_post_route():
    client = TestClient(app)
    # Post settings with 12000
    payload = {
        "system.home_title": "Test Title",
        "system.home_description": "Test Desc",
        "system.ollama_timeout_seconds": "12000",
        "image_to_prompt.timeout_seconds": "12000",
        "image_to_prompt.default_model": "qwen3.8:latest",
        "image_to_prompt.default_language": "pt-BR",
        "image_to_prompt.system_prompt": "Test system prompt valid length"
    }
    response = client.post("/settings", data=payload)
    assert response.status_code == 200
    assert "Đã lưu" in response.text or "Save" in response.text

    # Verify invalid value returns 400 with friendly error message and keeps field input
    bad_payload = payload.copy()
    bad_payload["image_to_prompt.timeout_seconds"] = "999999"
    resp_bad = client.post("/settings", data=bad_payload)
    assert resp_bad.status_code == 400
    assert "giá trị phải nhỏ hơn hoặc bằng 86400" in resp_bad.text
    # Check that candidate value is retained in HTML form
    assert 'value="999999"' in resp_bad.text
