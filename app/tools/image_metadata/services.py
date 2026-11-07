"""Services for reading, editing, stripping, and writing Image Metadata (EXIF, GPS, XP tags)."""
from __future__ import annotations

import base64
from datetime import datetime
import io
import json
from pathlib import Path
import re
from typing import Any
import zipfile

import aiohttp
from PIL import ExifTags, Image

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3:latest"

DEFAULT_AI_METADATA_PROMPT = """Bạn là một chuyên gia biên tập dữ liệu ảnh (EXIF/Metadata) chuyên nghiệp.
Dựa trên chủ đề hoặc yêu cầu của người dùng sau đây, hãy sáng tạo và trả về DUY NHẤT một đối tượng JSON (không kèm bất kỳ lời dẫn hay văn bản giải thích nào) theo cấu trúc sau:
{
  "title": "Tiêu đề ảnh ngắn gọn, ấn tượng, chuẩn SEO",
  "description": "Đoạn mô tả chi tiết, giàu cảm xúc về bối cảnh, ánh sáng, góc chụp và câu chuyện của bức ảnh (khoảng 2-3 câu)",
  "keywords": "từ khóa 1; từ khóa 2; từ khóa 3; từ khóa 4; từ khóa 5",
  "author": "Tên tác giả hoặc người chụp",
  "copyright": "Bản quyền (ví dụ: © 2026 Bản quyền tác giả)",
  "rating": 5,
  "software": "18.1",
  "latitude": 21.028511,
  "longitude": 105.854444,
  "altitude": 15,
  "camera_make": "Apple",
  "camera_model": "iPhone 15 Pro",
  "lens_model": "iPhone 15 Pro back triple camera 6.78mm f/1.78",
  "iso": 100,
  "f_number": 1.8,
  "focal_length": 24
}

Quy tắc quan trọng:
1. Nếu chủ đề nhắc tới một địa danh cụ thể (ví dụ: Hồ Gươm, Đà Nẵng, Hội An, Paris, Tokyo...), hãy cung cấp tọa độ latitude và longitude thực tế tương ứng. Nếu là ảnh trừu tượng/không rõ địa điểm, hãy để null cho latitude và longitude.
2. Giữ giá trị software mặc định là '18.1' trừ khi yêu cầu chỉ định phần mềm khác.
3. Trả về DUY NHẤT mã JSON hợp lệ.

Yêu cầu/Chủ đề của người dùng:
{topic}
"""

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

# Windows XP tag IDs
XP_TITLE_TAG = 0x9C9B
XP_COMMENT_TAG = 0x9C9C
XP_AUTHOR_TAG = 0x9C9D
XP_KEYWORDS_TAG = 0x9C9E
XP_SUBJECT_TAG = 0x9C9F

# Rating tags
RATING_TAG = 0x4746         # 0 - 5
RATING_PERCENT_TAG = 0x4749 # 0 - 99

# Lens model tag
LENS_MODEL_TAG = 0xA434


def _decode_xp_tag(val: Any) -> str:
    """Safely decode Windows XP UTF-16LE tags."""
    if isinstance(val, bytes):
        try:
            return val.decode("utf-16le", errors="ignore").rstrip("\x00").strip()
        except Exception:
            return ""
    if isinstance(val, str):
        return val.strip()
    return ""


def _decode_str_tag(val: Any) -> str:
    """Safely decode standard EXIF string / bytes tags."""
    if isinstance(val, bytes):
        for enc in ("utf-8", "latin-1", "ascii"):
            try:
                return val.decode(enc).rstrip("\x00").strip()
            except UnicodeDecodeError:
                continue
        return ""
    if isinstance(val, str):
        return val.rstrip("\x00").strip()
    return str(val) if val is not None else ""


def _decode_user_comment(val: Any) -> str:
    """Decode UserComment tag handling prefix codes (UNICODE, ASCII, etc.)."""
    if isinstance(val, bytes):
        if val.startswith(b"UNICODE\x00"):
            return val[8:].decode("utf-16le", errors="ignore").rstrip("\x00").strip()
        if val.startswith(b"ASCII\x00\x00\x00"):
            return val[8:].decode("ascii", errors="ignore").rstrip("\x00").strip()
        return _decode_str_tag(val)
    if isinstance(val, str):
        return val.strip()
    return ""


