"""Business logic for the PDF → Markdown tool.

Supports:
1. Pure text PDFs.
2. Mixed text & image PDFs (extracts figures, diagrams, photos and embeds them into Markdown in visual reading order).
3. Scanned / image-only PDFs:
   - High-resolution scan image rendering fallback (ensuring no data is lost even without external OCR).
   - OCR via Tesseract (local PyMuPDF OCR).
   - AI Vision OCR via Google Gemini API (e.g. gemini-2.5-flash).
   - AI Vision OCR via Ollama multimodal models (e.g. llama3.2-vision, llava).
4. Chunking long documents into parts.
5. Packaging into zip (Markdown parts + images/ folder) or single .md with base64 inline images.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
import io
from pathlib import Path
import re
from typing import Any, Dict, Iterator, List, Optional, Sequence
import urllib.error
import urllib.request

MIN_PAGES_PER_FILE = 1
MAX_PAGES_PER_FILE = 500

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_VISION_MODEL = "llama3.2-vision"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

# Cho phép ký tự tiếng Việt (Unicode letters/digits) và gạch ngang;
# các ký tự khác (khoảng trắng, ký tự đặc biệt) đều được thay bằng "-".
_SAFE_NAME_RE = re.compile(r"[^\w\u00C0-\u024F-]+", re.UNICODE)


class PdfConversionError(ValueError):
    """Raised when a PDF cannot be converted to Markdown text."""


@dataclass
class ConversionOptions:
    """Options controlling PDF extraction and formatting."""

    pages_per_file: int = 10
    extract_images: bool = True
    image_embed_mode: str = "folder"  # "folder" | "base64"
    min_image_dimension: int = 35  # skip tiny icons / line separators (in px)
    ocr_mode: str = "auto"  # "auto" | "off" | "ollama" | "gemini"
    ollama_model: str = DEFAULT_OLLAMA_VISION_MODEL
    ollama_url: str = DEFAULT_OLLAMA_BASE_URL
    gemini_api_key: str = ""
    gemini_model: str = DEFAULT_GEMINI_MODEL


@dataclass
class ConversionResult:
    """Output of a PDF-to-Markdown conversion.

    Acts like a list of markdown part dicts for backward compatibility,
    while also exposing `images` and conversion statistics.
    """

    parts: List[Dict[str, Any]] = field(default_factory=list)
    images: Dict[str, bytes] = field(default_factory=dict)
    total_pages: int = 0
    scanned_pages: int = 0
    extracted_images_count: int = 0

    def __len__(self) -> int:
        return len(self.parts)

    def __getitem__(self, idx: Any) -> Any:
        return self.parts[idx]

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self.parts)


def _fitz():
    """Lazy import so the rest of the app still boots without PyMuPDF."""
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz  # fallback to legacy import name
        except ImportError as exc:  # pragma: no cover
            raise PdfConversionError(
                "Chưa cài PyMuPDF — chạy: pip install PyMuPDF"
            ) from exc
    return fitz


def _validate_pages_per_file(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise PdfConversionError(
            f"Số trang mỗi file phải là số nguyên (từ {MIN_PAGES_PER_FILE} "
            f"đến {MAX_PAGES_PER_FILE})."
        ) from exc
    if not (MIN_PAGES_PER_FILE <= n <= MAX_PAGES_PER_FILE):
        raise PdfConversionError(
            f"Số trang mỗi file phải từ {MIN_PAGES_PER_FILE} đến {MAX_PAGES_PER_FILE}."
        )
    return n


def _sanitize_stem(name: str) -> str:
    """Turn a file stem into a safe, readable filename fragment."""
    cleaned = _SAFE_NAME_RE.sub("-", name).strip("-")
    return cleaned or "document"


def _extract_image_bytes(doc: Any, xref: int) -> tuple[bytes, str]:
    """Extract raw image bytes and file extension from a PDF xref.

    Handles CMYK, alpha masks, and unusual colorspaces by rendering to RGB PNG.
    """
    fitz = _fitz()
    try:
        data = doc.extract_image(xref)
        img_bytes = data["image"]
        ext = data.get("ext", "png").lower()
        if ext == "jpx":
            ext = "jp2"
        # If smask or CMYK colorspace, render via Pixmap to ensure standard RGB PNG
        if (
            data.get("smask", 0) > 0
            or data.get("colorspace", 0) > 3
            or ext not in ("png", "jpeg", "jpg", "webp")
        ):
            pix = fitz.Pixmap(doc, xref)
            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            return pix.tobytes("png"), "png"
        return img_bytes, ext
    except Exception:
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n >= 5:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            return pix.tobytes("png"), "png"
        except Exception as exc:
            raise PdfConversionError(f"Không thể trích xuất ảnh xref={xref}: {exc}") from exc


def _ocr_with_tesseract(page: Any) -> Optional[str]:
    """Attempt local OCR using PyMuPDF / Tesseract."""
    try:
        tp = page.get_textpage_ocr(language="vie+eng")
        text = tp.extractText().strip()
        if text:
            return text
    except Exception:
        pass
    return None


def _ocr_with_gemini(
    image_bytes: bytes,
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
    timeout: float = 45.0,
) -> Optional[str]:
    """Call Google Gemini API to OCR a scanned document page into Markdown."""
    if not api_key:
        return None
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    b64_data = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Hãy chuyển đổi toàn bộ nội dung trong hình ảnh tài liệu này "
                            "sang định dạng Markdown chuẩn. "
                            "Giữ nguyên tiêu đề (#, ##), cấu trúc bảng biểu, danh sách và văn bản. "
                            "Không thêm lời chào, giải thích, không bọc trong ```markdown."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": b64_data,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text.startswith("```markdown"):
                        text = text[len("```markdown") :].strip()
                    elif text.startswith("```"):
                        text = text[3:].strip()
                    if text.endswith("```"):
                        text = text[:-3].strip()
                    return text
    except Exception:
        pass
    return None


def _ocr_with_ollama(
    image_bytes: bytes,
    model: str = DEFAULT_OLLAMA_VISION_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: float = 60.0,
) -> Optional[str]:
    """Call local Ollama multimodal/vision model to OCR an image into Markdown."""
    b64_data = base64.b64encode(image_bytes).decode("ascii")
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Hãy chuyển đổi toàn bộ nội dung trong hình ảnh tài liệu này sang định dạng Markdown. "
                    "Giữ nguyên cấu trúc, tiêu đề, bảng biểu và văn bản. Chỉ trả về nội dung Markdown."
                ),
                "images": [b64_data],
            }
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {}).get("content", "").strip()
            if msg.startswith("```markdown"):
                msg = msg[len("```markdown") :].strip()
            elif msg.startswith("```"):
                msg = msg[3:].strip()
            if msg.endswith("```"):
                msg = msg[:-3].strip()
            return msg or None
    except Exception:
        pass
    return None


def _process_page(
    doc: Any,
    page: Any,
    page_no: int,
    stem: str,
    options: ConversionOptions,
    images_bundle: Dict[str, bytes],
    xref_to_src: Dict[int, str],
    global_img_counter: List[int],
) -> tuple[str, bool]:
    """Extract text and images from a single page and format as Markdown.

    Returns:
        (page_markdown, is_scanned)
    """
    fitz = _fitz()

    # 1. Extract text blocks (block_type 0 = text)
    try:
        raw_blocks = page.get_text("blocks")
        text_blocks = [b for b in raw_blocks if b[6] == 0 and b[4].strip()]
    except Exception:
        text_blocks = []

    # 2. Extract image information if enabled
    valid_imgs = []
    if options.extract_images:
        try:
            raw_imgs = page.get_image_info(xrefs=True)
            for img in raw_imgs:
                xref = img.get("xref", 0)
                width = img.get("width", 0)
                height = img.get("height", 0)
                if (
                    xref > 0
                    and width >= options.min_image_dimension
                    and height >= options.min_image_dimension
                ):
                    valid_imgs.append(img)
        except Exception:
            valid_imgs = []

    # 3. Case A: Scanned / pure image page (no text layer)
    if not text_blocks:
        is_scanned = True
        try:
            pix = page.get_pixmap(dpi=150)
            png_bytes = pix.tobytes("png")
        except Exception:
            png_bytes = b""

        # Attempt OCR if requested
        ocr_text: Optional[str] = None
        if png_bytes and options.ocr_mode != "off":
            if options.ocr_mode in ("auto", "gemini") and options.gemini_api_key:
                ocr_text = _ocr_with_gemini(
                    png_bytes, options.gemini_api_key, options.gemini_model
                )
            if not ocr_text and options.ocr_mode in ("auto", "ollama"):
                ocr_text = _ocr_with_ollama(
                    png_bytes, options.ollama_model, options.ollama_url
                )
            if not ocr_text and options.ocr_mode in ("auto", "tesseract"):
                ocr_text = _ocr_with_tesseract(page)

        if ocr_text:
            md_lines = [
                "> ✦ *Trang scan — nội dung nhận diện tự động qua OCR:*\n",
                ocr_text,
            ]
            return "\n".join(md_lines), True

        # Fallback: Save scanned page as an image so the user retains visual content
        if png_bytes:
            if options.image_embed_mode == "base64":
                b64 = base64.b64encode(png_bytes).decode("ascii")
                img_src = f"data:image/png;base64,{b64}"
            else:
                img_name = f"{stem}_trang-{page_no}_scan.png"
                rel_path = f"images/{img_name}"
                images_bundle[rel_path] = png_bytes
                img_src = rel_path

            note = (
                "> ℹ️ *Trang scan hình ảnh (không có lớp text).* "
                "Cấu hình Gemini hoặc Ollama trong Cài đặt để tự động nhận diện chữ."
                if options.ocr_mode != "off"
                else "> ℹ️ *Trang scan hình ảnh.*"
            )
            md = f"{note}\n\n![Bản scan trang {page_no}]({img_src})\n"
            return md, True

        return "(trang trống — không có dữ liệu)", True

    # 4. Case B: Mixed content or text page
    # Combine text blocks and images into a single sequence ordered by visual flow
    elements: List[Dict[str, Any]] = []
    for b in text_blocks:
        elements.append(
            {
                "type": "text",
                "y": b[1],
                "x": b[0],
                "text": b[4].strip(),
            }
        )

    if options.extract_images:
        for img in valid_imgs:
            elements.append(
                {
                    "type": "image",
                    "y": img["bbox"][1],
                    "x": img["bbox"][0],
                    "xref": img["xref"],
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                }
            )

    # Sort elements: top-to-bottom (grouped by 12 points line band), then left-to-right
    elements.sort(key=lambda el: (round(el["y"] / 12) * 12, el["x"]))

    rendered_items: List[str] = []
    for el in elements:
        if el["type"] == "text":
            rendered_items.append(el["text"])
        elif el["type"] == "image":
            xref = el["xref"]
            if xref in xref_to_src:
                img_src = xref_to_src[xref]
            else:
                global_img_counter[0] += 1
                img_idx = global_img_counter[0]
                try:
                    img_bytes, ext = _extract_image_bytes(doc, xref)
                    if options.image_embed_mode == "base64":
                        b64 = base64.b64encode(img_bytes).decode("ascii")
                        img_src = f"data:image/{ext};base64,{b64}"
                    else:
                        img_name = f"{stem}_p{page_no}_img{img_idx}.{ext}"
                        img_src = f"images/{img_name}"
                        images_bundle[img_src] = img_bytes
                    xref_to_src[xref] = img_src
                except Exception:
                    continue

            rendered_items.append(f"\n![Hình ảnh (Trang {page_no})]({img_src})\n")

    return "\n\n".join(rendered_items), False


def _build_markdown_chunk(
    stem: str,
    page_markdowns: Sequence[str],
    start: int,
    end: int,
    has_scanned: bool = False,
) -> str:
    """Render a sequence of page markdowns into one chunk document."""
    scan_badge = " · Có trang scan/ảnh" if has_scanned else ""
    lines: List[str] = [
        f"# {stem} — trang {start}–{end}",
        "",
        f"> Tách tự động từ PDF · {len(page_markdowns)} trang "
        f"(trang {start} đến trang {end}){scan_badge}.",
        "",
    ]
    for offset, content in enumerate(page_markdowns):
        page_no = start + offset
        lines.append(f"## Trang {page_no}")
        lines.append("")
        lines.append(content.strip() or "(trang trống)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_parts_with_images(
    stem: str,
    page_markdowns: List[str],
    scanned_flags: List[bool],
    pages_per_file: int,
) -> List[Dict[str, Any]]:
    """Split page contents into chunk parts."""
    n = _validate_pages_per_file(pages_per_file)
    total = len(page_markdowns)
    parts: List[Dict[str, Any]] = []

    for start in range(0, total, n):
        chunk_texts = page_markdowns[start : start + n]
        chunk_scans = scanned_flags[start : start + n]
        chunk_start = start + 1
        chunk_end = start + len(chunk_texts)
        has_scanned = any(chunk_scans)
        content = _build_markdown_chunk(
            stem, chunk_texts, chunk_start, chunk_end, has_scanned
        )

        parts.append(
            {
                "name": f"{stem}_trang-{chunk_start}-{chunk_end}.md",
                "start": chunk_start,
                "end": chunk_end,
                "content": content,
                "chars": sum(len(t.strip()) for t in chunk_texts),
                "has_scanned": has_scanned,
            }
        )
    return parts


def convert_pdf_bytes(
    data: bytes,
    pages_per_file: int = 10,
    source_name: str = "document.pdf",
    *,
    extract_images: bool = True,
    image_embed_mode: str = "folder",
    min_image_dimension: int = 35,
    ocr_mode: str = "auto",
    ollama_model: str = DEFAULT_OLLAMA_VISION_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_BASE_URL,
    gemini_api_key: str = "",
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> ConversionResult:
    """Extract Markdown (and optionally images/OCR) from raw PDF bytes.

    Returns a :class:`ConversionResult` object which behaves both as a list of
    parts (for backwards compatibility) and contains the `images` mapping.
    """
    if not data:
        raise PdfConversionError("File PDF trống (0 byte).")

    options = ConversionOptions(
        pages_per_file=pages_per_file,
        extract_images=extract_images,
        image_embed_mode=image_embed_mode,
        min_image_dimension=min_image_dimension,
        ocr_mode=ocr_mode,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
    )

    fitz = _fitz()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfConversionError(f"Không mở được file PDF: {exc}") from exc

    try:
        if doc.needs_pass:
            raise PdfConversionError(
                "PDF đang được bảo mật bằng mật khẩu — không thể trích xuất."
            )
        total_pages = doc.page_count
        if total_pages == 0:
            raise PdfConversionError("PDF không có trang nào.")

        stem = _sanitize_stem(Path(source_name).stem)
        images_bundle: Dict[str, bytes] = {}
        xref_to_src: Dict[int, str] = {}
        global_img_counter: List[int] = [0]

        page_markdowns: List[str] = []
        scanned_flags: List[bool] = []

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_no = page_idx + 1
            md_content, is_scanned = _process_page(
                doc=doc,
                page=page,
                page_no=page_no,
                stem=stem,
                options=options,
                images_bundle=images_bundle,
                xref_to_src=xref_to_src,
                global_img_counter=global_img_counter,
            )
            page_markdowns.append(md_content)
            scanned_flags.append(is_scanned)

    finally:
        doc.close()

    parts = _render_parts_with_images(
        stem=stem,
        page_markdowns=page_markdowns,
        scanned_flags=scanned_flags,
        pages_per_file=pages_per_file,
    )

    return ConversionResult(
        parts=parts,
        images=images_bundle,
        total_pages=total_pages,
        scanned_pages=sum(scanned_flags),
        extracted_images_count=len(images_bundle),
    )


def convert_pdf_file(
    pdf_path: Path,
    pages_per_file: int = 10,
    *,
    extract_images: bool = True,
    image_embed_mode: str = "folder",
    min_image_dimension: int = 35,
    ocr_mode: str = "auto",
    ollama_model: str = DEFAULT_OLLAMA_VISION_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_BASE_URL,
    gemini_api_key: str = "",
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> ConversionResult:
    """Same as :func:`convert_pdf_bytes` but reads from a local file."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise PdfConversionError(f"File PDF không tồn tại: {pdf_path}")
    return convert_pdf_bytes(
        pdf_path.read_bytes(),
        pages_per_file=pages_per_file,
        source_name=pdf_path.name,
        extract_images=extract_images,
        image_embed_mode=image_embed_mode,
        min_image_dimension=min_image_dimension,
        ocr_mode=ocr_mode,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
    )


