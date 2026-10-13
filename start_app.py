"""Hidden launcher for the Personal-Tool server.

- Nếu server CHƯA chạy trên cổng 8000 → khởi động uvicorn trong nền (không cửa sổ).
- Nếu server ĐANG chạy → chỉ mở trình duyệt.
- Luôn mở trình duyệt tới http://127.0.0.1:8000.
"""
import os
import socket
import subprocess
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}/"


def port_open() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False


def main() -> None:
    if not port_open():
        # Start the server detached so it keeps running after this script exits.
        subprocess.Popen(
            [VENV_PY, "-m", "uvicorn", "main:app", "--host", HOST, "--port", str(PORT)],
            cwd=ROOT,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        # Wait for it to come up (max ~20s) before opening the browser.
        for _ in range(80):
            if port_open():
                break
            time.sleep(0.25)

    webbrowser.open(URL)


if __name__ == "__main__":
    main()