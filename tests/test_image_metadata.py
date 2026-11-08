import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import zipfile
from fastapi.testclient import TestClient
from PIL import Image

from main import app
from app.tools.image_metadata import services

client = TestClient(app)

def create_test_image(format="JPEG", size=(200, 150)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(100, 150, 200))
    img.save(buf, format=format)
    return buf.getvalue()

def test_page_loads():
    response = client.get("/tools/image-metadata")
    assert response.status_code == 200
    assert "Metadata" in response.text
    assert "leaflet" in response.text

def test_read_metadata():
    img_bytes = create_test_image("JPEG")
    files = {"file": ("sample.jpg", img_bytes, "image/jpeg")}
    response = client.post("/tools/image-metadata/read", files=files)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["width"] == 200
    assert data["height"] == 150
    assert data["format"] == "JPEG"

def test_save_metadata():
    img_bytes = create_test_image("JPEG")
    files = {"file": ("sample.jpg", img_bytes, "image/jpeg")}
    form_data = {
        "title": "Hồ Tây Chiều Thu",
        "description": "Hoàng hôn lãng mạn tại Hồ Tây Hà Nội",
        "author": "Nhiếp Ảnh Gia",
        "copyright": "Bản quyền 2026",
        "keywords": "hanoi; hotay; hoanghon",
        "rating": "5",
        "software": "Personal-Tool",
        "date_taken": "2026-11-07T08:30:00",
        "latitude": "21.0583",
        "longitude": "105.8236",
        "altitude": "12",
        "camera_make": "Sony",
        "camera_model": "ILCE-7M4",
        "custom_filename": "hotay_updated.jpg",
    }
    response = client.post("/tools/image-metadata/save", files=files, data=form_data)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    updated_bytes = response.content

    # Verify extracted metadata from the output
    extracted = services.extract_metadata(updated_bytes, "hotay_updated.jpg")
    assert extracted["title"] == "Hồ Tây Chiều Thu"
    assert extracted["description"] == "Hoàng hôn lãng mạn tại Hồ Tây Hà Nội"
    assert extracted["author"] == "Nhiếp Ảnh Gia"
    assert extracted["rating"] == 5
    assert extracted["has_gps"] is True
    assert abs(extracted["latitude"] - 21.0583) < 0.001
    assert abs(extracted["longitude"] - 105.8236) < 0.001

def test_batch_metadata():
    img1 = create_test_image("JPEG")
    img2 = create_test_image("PNG")

    files = [
        ("files", ("photo1.jpg", img1, "image/jpeg")),
        ("files", ("photo2.png", img2, "image/png")),
    ]
    form_data = {
        "title": "Batch Photo Title",
        "author": "Batch Author",
        "latitude": "16.0544",
        "longitude": "108.2022",
    }
    response = client.post("/tools/image-metadata/save-batch", files=files, data=form_data)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    # Check zip contents
    zip_buf = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buf, "r") as zf:
        namelist = zf.namelist()
        assert "photo1.jpg" in namelist
        assert "photo2.png" in namelist

def test_dashboard_shows_new_tool():
    response = client.get("/")
    assert response.status_code == 200
    assert "/tools/image-metadata" in response.text

def test_ollama_endpoints():
    # 1. Models list
    resp = client.get("/tools/image-metadata/ollama-models")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert "models" in resp.json()

    # 2. Empty topic validation
    resp_empty = client.post("/tools/image-metadata/generate-ai", data={"topic": ""})
    assert resp_empty.status_code == 400

    # 3. Check language options rendered on metadata page
    resp_page = client.get("/tools/image-metadata")
    assert resp_page.status_code == 200
    assert "ai-language-select" in resp_page.text
    assert "Tiếng Việt (Vietnamese)" in resp_page.text


def test_ai_prompt_language_formatting():
    import asyncio
    from unittest.mock import AsyncMock, patch

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "response": '{"title": "Title in English", "description": "Description in English", "keywords": "test; eng", "software": "18.1"}'
    })

    captured_payload = {}

    class MockSession:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        def post(self, url, json=None):
            captured_payload.update(json or {})
            class ContextManager:
                async def __aenter__(self):
                    return mock_resp
                async def __aexit__(self, *args):
                    pass
            return ContextManager()

    with patch("aiohttp.ClientSession", MockSession):
        res = asyncio.run(services.generate_ai_metadata(
            topic="A photo of mountains",
            model="llama3:latest",
            language="en"
        ))
        assert res["title"] == "Title in English"
        assert "English" in captured_payload.get("prompt", "")
        assert "A photo of mountains" in captured_payload.get("prompt", "")


