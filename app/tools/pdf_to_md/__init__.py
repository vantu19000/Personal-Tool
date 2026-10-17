"""PDF → Markdown tool — chuyển PDF text-based sang file .md bằng PyMuPDF.

Mỗi ``N`` trang (cài đặt được, mặc định 10) được tách thành một file Markdown
riêng. Phiên bản đầu tiên chỉ hỗ trợ PDF có sẵn lớp text (không scan/OCR).
"""
from .router import router

__all__ = ["router"]
