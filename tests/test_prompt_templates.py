"""Smoke and functional tests for Prompt Templates (MongoDB storage and Image-to-Prompt integration)."""
import asyncio
import os
import pytest
from fastapi.testclient import TestClient

from main import app
from app.prompt_templates.services import prompt_template_repo, INITIAL_TEMPLATES


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_initial_seeding_and_list():
    """Verify built-in templates are seeded and retrieved."""
    templates = asyncio.run(prompt_template_repo.get_all_templates())
    assert len(templates) >= 5
    default_tpl = next((t for t in templates if t.get("is_default")), None)
    assert default_tpl is not None
    assert "SEO" in default_tpl.get("name")


def test_template_crud_service():
    """Verify CRUD operations in PromptTemplateRepository."""
    # 1. Create
    new_tpl_data = {
        "name": "Test Fashion Lookbook",
        "description": "Mẫu test lookbook thời trang",
        "category": "Thời trang",
        "language": "en",
        "prompt_content": "Subject: Fashion model.\nPose: Walking.\nBackground: Studio.\nStyle: Clean 8k.",
        "is_default": False,
    }
    created = asyncio.run(prompt_template_repo.create_template(new_tpl_data))
    assert created["id"] > 0
    created_id = created["id"]
    assert created["name"] == "Test Fashion Lookbook"

    # 2. Read by ID
    fetched = asyncio.run(prompt_template_repo.get_template_by_id(created_id))
    assert fetched is not None
    assert fetched["name"] == "Test Fashion Lookbook"

    # 3. Update
    updated = asyncio.run(
        prompt_template_repo.update_template(created_id, {"description": "Updated description test"})
    )
    assert updated["description"] == "Updated description test"

    # 4. Set Default
    set_def = asyncio.run(prompt_template_repo.set_default_template(created_id))
    assert set_def["is_default"] is True
    # Verify previous default was unset
    tpl1 = asyncio.run(prompt_template_repo.get_template_by_id(1))
    if tpl1:
        assert tpl1.get("is_default") is False

    # 5. Delete
    deleted = asyncio.run(prompt_template_repo.delete_template(created_id))
    assert deleted is True
    assert asyncio.run(prompt_template_repo.get_template_by_id(created_id)) is None

    # Reset default template 1
    asyncio.run(prompt_template_repo.set_default_template(1))


def test_prompt_templates_screen_routes(client):
    """Verify HTML pages render successfully."""
    # /tools/prompt-templates
    r1 = client.get("/tools/prompt-templates")
    assert r1.status_code == 200
    assert "Kho Mẫu Prompt" in r1.text
    assert "template-modal" in r1.text
    assert "prompt-card-container" in r1.text or "template-card-container" in r1.text

    # Alias /prompt-templates
    r2 = client.get("/prompt-templates")
    assert r2.status_code == 200
    assert "Kho Mẫu Prompt" in r2.text


def test_api_list_and_get(client):
    """Verify /api/prompt-templates endpoints."""
    r_list = client.get("/api/prompt-templates")
    assert r_list.status_code == 200
    json_data = r_list.json()
    assert json_data["status"] == "ok"
    assert json_data["total"] >= 5

    # Test filtering by category
    r_cat = client.get("/api/prompt-templates?category=Chân dung")
    assert r_cat.status_code == 200
    assert len(r_cat.json()["data"]) >= 1

    # Test get single
    first_id = json_data["data"][0]["id"]
    r_single = client.get(f"/api/prompt-templates/{first_id}")
    assert r_single.status_code == 200
    assert r_single.json()["data"]["id"] == first_id


def test_api_create_update_delete(client):
    """Verify API CRUD lifecycle."""
    # Create via JSON
    payload = {
        "name": "API Test Template",
        "description": "Created via API test",
        "category": "Điện ảnh",
        "language": "pt-BR",
        "prompt_content": "Subject: Cinematic actor.\nPose: Looking away.\nLighting: Moody.",
        "is_default": False,
    }
    r_create = client.post("/api/prompt-templates", json=payload)
    assert r_create.status_code == 201
    created_obj = r_create.json()["data"]
    test_id = created_obj["id"]
    assert created_obj["name"] == "API Test Template"

    # Update via PUT
    r_update = client.put(f"/api/prompt-templates/{test_id}", json={"name": "API Test Template (Updated)"})
    assert r_update.status_code == 200
    assert r_update.json()["data"]["name"] == "API Test Template (Updated)"

    # Set Default
    r_def = client.post(f"/api/prompt-templates/{test_id}/set-default")
    assert r_def.status_code == 200
    assert r_def.json()["data"]["is_default"] is True

    # Delete
    r_del = client.delete(f"/api/prompt-templates/{test_id}")
    assert r_del.status_code == 200

    # Verify 404 after deletion
    r_after = client.get(f"/api/prompt-templates/{test_id}")
    assert r_after.status_code == 404

    # Reset default back to template 1
    client.post("/api/prompt-templates/1/set-default")


def test_image_to_prompt_template_selector_integration(client):
    """Verify Image to Prompt screen integrates the MongoDB prompt template selector."""
    r_page = client.get("/tools/image-to-prompt")
    assert r_page.status_code == 200
    assert 'id="prompt-template-select"' in r_page.text
    assert 'id="btn-apply-template"' in r_page.text
    assert 'id="btn-refresh-templates"' in r_page.text
    assert '/tools/prompt-templates' in r_page.text
    assert 'templatesCache' in r_page.text
