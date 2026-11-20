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
    assert 'insertVariableIntoBatchPrompt' in r_page.text
    assert '{output_language}' in r_page.text
    assert '{aspect_ratio}' in r_page.text


def test_prepare_prompt_all_template_variables():
    """Verify all template variables ({output_language}, {language}, {aspect_ratio}, {ratio}, {dimensions}, {width}, {height}, {character_description}) are correctly replaced."""
    from app.tools.image_to_prompt.services import prepare_prompt

    raw_template = (
        "Output: {output_language} | Short: {language}\n"
        "Ratio: {aspect_ratio} | Short Ratio: {ratio}\n"
        "Size: {width}x{height} | Dim: {dimensions} | Res: {resolution}\n"
        "Char: {character_description}"
    )

    result = prepare_prompt(
        prompt=raw_template,
        language="pt-BR",
        character_description="A stylish businesswoman",
        aspect_ratio="4:5",
        width=1080,
        height=1350,
    )

    assert "Output: Português - Brasil (Tiếng Bồ Đào Nha - Brazil) | Short: Português - Brasil (Tiếng Bồ Đào Nha - Brazil)" in result
    assert "Ratio: 4:5 | Short Ratio: 4:5" in result
    assert "Size: 1080x1350 | Dim: 1080x1350 | Res: 1080x1350" in result
    assert "Char: A stylish businesswoman" in result


def test_prompt_templates_variables_cheatsheet_rendered(client):
    """Verify Prompt Templates management page renders the Variables Reference Guide and buttons."""
    r = client.get("/tools/prompt-templates")
    assert r.status_code == 200
    assert "Danh sách các Biến hệ thống hỗ trợ trong Template" in r.text
    assert "{output_language}" in r.text
    assert "{aspect_ratio}" in r.text
    assert "{dimensions}" in r.text
    assert "{width}" in r.text
    assert "{height}" in r.text
    assert "{character_description}" in r.text
    assert "{seo_keywords}" in r.text
    assert "insertVariableIntoPrompt" in r.text


def test_prepare_prompt_seo_keywords_variable_and_injection():
    """Verify {seo_keywords} substitution and automatic injection if omitted from template."""
    from app.tools.image_to_prompt.services import prepare_prompt

    # Case A: Template contains {seo_keywords}
    template_with_seo = "Title: Foto | Keywords: {seo_keywords} | Alias: {keywords}\nPrompt: Studio portrait."
    res_a = prepare_prompt(
        prompt=template_with_seo,
        seo_keywords="ensaio feminino, moda executiva",
    )
    assert "Keywords: ensaio feminino, moda executiva | Alias: ensaio feminino, moda executiva" in res_a

    # Case B: Template does NOT contain {seo_keywords}, but seo_keywords is provided
    template_without_seo = "Title: Foto\nPrompt: Studio portrait."
    res_b = prepare_prompt(
        prompt=template_without_seo,
        seo_keywords="ensaio feminino, moda executiva",
    )
    assert "Yêu cầu Từ khóa SEO (SEO Keywords)" in res_b
    assert "ensaio feminino, moda executiva" in res_b

    # Case C: No seo_keywords provided
    res_c = prepare_prompt(
        prompt=template_without_seo,
        seo_keywords="",
    )
    assert "Yêu cầu Từ khóa SEO (SEO Keywords)" not in res_c


def test_image_to_prompt_seo_keywords_integration(client):
    """Verify Image to Prompt screen includes SEO keywords input and handles save-defaults."""
    r = client.get("/tools/image-to-prompt")
    assert r.status_code == 200
    assert 'id="batch-seo-keywords"' in r.text
    assert 'insertVariableIntoBatchPrompt(\'{seo_keywords}\')' in r.text

    # Test save-defaults saves seo_keywords
    res_save = client.post(
        "/tools/image-to-prompt/save-defaults",
        data={
            "model": "qwen3.8:latest",
            "language": "pt-BR",
            "seo_keywords": "ensaio feminino, foto profissional",
        },
    )
    assert res_save.status_code == 200
    assert res_save.json()["status"] == "ok"


def test_extract_prompt_when_prompt_section_is_first():
    """Verify parse_title_and_prompt extracts the exact prompt when format is Prompt -> Title -> Slug."""
    from app.tools.image_to_prompt.services import parse_title_and_prompt

    ai_output = (
        "Prompt:\n"
        "A stylish businesswoman in navy blue blazer, standing in an executive glass office.\n\n"
        "Title:\n"
        "1, Mulher de Sucesso no Escritorio\n"
        "2, Retrato Executivo Feminino\n\n"
        "Slug:\n"
        "1, mulher-de-sucesso-no-escritorio\n"
        "2, retrato-executivo-feminino"
    )

    parsed = parse_title_and_prompt(ai_output)
    # The prompt sent to chatgpt must be only the prompt content, excluding titles and slugs
    assert parsed["prompt"] == "A stylish businesswoman in navy blue blazer, standing in an executive glass office."
    assert "Title:" not in parsed["prompt"]
    assert "Slug:" not in parsed["prompt"]
    assert "Mulher de Sucesso" in parsed["title"]
    assert "1. mulher-de-sucesso-no-escritorio" in parsed["slug"]


