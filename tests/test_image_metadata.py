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
    print("\nALL IMAGE METADATA TESTS PASSED SUCCESSFULLY!")