def test_folder_scan_and_ai_process():
    import json
    import tempfile
    from unittest.mock import AsyncMock, patch

    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        # Create test images
        img_bytes = create_test_image("JPEG")
        (td / "img1.jpg").write_bytes(img_bytes)
        (td / "img2.jpg").write_bytes(img_bytes)
        (td / "notes.txt").write_text("not an image")
        
        # Subfolder results should be ignored during scan
        results_dir = td / "results"
        results_dir.mkdir()
        (results_dir / "already_processed.jpg").write_bytes(img_bytes)

        # 1. Test scan service
        scanned = services.scan_folder_images(td, recursive=True)
        names = [p.name for p in scanned]
        assert "img1.jpg" in names
        assert "img2.jpg" in names
        assert "already_processed.jpg" not in names
        assert "notes.txt" not in names

        # 2. Test scan endpoint
        resp_scan = client.get(f"/tools/image-metadata/folder-scan?folder={td}")
        assert resp_scan.status_code == 200
        scan_data = resp_scan.json()
        assert scan_data["count"] == 2
        assert scan_data["results_dir"] == str(td / "results")

        # 3. Test folder AI process endpoint with mock Ollama
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "response": '{"title": "Đỉnh Fansipan Hùng Vĩ", "description": "Mây bồng bềnh", "keywords": "fansipan; sapa", "author": "Tu Nguyen", "rating": 5, "latitude": 22.3033, "longitude": 103.7753}'
        })

        class MockSession:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def post(self, url, json=None):
                class ContextManager:
                    async def __aenter__(self):
                        return mock_resp
                    async def __aexit__(self, *args):
                        pass
                return ContextManager()

        with patch("aiohttp.ClientSession", MockSession):
            resp_proc = client.post(
                "/tools/image-metadata/process-folder-ai",
                data={
                    "folder": str(td),
                    "topic": "Chuyến đi Sa Pa",
                    "model": "llama3:latest",
                    "language": "vi",
                    "latitude": "22.3033",
                    "longitude": "103.7753",
                }
            )
            assert resp_proc.status_code == 200

            # Parse NDJSON events
            lines = [line.strip() for line in resp_proc.text.split("\n") if line.strip()]
            events = [json.loads(l) for l in lines]
            event_types = [e["type"] for e in events]
            assert "start" in event_types
            assert "file_start" in event_types
            assert "file_done" in event_types
            assert "done" in event_types

            # Verify files were created in results/
            out1 = results_dir / "img1.jpg"
            out2 = results_dir / "img2.jpg"
            assert out1.exists()
            assert out2.exists()

            # Verify metadata on output file
            meta1 = services.extract_metadata(out1.read_bytes(), "img1.jpg")
            assert meta1["title"] == "Đỉnh Fansipan Hùng Vĩ"
            assert meta1["has_gps"] is True
            assert abs(meta1["latitude"] - 22.3033) < 0.001
            assert abs(meta1["longitude"] - 103.7753) < 0.001
            # Datetime should be set to current time
            assert meta1["date_taken"] != ""


if __name__ == "__main__":
    test_page_loads()
    print("✓ test_page_loads passed")
    test_read_metadata()
    print("✓ test_read_metadata passed")
    test_save_metadata()
    print("✓ test_save_metadata passed")
    test_batch_metadata()
    print("✓ test_batch_metadata passed")
    test_dashboard_shows_new_tool()
    print("✓ test_dashboard_shows_new_tool passed")
    test_ollama_endpoints()
    print("✓ test_ollama_endpoints passed")
    test_ai_prompt_language_formatting()
    print("✓ test_ai_prompt_language_formatting passed")
    test_folder_scan_and_ai_process()
    print("✓ test_folder_scan_and_ai_process passed")
    print("\nALL IMAGE METADATA TESTS PASSED SUCCESSFULLY!")
