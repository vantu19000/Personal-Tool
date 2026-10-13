"""Router for the Hash Calculator tool.

GET  /tools/hash-calculator          — form page (strings, files, algorithm pickers)
POST /tools/hash-calculator/compute  — compute digests for N strings and/or M files

Supported algorithms (whitelist): md5, sha1, sha224, sha256, sha384, sha512,
sha3_224, sha3_256, sha3_384, sha3_512. Default when none is selected: md5.
"""
import hashlib
import re

from fastapi import APIRouter, Request

from app.core.templates import templates

router = APIRouter()

SUPPORTED_ALGORITHMS = [
    "md5",
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
    "sha3_224",
    "sha3_256",
    "sha3_384",
    "sha3_512",
]
DEFAULT_ALGORITHMS = ["md5"]

CHUNK_SIZE = 1024 * 1024          # 1 MiB — read files in chunks to limit RAM usage
MAX_STRINGS = 100                 # tối đa 100 chuỗi text mỗi lần
MAX_FILES = 50                    # tối đa 50 file mỗi lần
MAX_FILE_SIZE = 2 * 1024**3       # 2 GiB mỗi file


@router.get("/hash-calculator", name="hash-calculator")
async def hash_calculator(request: Request):
    return templates.TemplateResponse(
        request,
        "tools/hash_calculator.html",
        {
            "active_tool": "hash-calculator",
            "algorithms": SUPPORTED_ALGORITHMS,
            "default_algorithms": DEFAULT_ALGORITHMS,
            "max_strings": MAX_STRINGS,
            "max_files": MAX_FILES,
        },
    )


# Repeated multipart parts under one name are collapsed by this Starlette
# version (last value wins), so the frontend sends each file as its own part
# (file_0, file_1, ...) and we collect every UploadFile value from the form.
_FILE_PART_RE = re.compile(r"^file(\d+)?$")


def _is_upload_file(value) -> bool:
    """True for any multipart file part (FastAPI or Starlette UploadFile)."""
    return (
        type(value).__name__ == "UploadFile"
        and hasattr(value, "read")
        and hasattr(value, "filename")
    )


def _collect_upload_files(form) -> list:
    """Return all uploaded files in part order, regardless of part name."""
    uploads: list[tuple[int, object]] = []
    for key, value in form.multi_items():
        if not _is_upload_file(value):
            continue
        match = _FILE_PART_RE.match(str(key))
        uploads.append((int(match.group(1)) if match and match.group(1) else 0, value))
    return [value for _, value in sorted(uploads, key=lambda item: item[0])]


@router.post("/hash-calculator/compute", name="hash-calculator-compute")
async def compute_hashes(request: Request):
    """Compute the selected digests for every provided string and/or file.

    Form fields:
    - text:       chuỗi văn bản cần băm — mỗi dòng là 1 chuỗi riêng biệt
    - algorithms: danh sách thuật toán phân tách bằng dấu phẩy (vd: md5,sha256); để trống = md5
    - file_0, file_1, ...: danh sách file cần tính mã băm (tối đa 50)
    """
    form = await request.form()
    text = str(form.get("text") or "")
    algorithms = str(form.get("algorithms") or "")
    files = _collect_upload_files(form)

    # --- Parse & validate algorithms ---------------------------------------
    algos: list[str] = []
    for raw in algorithms.split(","):
        name = raw.strip().lower()
        if not name:
            continue
        if name not in SUPPORTED_ALGORITHMS:
            return {
                "ok": False,
                "error": f"Thuật toán không hỗ trợ: {raw!r}. "
                         f"Chọn trong: {', '.join(SUPPORTED_ALGORITHMS)}.",
            }
        if name not in algos:  # bỏ trùng
            algos.append(name)
    if not algos:
        algos = list(DEFAULT_ALGORITHMS)

    # --- Split text into individual strings (1 line = 1 string) --------------
    strings = [line for line in text.splitlines() if line.strip()]
    if len(strings) > MAX_STRINGS:
        return {
            "ok": False,
            "error": f"Quá nhiều chuỗi (tối đa {MAX_STRINGS}).",
        }

    # --- Validate file list ---------------------------------------------------
    if len(files) > MAX_FILES:
        return {
            "ok": False,
            "error": f"Quá nhiều file (tối đa {MAX_FILES}).",
        }

    if not strings and not files:
        return {"ok": False, "error": "Vui lòng nhập ít nhất 1 chuỗi hoặc chọn 1 file."}

    # --- Hash the strings (data is small — one-shot digest) --------------------
    string_results = [
        {"value": s, "hashes": _digest_bytes(s.encode("utf-8"), algos)}
        for s in strings
    ]

    # --- Hash the files (chunked to keep memory flat on large files) ----------
    file_results = []
    for upload in files:
        if upload.size is not None and upload.size > MAX_FILE_SIZE:
            return {
                "ok": False,
                "error": f"File {upload.filename or 'không tên'} vượt quá 2 GiB.",
            }

        hashers = {alg: hashlib.new(alg) for alg in algos}
        size = 0
        while chunk := await upload.read(CHUNK_SIZE):
            size += len(chunk)
            for h in hashers.values():
                h.update(chunk)
        file_results.append(
            {
                "name": upload.filename or "unknown",
                "size": size,
                "hashes": {alg: h.hexdigest() for alg, h in hashers.items()},
            }
        )

    return {
        "ok": True,
        "algorithms": algos,
        "strings": string_results,
        "files": file_results,
    }


def _digest_bytes(data: bytes, algorithms: list[str]) -> dict[str, str]:
    """One-shot hex digests of *data* for every algorithm in *algorithms*."""
    return {alg: hashlib.new(alg, data).hexdigest() for alg in algorithms}