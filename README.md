# Personal-Tool

Ứng dụng web **đa tool chạy local** được xây bằng **FastAPI** + **Jinja2** + **Tailwind CSS**.
Mỗi "tool" là một module độc lập được đăng ký vào registry, nên thêm tool mới chỉ mất vài dòng — sidebar và dashboard tự cập nhật.

Tool đầu tiên: **SRT Translator** (hiện ở dạng skeleton/UI).

---

## 1. Công nghệ (Tech stack)

| Thành phần     | Dùng cho                                       |
| -------------- | ---------------------------------------------- |
| Python 3.12    | Runtime                                        |
| FastAPI        | Framework web / router / endpoints             |
| Starlette      | HTTP core, `StaticFiles`, `Jinja2Templates`    |
| Jinja2         | Server-side templating (layout + blocks)       |
| Tailwind CSS   | Styling (thông qua CDN Play)                   |
| Alpine.js      | Interactions nhẹ (menu mobile, ...)            |
| Uvicorn        | ASGI server chạy local                         |

> Ghi chú: dự án dùng FastAPI **bản mới**, nên `TemplateResponse` yêu cầu `request`
> là **tham số đầu tiên** (không phải trong dict context).

---

## 2. Yêu cầu (Prerequisites)

- **Python 3.12+** — kiểm tra: `python --version`
- **Git** (tùy chọn)
- Windows / macOS / Linux đều chạy được.

---

## 3. Cài đặt (Setup)

Bật PowerShell (hoặc Terminal) tại thư mục dự án:

```powershell
# 1) vào thư mục project
cd d:\Projects\Personal-Tool

# 2) tạo virtual environment (lần đầu)
python -m venv .venv

# 3) activate
#    Windows PowerShell:
.\.venv\Scripts\Activate.ps1
#    Nếu báo lỗi "running scripts is disabled", chọn 1 trong 2 cách:
#      (a) chạy bằng cmd:   cmd  →  .\.venv\Scripts\activate.bat
#      (b) mở rộng quyền PS:
#      Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 4) cài dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Virtual env tạo sẵn ở `.venv` và đã được ignore bởi `.gitignore`.

---

## 4. Chạy project (Run)

```powershell
# chắc chắn venv đã active (Prompt hiển thị (.venv))
uvicorn main:app --reload
```

Hoặc:

```powershell
python -m uvicorn main:app --reload
```

Mở trình duyệt:

| Route                                 | Trang                              |
| ------------------------------------- | ---------------------------------- |
| `http://127.0.0.1:8000`               | Dashboard (liệt kê các tool)       |
| `http://127.0.0.1:8000/tools/srt-translator` | SRT Translator (skeleton) |

- `--reload` : tự khởi động lại server mỗi khi sửa code (dùng khi dev).
- Mặc định listen ở `127.0.0.1:8000`.

Chạy host khác / port khác:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 5. Các lệnh thường dùng (Commands)

```powershell
# === virtual env ===
python -m venv .venv                 # tạo venv
.\.venv\Scripts\Activate.ps1         # activate (PowerShell)
deactivate                           # tắt venv

# === dependencies ===
pip install -r requirements.txt      # cài dependencies
pip freeze > requirements.txt        # ghi lại version hiện tại
pip list                             # xem đã cài gì
pip install -U package               # cập nhật 1 package

# === chạy server ===
uvicorn main:app --reload            # chạy local (dev, auto reload)
uvicorn main:app --port 8000         # chỉnh port
python -m uvicorn main:app --reload  # cách gọi tương đương

# === git (nếu dùng) ===
git status
git add .
git commit -m "msg"
git log --oneline

# === dọn cache (khi cần) ===
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

---

## 6. Cấu trúc thư mục (Project structure)

```
Personal-Tool/
├── main.py                      # app factory + mount /static + đăng ký router
├── requirements.txt
├── .gitignore
├── .python-version              # pin Python 3.12.10
└── app/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── config.py            # registry TOOLS → điều khiển sidebar & dashboard
    │   └── templates.py         # `templates` (Jinja2Templates) dùng chung
    ├── static/
    │   ├── css/app.css          # CSS tùy biến ngoài Tailwind
    │   └── js/app.js            # drag-drop, menu mobile, toast, confirm
    ├── templates/
    │   ├── base.html            # layout gốc + <nav> + Tailwind CDN + Alpine
    │   ├── _sidebar.html        # vòng lặp TOOLS + chỗ trống cho tool mới
    │   ├── dashboard.html       # trang chủ liệt kê tool
    │   └── tools/
    │       └── srt_translator.html
    └── tools/
        ├── __init__.py
        └── srt_translator/
            ├── __init__.py
            └── router.py        # GET /tools/srt-translator
```

---

## 7. Thêm tool mới (How to add a new tool)

**3 bước** (trùng đúng chú thích trong `app/core/config.py`), sidebar + dashboard tự cập nhật:

**Bước 1 — khai báo trong registry** (`app/core/config.py`), thêm 1 dict vào list `TOOLS`:

```python
TOOLS = [
    {"id": "srt-translator", "name": "SRT Translator", "path": "/tools/srt-translator"},
    {"id": "new-tool", "name": "Tool Mới", "path": "/tools/new-tool"},
]
```

> `id` dùng để highlight link active trong sidebar → dùng **gạch nối** (vd `new-tool`).

**Bước 2 — tạo router** tại `app/tools/new_tool/` (1 file `__init__.py` rỗng + `router.py`):

```python
# app/tools/new_tool/router.py
from fastapi import APIRouter, Request

from app.core.templates import templates   # import tên `templates` (KHÔNG phải JINJA_ENV)

router = APIRouter()


@router.get("/new-tool", name="new-tool")
async def new_tool(request: Request):
    return templates.TemplateResponse(
        request,                       # request là tham số ĐẦU TIÊN
        "tools/new_tool.html",
        {"active_tool": "new-tool"},   # khớp `id` trong registry
    )
```

> Template đặt ở `app/templates/tools/new_tool.html`, dùng `extends "base.html"`
> và override block `content`.

**Bước 3 — đăng ký router trong `main.py`** (trong `create_app()`, kế bên router SRT, dùng prefix `/tools`):

```python
from app.tools.new_tool import router as new_tool_router

# bên trong create_app():
app.include_router(new_tool_router, prefix="/tools", tags=["new-tool"])
```

Xong — khởi động lại server, tool mới sẽ hiện trong sidebar và dashboard.

---

## 8. Kiểm tra nhanh (Smoke test)

Không cần mở trình duyệt:

```powershell
.\.venv\Scripts\python.exe -c "import warnings; warnings.filterwarnings('ignore'); from fastapi.testclient import TestClient; import main; c=TestClient(main.app); print(c.get('/').status_code, c.get('/tools/srt-translator').status_code)"
```

Kết quả mong đợi: `200 200`.

---

## 9. Lưu ý (Notes)

- Tailwind & Alpine đang dùng **CDN** (dễ dev, không cần build). Khi ra production
  nên cân nhắc build bundle để tránh phụ thuộc mạng.
- Các file tạm (`__pycache__`, `.venv`, `.log`) đã được ignore.
- Muốn đổi tên tool / icon / thứ tự: sửa list `TOOLS` trong `app/core/config.py`.