def convert_folder(
    source_folder: Path,
    output_folder: Path,
    pages_per_file: int = 10,
    *,
    extract_images: bool = True,
    image_embed_mode: str = "folder",
    min_image_dimension: int = 35,
    ocr_mode: str = "auto",
    ollama_model: str = DEFAULT_OLLAMA_VISION_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_BASE_URL,
    gemini_api_key: str = "",
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> Dict[str, Any]:
    """Convert every ``*.pdf`` in ``source_folder`` into Markdown and image assets.

    For each PDF the Markdown parts and image assets are written into:
    ``output_folder/<pdf-stem>/<part-name>.md``
    ``output_folder/<pdf-stem>/images/<img-name>``
    """
    src = Path(source_folder)
    out = Path(output_folder)
    if not src.exists() or not src.is_dir():
        raise PdfConversionError(f"Thư mục nguồn không tồn tại: {src}")
    out.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    if not pdfs:
        raise PdfConversionError(f"Không tìm thấy file .pdf nào trong: {src}")

    ok = 0
    failed = 0
    errors: List[Dict[str, str]] = []
    outputs: List[Dict[str, Any]] = []

    for pdf in pdfs:
        try:
            result = convert_pdf_file(
                pdf,
                pages_per_file=pages_per_file,
                extract_images=extract_images,
                image_embed_mode=image_embed_mode,
                min_image_dimension=min_image_dimension,
                ocr_mode=ocr_mode,
                ollama_model=ollama_model,
                ollama_url=ollama_url,
                gemini_api_key=gemini_api_key,
                gemini_model=gemini_model,
            )
            dest_dir = out / _sanitize_stem(pdf.stem)
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Write markdown parts
            for part in result.parts:
                (dest_dir / part["name"]).write_text(part["content"], encoding="utf-8")

            # Write extracted images if folder mode
            if result.images:
                for rel_path, img_bytes in result.images.items():
                    target_file = dest_dir / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_bytes(img_bytes)

            ok += 1
            outputs.append(
                {
                    "file": pdf.name,
                    "files": len(result.parts),
                    "images": len(result.images),
                    "scanned_pages": result.scanned_pages,
                    "output_path": str(dest_dir),
                }
            )
        except PdfConversionError as exc:
            failed += 1
            errors.append({"file": pdf.name, "error": str(exc)})
        except Exception as exc:
            failed += 1
            errors.append({"file": pdf.name, "error": f"Lỗi không xác định: {exc}"})

    return {
        "ok": ok,
        "failed": failed,
        "total": len(pdfs),
        "errors": errors,
        "outputs": outputs,
        "output_folder": str(out),
    }