def _format_datetime_to_html(exif_dt: str) -> str:
    """Convert EXIF 'YYYY:MM:DD HH:MM:SS' to HTML 'YYYY-MM-DDTHH:MM:SS'."""
    if not exif_dt or not isinstance(exif_dt, str):
        return ""
    try:
        parts = exif_dt.strip().split(" ")
        if len(parts) == 2:
            date_part = parts[0].replace(":", "-")
            return f"{date_part}T{parts[1]}"
    except Exception:
        pass
    return exif_dt


def _format_html_to_exif_datetime(html_dt: str) -> str:
    """Convert HTML 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DDTHH:MM:SS' to EXIF 'YYYY:MM:DD HH:MM:SS'."""
    if not html_dt or not isinstance(html_dt, str):
        return ""
    try:
        cleaned = html_dt.strip().replace("T", " ")
        if len(cleaned) == 16:  # YYYY-MM-DD HH:MM
            cleaned += ":00"
        parts = cleaned.split(" ")
        if len(parts) == 2:
            date_part = parts[0].replace("-", ":")
            return f"{date_part} {parts[1]}"
    except Exception:
        pass
    return html_dt


def _dms_to_dd(dms: Any, ref: str) -> float | None:
    """Convert EXIF DMS tuple (degrees, minutes, seconds) to decimal degrees."""
    if not dms or len(dms) < 3:
        return None
    try:
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        dd = d + (m / 60.0) + (s / 3600.0)
        if ref.upper() in ("S", "W"):
            dd = -dd
        return round(dd, 6)
    except Exception:
        return None


def _dd_to_dms(dd: float) -> tuple[float, float, float]:
    """Convert decimal degrees to (degrees, minutes, seconds) tuple."""
    abs_dd = abs(dd)
    deg = int(abs_dd)
    rem = (abs_dd - deg) * 60.0
    minutes = int(rem)
    seconds = round((rem - minutes) * 60.0, 4)
    return (float(deg), float(minutes), float(seconds))


