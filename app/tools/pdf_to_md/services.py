"""Business logic for the PDF → Markdown tool.

Strategy (first version — text-based PDFs only, no OCR):
- Open the PDF with PyMuPDF (``fitz``) and extract the text layer of every
  page via ``page.get_text("text")``.
- Group the pages into chunks of ``pages_per_file`` (default 10) and render
  each chunk as one Markdown document.
- PDFs without a text layer (scanned images) or protected with a password are
  rejected with a clear, user-facing error.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

MIN_PAGES_PER_FILE = 1
MAX_PAGES_PER_FILE = 500

# Cho phép ký tự tiếng Việt (Unicode letters/digits) và gạch ngang;
# các ký tự khác (khoảng trắng, ký tự đặc biệt) đều được thay bằng "-".
_SAFE_NAME_RE = re.compile(r"[^\w\u00C0-\u024F-]+", re.UNICODE)


class PdfConversionError(ValueError):
    """Raised when a PDF cannot be converted to Markdown text."""


def _fitz():
    """Lazy import so the rest of the app still boots without PyMuPDF."""
    try:
        import fitz  # PyMuPDF
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


def _build_markdown(stem: str, page_texts: Sequence[str], start: int, end: int) -> str:
    """Render one chunk of pages as a Markdown document.

    ``start`` / ``end`` are 1-based inclusive page numbers in the source PDF.
    """
    lines: List[str] = [
        f"# {stem} — trang {start}–{end}",
        "",
        f"> Tách tự động từ PDF · {len(page_texts)} trang "
        f"(trang {start} đến trang {end}).",
        "",
    ]
    for offset, text in enumerate(page_texts):
        page_no = start + offset
        lines.append(f"## Trang {page_no}")
        lines.append("")
        lines.append(text.strip() or "(trang trống — không có text)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_parts(stem: str, page_texts: List[str], pages_per_file: int) -> List[Dict[str, Any]]:
    """Split page texts into chunks and build the Markdown parts."""
    n = _validate_pages_per_file(pages_per_file)
    total = len(page_texts)
    parts: List[Dict[str, Any]] = []
    for start in range(0, total, n):
        chunk = page_texts[start : start + n]
        chunk_start = start + 1
        chunk_end = start + len(chunk)
        parts.append(
            {
                "name": f"{stem}_trang-{chunk_start}-{chunk_end}.md",
                "start": chunk_start,
                "end": chunk_end,
                "content": _build_markdown(stem, chunk, chunk_start, chunk_end),
                "chars": sum(len(t.strip()) for t in chunk),
            }
        )
    return parts


def convert_pdf_bytes(data: bytes, pages_per_file: int, source_name: str = "document.pdf") -> List[Dict[str, Any]]:
    """Extract text from raw PDF bytes and return the Markdown parts.

    Each part is ``{name, start, end, content, chars}`` where ``start``/``end``
    are the 1-based inclusive page range in the source PDF.
    """
    if not data:
        raise PdfConversionError("File PDF trống (0 byte).")
    fitz = _fitz()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfConversionError(f"Không mở được file PDF: {exc}") from exc

    try:
        if doc.needs_pass:
            raise PdfConversionError(
                "PDF đang được bảo mật bằng mật khẩu — không trích được text."
            )
        if doc.page_count == 0:
            raise PdfConversionError("PDF không có trang nào.")
        page_texts: List[str] = [page.get_text("text") for page in doc]
    finally:
        doc.close()

    if not any(t.strip() for t in page_texts):
        raise PdfConversionError(
            "PDF này không có lớp text (có thể là bản scan ảnh) — "
            "phiên bản đầu tiên chỉ hỗ trợ PDF text-based."
        )

    stem = _sanitize_stem(Path(source_name).stem)
    return _render_parts(stem, page_texts, pages_per_file)


def convert_pdf_file(pdf_path: Path, pages_per_file: int) -> List[Dict[str, Any]]:
    """Same as :func:`convert_pdf_bytes` but reads from a local file."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise PdfConversionError(f"File PDF không tồn tại: {pdf_path}")
    return convert_pdf_bytes(pdf_path.read_bytes(), pages_per_file, pdf_path.name)


def convert_folder(
    source_folder: Path, output_folder: Path, pages_per_file: int
) -> Dict[str, Any]:
    """Convert every ``*.pdf`` in ``source_folder``.

    For each PDF the Markdown parts are written into
    ``output_folder/<pdf-stem>/<part-name>``. Returns a summary dict with
    ``ok``, ``failed``, ``total``, ``errors``, ``outputs`` and
    ``output_folder``.
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
            parts = convert_pdf_file(pdf, pages_per_file)
            dest_dir = out / _sanitize_stem(pdf.stem)
            dest_dir.mkdir(parents=True, exist_ok=True)
            for part in parts:
                (dest_dir / part["name"]).write_text(part["content"], encoding="utf-8")
            ok += 1
            outputs.append(
                {
                    "file": pdf.name,
                    "files": len(parts),
                    "output_path": str(dest_dir),
                }
            )
        except PdfConversionError as exc:
            failed += 1
            errors.append({"file": pdf.name, "error": str(exc)})
        except Exception as exc:  # defensive: never kill the whole batch
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

