#!/bin/zsh

# Di chuyển vào thư mục chứa dự án hiện tại
cd "$(dirname "$0")"

# Nạp các đường dẫn môi trường phổ biến trên macOS (pyenv, homebrew, v.v.)
export PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

if command -v pyenv 1>/dev/null 2>&1; then
    eval "$(pyenv init -)"
fi

echo "=========================================================="
echo "🚀 Đang khởi động Personal-Tool trên macOS..."
echo "📍 Thư mục làm việc: $(pwd)"
echo "🌐 Ứng dụng: http://127.0.0.1:8000"
echo "=========================================================="

# Tự động mở trình duyệt sau 1.5 giây
(sleep 1.5 && open "http://127.0.0.1:8000") &

# Chạy server với pyenv
if command -v pyenv 1>/dev/null 2>&1; then
    pyenv exec python -m uvicorn main:app --reload
else
    python3 -m uvicorn main:app --reload
fi