def make_thumbnail_data_url(img: Image.Image, max_size: int = 240) -> str:
    """Create a lightweight base64 thumbnail data URL for instant UI preview."""
    try:
        thumb = img.copy()
        thumb.thumbnail((max_size, max_size))
        out = io.BytesIO()
        if thumb.mode in ("RGBA", "LA", "P"):
            thumb.save(out, format="PNG")
            mime = "image/png"
        else:
            thumb.save(out, format="JPEG", quality=75)
            mime = "image/jpeg"
        b64 = base64.b64encode(out.getvalue()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""


def extract_metadata(image_bytes: bytes, filename: str = "") -> dict[str, Any]:
    """Extract metadata, EXIF, GPS, camera details, and image info from raw image bytes."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        width, height = img.size
        img_format = img.format or "JPEG"
        thumb_url = make_thumbnail_data_url(img)

        exif = img.getexif()

    # Raw EXIF readable tags for inspector
    raw_tags: dict[str, str] = {}
    for tag_id, val in exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, hex(tag_id))
        if isinstance(val, bytes):
            if len(val) > 40:
                raw_tags[tag_name] = f"[{len(val)} bytes]"
            else:
                raw_tags[tag_name] = _decode_xp_tag(val) or _decode_str_tag(val)
        else:
            raw_tags[tag_name] = str(val)

    # 1. Title & Description
    xp_title = _decode_xp_tag(exif.get(XP_TITLE_TAG))
    xp_subject = _decode_xp_tag(exif.get(XP_SUBJECT_TAG))
    xp_comment = _decode_xp_tag(exif.get(XP_COMMENT_TAG))
    img_desc = _decode_str_tag(exif.get(ExifTags.Base.ImageDescription))

    title = xp_title or img_desc
    description = xp_subject or xp_comment or (img_desc if xp_title else "")

    # 2. Author, Copyright, Keywords, Software
    xp_author = _decode_xp_tag(exif.get(XP_AUTHOR_TAG))
    artist = _decode_str_tag(exif.get(ExifTags.Base.Artist))
    author = xp_author or artist

    copyright_text = _decode_str_tag(exif.get(ExifTags.Base.Copyright))
    keywords = _decode_xp_tag(exif.get(XP_KEYWORDS_TAG))
    software = _decode_str_tag(exif.get(ExifTags.Base.Software))

    # 3. Rating
    rating_val = exif.get(RATING_TAG)
    if rating_val is None:
        percent = exif.get(RATING_PERCENT_TAG)
        if percent is not None:
            try:
                p = int(percent)
                rating_val = 5 if p >= 90 else 4 if p >= 75 else 3 if p >= 50 else 2 if p >= 25 else 1 if p > 0 else 0
            except Exception:
                rating_val = 0
    try:
        rating = int(rating_val) if rating_val is not None else 0
    except Exception:
        rating = 0

    # 4. Dates
    date_modified_raw = _decode_str_tag(exif.get(ExifTags.Base.DateTime))
    date_modified = _format_datetime_to_html(date_modified_raw)

    # Sub IFDs
    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    date_taken_raw = _decode_str_tag(exif_ifd.get(ExifTags.Base.DateTimeOriginal))
    date_digitized_raw = _decode_str_tag(exif_ifd.get(ExifTags.Base.DateTimeDigitized))

    date_taken = _format_datetime_to_html(date_taken_raw)
    date_digitized = _format_datetime_to_html(date_digitized_raw)

    # User comment in Exif IFD
    if not description:
        user_cmt = _decode_user_comment(exif_ifd.get(ExifTags.Base.UserComment))
        if user_cmt:
            description = user_cmt

    # Camera & Lens info
    camera_make = _decode_str_tag(exif.get(ExifTags.Base.Make))
    camera_model = _decode_str_tag(exif.get(ExifTags.Base.Model))
    lens_model = _decode_str_tag(exif_ifd.get(LENS_MODEL_TAG))

    iso = exif_ifd.get(ExifTags.Base.ISOSpeedRatings)
    try:
        iso = int(iso) if iso is not None else None
    except Exception:
        iso = None

    f_number = exif_ifd.get(ExifTags.Base.FNumber)
    try:
        f_number = float(f_number) if f_number is not None else None
    except Exception:
        f_number = None

    focal_length = exif_ifd.get(ExifTags.Base.FocalLength)
    try:
        focal_length = float(focal_length) if focal_length is not None else None
    except Exception:
        focal_length = None

    exp_time = exif_ifd.get(ExifTags.Base.ExposureTime)
    exposure_time_str = ""
    if exp_time is not None:
        try:
            exp_val = float(exp_time)
            if exp_val > 0 and exp_val < 1:
                exposure_time_str = f"1/{round(1 / exp_val)}"
            else:
                exposure_time_str = f"{exp_val}s"
        except Exception:
            exposure_time_str = str(exp_time)

    # 5. GPS
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
    lat_ref = gps_ifd.get(ExifTags.GPS.GPSLatitudeRef)
    raw_lat = gps_ifd.get(ExifTags.GPS.GPSLatitude)
    lon_ref = gps_ifd.get(ExifTags.GPS.GPSLongitudeRef)
    raw_lon = gps_ifd.get(ExifTags.GPS.GPSLongitude)
    raw_alt = gps_ifd.get(ExifTags.GPS.GPSAltitude)
    alt_ref = gps_ifd.get(ExifTags.GPS.GPSAltitudeRef)

    lat_ref_str = _decode_str_tag(lat_ref)
    lon_ref_str = _decode_str_tag(lon_ref)

    latitude = _dms_to_dd(raw_lat, lat_ref_str) if (raw_lat and lat_ref_str) else None
    longitude = _dms_to_dd(raw_lon, lon_ref_str) if (raw_lon and lon_ref_str) else None

    altitude = None
    if raw_alt is not None:
        try:
            alt_val = float(raw_alt)
            if alt_ref == 1 or str(alt_ref) == "1":
                alt_val = -alt_val
            altitude = round(alt_val, 2)
        except Exception:
            altitude = None

    has_gps = bool(latitude is not None and longitude is not None)

    return {
        "filename": filename,
        "file_size": len(image_bytes),
        "format": img_format,
        "width": width,
        "height": height,
        "thumbnail_data_url": thumb_url,
        "title": title,
        "description": description,
        "author": author,
        "copyright": copyright_text,
        "keywords": keywords,
        "rating": rating,
        "software": software,
        "date_taken": date_taken,
        "date_digitized": date_digitized,
        "date_modified": date_modified,
        "has_gps": has_gps,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "camera_make": camera_make,
        "camera_model": camera_model,
        "lens_model": lens_model,
        "iso": iso,
        "f_number": f_number,
        "focal_length": focal_length,
        "exposure_time": exposure_time_str,
        "raw_tags": raw_tags,
    }


def update_metadata(
    image_bytes: bytes,
    meta: dict[str, Any],
    clear_gps: bool = False,
    clear_all: bool = False,
) -> tuple[bytes, str]:
    """Write updated metadata to image bytes and return (output_bytes, mime_type)."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        img_format = img.format or "JPEG"
        save_format = img_format.upper()
        if save_format in ("JPG", "JPE"):
            save_format = "JPEG"
        elif save_format in ("TIF",):
            save_format = "TIFF"

        # Determine MIME type
        mime_map = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "TIFF": "image/tiff",
        }
        mime_type = mime_map.get(save_format, "image/jpeg")

        # If user selected strip all metadata
        if clear_all:
            out_clean = io.BytesIO()
            clean_img = img.copy()
            if save_format == "JPEG":
                if clean_img.mode in ("RGBA", "P"):
                    clean_img = clean_img.convert("RGB")
                clean_img.save(out_clean, format="JPEG", quality=98, subsampling=0)
            elif save_format == "PNG":
                clean_img.save(out_clean, format="PNG", optimize=True)
            elif save_format == "WEBP":
                clean_img.save(out_clean, format="WEBP", quality=95)
            elif save_format == "TIFF":
                clean_img.save(out_clean, format="TIFF")
            else:
                clean_img.save(out_clean, format=save_format)
            return out_clean.getvalue(), mime_type

        # Get existing or create fresh Exif
        exif = img.getexif()

        # 1. Update Base / XP Tags
        title = meta.get("title", "").strip()
        description = meta.get("description", "").strip()
        author = meta.get("author", "").strip()
        copyright_val = meta.get("copyright", "").strip()
        keywords = meta.get("keywords", "").strip()
        software = meta.get("software", "").strip()
        camera_make = meta.get("camera_make", "").strip()
        camera_model = meta.get("camera_model", "").strip()
        date_modified_html = meta.get("date_modified", "").strip()

        # Title
        if title:
            exif[XP_TITLE_TAG] = title.encode("utf-16le")
            exif[ExifTags.Base.ImageDescription] = title
        else:
            exif.pop(XP_TITLE_TAG, None)
            if not description:
                exif.pop(ExifTags.Base.ImageDescription, None)

        # Description
        if description:
            exif[XP_SUBJECT_TAG] = description.encode("utf-16le")
            exif[XP_COMMENT_TAG] = description.encode("utf-16le")
            if not title:
                exif[ExifTags.Base.ImageDescription] = description
        else:
            exif.pop(XP_SUBJECT_TAG, None)
            exif.pop(XP_COMMENT_TAG, None)

        # Author / Artist
        if author:
            exif[XP_AUTHOR_TAG] = author.encode("utf-16le")
            exif[ExifTags.Base.Artist] = author
        else:
            exif.pop(XP_AUTHOR_TAG, None)
            exif.pop(ExifTags.Base.Artist, None)

        # Copyright
        if copyright_val:
            exif[ExifTags.Base.Copyright] = copyright_val
        else:
            exif.pop(ExifTags.Base.Copyright, None)

        # Keywords
        if keywords:
            exif[XP_KEYWORDS_TAG] = keywords.encode("utf-16le")
        else:
            exif.pop(XP_KEYWORDS_TAG, None)

        # Software
        if software:
            exif[ExifTags.Base.Software] = software
        else:
            exif.pop(ExifTags.Base.Software, None)

        # Camera Make & Model
        if camera_make:
            exif[ExifTags.Base.Make] = camera_make
        else:
            exif.pop(ExifTags.Base.Make, None)

        if camera_model:
            exif[ExifTags.Base.Model] = camera_model
        else:
            exif.pop(ExifTags.Base.Model, None)

        # Date Modified
        if date_modified_html:
            exif[ExifTags.Base.DateTime] = _format_html_to_exif_datetime(date_modified_html)

        # Rating
        rating = meta.get("rating")
        if rating is not None and str(rating).isdigit():
            r = max(0, min(5, int(rating)))
            exif[RATING_TAG] = r
            percent_map = {0: 0, 1: 1, 2: 25, 3: 50, 4: 75, 5: 99}
            exif[RATING_PERCENT_TAG] = percent_map.get(r, 0)

        # 2. Update Exif IFD
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)

        date_taken_html = meta.get("date_taken", "").strip()
        if date_taken_html:
            exif_ifd[ExifTags.Base.DateTimeOriginal] = _format_html_to_exif_datetime(date_taken_html)
        else:
            exif_ifd.pop(ExifTags.Base.DateTimeOriginal, None)

        date_digitized_html = meta.get("date_digitized", "").strip()
        if date_digitized_html:
            exif_ifd[ExifTags.Base.DateTimeDigitized] = _format_html_to_exif_datetime(date_digitized_html)
        else:
            exif_ifd.pop(ExifTags.Base.DateTimeDigitized, None)

        lens_model = meta.get("lens_model", "").strip()
        if lens_model:
            exif_ifd[LENS_MODEL_TAG] = lens_model
        else:
            exif_ifd.pop(LENS_MODEL_TAG, None)

        iso = meta.get("iso")
        if iso is not None and str(iso).strip().isdigit():
            exif_ifd[ExifTags.Base.ISOSpeedRatings] = int(iso)
        else:
            exif_ifd.pop(ExifTags.Base.ISOSpeedRatings, None)

        f_num = meta.get("f_number")
        if f_num is not None and str(f_num).strip():
            try:
                exif_ifd[ExifTags.Base.FNumber] = float(f_num)
            except Exception:
                pass

        focal = meta.get("focal_length")
        if focal is not None and str(focal).strip():
            try:
                exif_ifd[ExifTags.Base.FocalLength] = float(focal)
            except Exception:
                pass

        # Also store description into UserComment if provided
        if description:
            try:
                exif_ifd[ExifTags.Base.UserComment] = b"UNICODE\x00" + description.encode("utf-16le")
            except Exception:
                pass

        exif[ExifTags.IFD.Exif] = exif_ifd

        # 3. Update GPS Info IFD
        if clear_gps:
            # Clear all GPS tags
            exif.pop(ExifTags.IFD.GPSInfo, None)
        else:
            lat_str = str(meta.get("latitude", "")).strip()
            lon_str = str(meta.get("longitude", "")).strip()
            alt_str = str(meta.get("altitude", "")).strip()

            if lat_str and lon_str:
                try:
                    lat_val = float(lat_str)
                    lon_val = float(lon_str)

                    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                    gps_ifd[ExifTags.GPS.GPSVersionID] = b"\x02\x03\x00\x00"

                    # Latitude
                    lat_dms = _dd_to_dms(lat_val)
                    gps_ifd[ExifTags.GPS.GPSLatitudeRef] = "N" if lat_val >= 0 else "S"
                    gps_ifd[ExifTags.GPS.GPSLatitude] = lat_dms

                    # Longitude
                    lon_dms = _dd_to_dms(lon_val)
                    gps_ifd[ExifTags.GPS.GPSLongitudeRef] = "E" if lon_val >= 0 else "W"
                    gps_ifd[ExifTags.GPS.GPSLongitude] = lon_dms

                    # Altitude
                    if alt_str:
                        alt_val = float(alt_str)
                        gps_ifd[ExifTags.GPS.GPSAltitudeRef] = 0 if alt_val >= 0 else 1
                        gps_ifd[ExifTags.GPS.GPSAltitude] = abs(alt_val)
                    else:
                        gps_ifd.pop(ExifTags.GPS.GPSAltitude, None)
                        gps_ifd.pop(ExifTags.GPS.GPSAltitudeRef, None)

                    exif[ExifTags.IFD.GPSInfo] = gps_ifd
                except (ValueError, TypeError):
                    pass
            elif not lat_str and not lon_str and meta.get("remove_gps_if_empty"):
                exif.pop(ExifTags.IFD.GPSInfo, None)

        out = io.BytesIO()
        save_img = img.copy()

        # Save preserving highest fidelity
        if save_format == "JPEG":
            if save_img.mode in ("RGBA", "P"):
                save_img = save_img.convert("RGB")
            save_img.save(out, format="JPEG", quality=98, subsampling=0, exif=exif)
        elif save_format == "PNG":
            save_img.save(out, format="PNG", exif=exif, optimize=True)
        elif save_format == "WEBP":
            save_img.save(out, format="WEBP", quality=95, exif=exif)
        elif save_format == "TIFF":
            save_img.save(out, format="TIFF", exif=exif)
        else:
            save_img.save(out, format=save_format, exif=exif)

        return out.getvalue(), mime_type


def create_zip_archive(files: list[tuple[str, bytes]]) -> bytes:
    """Create a ZIP archive containing multiple processed images."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, data in files:
            zf.writestr(fname, data)
    return zip_buffer.getvalue()


def _clean_json_text(text: str) -> str:
    """Strip markdown code fence ```json ... ``` or extract outermost JSON object."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()
    return text


def _normalize_ai_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize and normalize fields returned from Ollama JSON."""
    out: dict[str, Any] = {}
    out["title"] = str(data.get("title", "")).strip()
    out["description"] = str(data.get("description", "")).strip()
    out["keywords"] = str(data.get("keywords", "")).strip()
    out["author"] = str(data.get("author", "")).strip()
    out["copyright"] = str(data.get("copyright", "")).strip()
    out["software"] = str(data.get("software", "")).strip() or "18.1"

    # Rating
    try:
        r = int(data.get("rating", 5))
        out["rating"] = max(0, min(5, r))
    except Exception:
        out["rating"] = 5

    # Coordinates
    lat = data.get("latitude")
    lon = data.get("longitude")
    alt = data.get("altitude")

    try:
        out["latitude"] = float(lat) if lat is not None and str(lat).strip() not in ("", "null", "None") else None
    except Exception:
        out["latitude"] = None

    try:
        out["longitude"] = float(lon) if lon is not None and str(lon).strip() not in ("", "null", "None") else None
    except Exception:
        out["longitude"] = None

    try:
        out["altitude"] = float(alt) if alt is not None and str(alt).strip() not in ("", "null", "None") else None
    except Exception:
        out["altitude"] = None

    # Camera
    out["camera_make"] = str(data.get("camera_make", "")).strip()
    out["camera_model"] = str(data.get("camera_model", "")).strip()
    out["lens_model"] = str(data.get("lens_model", "")).strip()

    try:
        iso = data.get("iso")
        out["iso"] = int(iso) if iso is not None and str(iso).strip().isdigit() else None
    except Exception:
        out["iso"] = None

    try:
        f_num = data.get("f_number")
        out["f_number"] = float(f_num) if f_num is not None and str(f_num).strip() else None
    except Exception:
        out["f_number"] = None

    try:
        focal = data.get("focal_length")
        out["focal_length"] = float(focal) if focal is not None and str(focal).strip() else None
    except Exception:
        out["focal_length"] = None

    return out


async def list_ollama_models(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout_seconds: float = 4.0) -> list[str]:
    """Return available Ollama models or default fallbacks if unreachable."""
    url = base_url.rstrip("/") + "/api/tags"
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    names = [m["name"] for m in models if isinstance(m, dict) and m.get("name")]
                    if names:
                        return sorted(names)
    except Exception:
        pass
    return ["llama3:latest", "qwen3.8:latest", "llama3.2-vision:11b"]


async def generate_ai_metadata(
    topic: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    prompt_template: str = "",
    image_bytes: bytes | None = None,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Send user topic + prompt template to Ollama, parse returned JSON and normalize."""
    url = base_url.rstrip("/") + "/api/generate"
    template = prompt_template.strip() or DEFAULT_AI_METADATA_PROMPT
    full_prompt = template.replace("{topic}", topic.strip())

    payload: dict[str, Any] = {
        "model": model,
        "prompt": full_prompt,
        "format": "json",
        "stream": False,
    }

    if image_bytes:
        b64_img = base64.b64encode(image_bytes).decode("ascii")
        payload["images"] = [b64_img]

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                err_text = await resp.text()
                raise RuntimeError(f"Ollama báo lỗi (HTTP {resp.status}): {err_text}")
            result = await resp.json()
            raw_response = result.get("response", "")

    cleaned_json = _clean_json_text(raw_response)
    try:
        parsed = json.loads(cleaned_json)
    except Exception as exc:
        raise ValueError(f"Không thể phân tích định dạng JSON từ Ollama: {exc}\nNội dung trả về: {raw_response[:300]}") from exc

    return _normalize_ai_metadata(parsed)

