"""Services and database operations for AI Ideas Management (Kho Ý Tưởng AI)."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository
from app.core.pagination import PaginationMeta
from app.ideas.models import (
    IDEA_STATUS_METADATA,
    RECOMMENDED_FORMATS,
    AIIdeaModel,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ai_ideas"

# Rich default seed dataset for AI Ideas
DEFAULT_IDEAS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Hướng dẫn SMB tự setup AI Agent CSKH 0 đồng trên máy tính cục bộ bảo mật 100%",
        "angle": "Thực hành cầm tay chỉ việc (Step-by-step How-to) cho chủ shop và doanh nghiệp SMB",
        "target_audience": "Chủ shop online, Freelancer, Quản lý doanh nghiệp vừa và nhỏ",
        "recommended_format": "Bài viết dài (Blog / Website)",
        "viral_score": 96,
        "status": "ready",
        "keywords": ["AI Agent", "Ollama", "CSKH tự động", "Bảo mật dữ liệu", "Tiết kiệm chi phí"],
        "outline": """1. Mở đầu: Nỗi đau chi phí tổng đài và nguy cơ rò rỉ dữ liệu khách hàng lên Cloud.
2. Tại sao Local AI là xu thế tất yếu cho SMBs năm 2026?
3. Cấu hình phần cứng tối thiểu cần chuẩn bị (RAM 16GB, GPU cơ bản hoặc Apple Silicon).
4. Từng bước cài đặt:
   - Bước 1: Cài đặt Runtime mã nguồn mở (Ollama / vLLM).
   - Bước 2: Tải mô hình tiếng Việt chuyên dụng.
   - Bước 3: Nạp kịch bản trả lời khách hàng (RAG đơn giản).
5. Tích hợp trực tiếp vào Zalo OA & Messenger.
6. Đánh giá hiệu quả sau 30 ngày thử nghiệm.""",
        "source_article_id": 1,
        "source_article": "Doanh nghiệp vừa và nhỏ chuyển mình: Ứng dụng AI Agent...",
        "target_product_id": 3,
        "target_product_name": "Web Blog Công Nghệ AI & Tự Động Hóa",
        "target_platform": "blog",
        "ai_prompt_used": "Trích xuất ý tưởng bài viết thực hành kỹ thuật từ bài báo chuyển đổi số SMB",
        "notes": "Cần thêm ảnh chụp màn hình terminal lúc chạy lệnh curl cài đặt.",
        "created_at": "2026-11-11 14:10",
        "updated_at": "2026-11-11 14:10",
    },
    {
        "id": 2,
        "title": "Infographic Carousel: 5 mốc thời gian và chi phí người mua nhà cần nhớ theo Luật Đất Đai mới",
        "angle": "Trực quan hóa số liệu pháp lý, cảnh báo nghĩa vụ tài chính người dân cần biết trước khi làm sổ",
        "target_audience": "Người có ý định mua nhà, Đang làm thủ tục sổ đỏ, Nhà đầu tư cá nhân",
        "recommended_format": "Infographic Carousel (Fanpage / Threads)",
        "viral_score": 92,
        "status": "drafting",
        "keywords": ["Bảng giá đất", "Luật Đất Đai", "Chi phí làm sổ đỏ", "Mua chung cư", "Pháp lý"],
        "outline": """- Slide 1 (Hook): Bảng giá đất mới chuẩn bị áp dụng: Bạn sẽ phải trả thêm bao nhiêu tiền thuế?
- Slide 2: So sánh bảng giá đất cũ vs mới tại 3 khu vực ven đô trọng điểm.
- Slide 3: 3 trường hợp được miễn hoặc giảm tiền sử dụng đất bạn không nên bỏ qua.
- Slide 4: Quy trình 4 bước nộp hồ sơ hợp lệ tại Văn phòng đăng ký đất đai.
- Slide 5 (Call to Action): Tải file Excel tự tính thuế đất chuẩn 2026 tại phần bình luận.""",
        "source_article_id": 2,
        "source_article": "Bảng giá đất mới tại các thành phố lớn: Chuyên gia phân tích độ trễ...",
        "target_product_id": 1,
        "target_product_name": "Kênh YouTube BĐS & Quy Hoạch Thủ Đô",
        "target_platform": "youtube",
        "ai_prompt_used": "Chuyển bài viết chính sách đất đai thành kịch bản Carousel 5 slide cho mạng xã hội",
        "notes": "Phối màu chủ đạo xanh lam và vàng amber theo nhận diện kênh.",
        "created_at": "2026-11-11 13:50",
        "updated_at": "2026-11-11 14:00",
    },
    {
        "id": 3,
        "title": "Bóc trần sự thật về Livestream AI 24/7: Lời đồn triệu đơn hay chỉ là ảo tưởng đốt tiền?",
        "angle": "Phản biện đa chiều (Critical analysis) dựa trên phỏng vấn thực tế 5 chủ shop thời trang",
        "target_audience": "Nhà bán hàng Online, Creator, Marketer TikTok Shop",
        "recommended_format": "Video ngắn (TikTok / Shorts / Reels)",
        "viral_score": 88,
        "status": "reviewing",
        "keywords": ["AI Livestream", "Người ảo TikTok", "Shoppertainment", "Doanh thu thực", "KOL"],
        "outline": """0:00 - 0:05: Hook: 'Live xuyên đêm không ngủ, doanh thu trăm triệu? Sự thật là...'
0:05 - 0:25: Bóc chi phí thật: Bản quyền Avatar ảo + Server GPU + Kịch bản prompt (không hề rẻ).
0:25 - 0:45: Tỷ lệ chốt đơn thực tế vào khung giờ ma 2h - 5h sáng: Sản phẩm nào bán được, sản phẩm nào ế ẩm?
0:45 - 0:55: Thuật toán quét của TikTok: Rủi ro bị bóp tương tác nếu nội dung lặp lại vô hồn.
0:55 - 1:15: Kết luận & Lời khuyên vàng: Khi nào bạn nên đầu tư AI Live, khi nào vẫn cần người thật?""",
        "source_article_id": 3,
        "source_article": "Hiện tượng bán hàng online bằng người ảo AI Livestream...",
        "target_product_id": 2,
        "target_product_name": "TikTok GenZ Đầu Tư & Tài Chính Cá Nhân",
        "target_platform": "tiktok",
        "ai_prompt_used": "Phát triển kịch bản video ngắn phản biện xu hướng AI Livestream",
        "notes": "Chèn B-roll quay giao diện phần mềm AI clone giọng nói.",
        "created_at": "2026-11-11 13:30",
        "updated_at": "2026-11-11 13:45",
    },
    {
        "id": 4,
        "title": "Checklist 'Cai nghiện số 48h': Lịch trình cắm trại ven đô cho dân văn phòng cạn pin",
        "angle": "Cung cấp giải pháp phục hồi tinh thần kết hợp xu hướng du lịch chữa lành và kết nối thiên nhiên",
        "target_audience": "Dân công sở 22-35 tuổi tại Hà Nội và TP.HCM, Nhóm bạn trẻ, Cặp đôi",
        "recommended_format": "Bài viết dài (Blog / Website)",
        "viral_score": 85,
        "status": "published",
        "keywords": ["Du lịch chữa lành", "Camping ven đô", "Work-life balance", "Chữa lành", "Digital Detox"],
        "outline": """I. Hội chứng 'Kiệt sức thầm lặng' và chiếc điện thoại không bao giờ ngừng rung.
II. Quy tắc vàng của một chuyến Digital Detox:
    - Tắt thông báo công việc từ tối thứ 6.
    - Không mang laptop, chỉ dùng camera chụp ảnh kỷ niệm.
III. Gợi ý 3 địa điểm xanh mát cách trung tâm chưa đầy 60 phút di chuyển.
IV. Lịch trình 48h mẫu: Từ hái rau hữu cơ, thiền chuông đến đốt lửa trại nướng khoai.
V. Checklist hành lý gọn nhẹ dưới 5kg.""",
        "source_article_id": 5,
        "source_article": "Người trẻ chuộng 'Du lịch tái tạo năng lượng': Tìm về thiên nhiên...",
        "target_product_id": 5,
        "target_product_name": "Instagram Không Gian & Phong Cách Sống Đẹp",
        "target_platform": "instagram",
        "ai_prompt_used": "Tạo cẩm nang hành trình du lịch kết hợp lối sống chữa lành",
        "notes": "Đã xuất bản trên Blog và Instagram Carousel, lượng lưu bài viết đạt 340 lượt.",
        "created_at": "2026-11-11 13:10",
        "updated_at": "2026-11-11 13:10",
    },
    {
        "id": 5,
        "title": "Video dài: Điều tra 4 chiêu trò 'thổi giá' đất nền phân lô ven đô và cách tự bảo vệ sổ đỏ của bạn",
        "angle": "Phân tích điều tra (Expose format) dựa trên cảnh báo của VTV24 và thực tế tại các huyện sắp lên quận",
        "target_audience": "Người mua đất lần đầu, Gia đình tích lũy tài chính, Nhà đầu tư F0",
        "recommended_format": "Video dài (YouTube 10-15 phút)",
        "viral_score": 94,
        "status": "ready",
        "keywords": ["Sốt đất ảo", "BĐS Ven đô", "Cảnh báo lừa đảo", "Quy hoạch", "Sổ đỏ"],
        "outline": """Phần 1: Cảnh tượng đặt cọc nhộn nhịp tại quán cafe ven đường: Đâu là diễn viên, đâu là nạn nhân?
Phần 2: 4 chiêu bài tinh vi nhất:
   - Chiêu 1: Cắm cọc đo đạc giả quy hoạch mở đường lớn.
   - Chiêu 2: Bán đất nông nghiệp bằng vi bằng giấy tay.
   - Chiêu 3: Cò mồi tung tin đồn tập đoàn lớn chuẩn bị thâu tóm dự án.
   - Chiêu 4: Dựng lều phát quà kích động tâm lý sợ bỏ lỡ (FOMO).
Phần 3: Cách tra cứu quy hoạch chuẩn 100% trên điện thoại trong 3 phút.
Phần 4: Lời khuyên pháp lý từ luật sư bất động sản.""",
        "source_article_id": 6,
        "source_article": "Chuyển động 24h: Cảnh báo chiêu trò thổi giá bất động sản vùng ven...",
        "target_product_id": 1,
        "target_product_name": "Kênh YouTube BĐS & Quy Hoạch Thủ Đô",
        "target_platform": "youtube",
        "ai_prompt_used": "Xây dựng kịch bản video dài phóng sự điều tra bất động sản cảnh báo rủi ro",
        "notes": "Chuẩn bị thumbnail có biểu tượng cảnh báo và ảnh chụp hiện trường cắm mốc.",
        "created_at": "2026-11-11 12:40",
        "updated_at": "2026-11-11 12:40",
    },
    {
        "id": 6,
        "title": "Kịch bản Podcast: Bán dẫn và Vi mạch tại Việt Nam: Cú hích lịch sử hay thách thức nguồn nhân lực?",
        "angle": "Đối thoại chuyên sâu với góc nhìn thực tế từ các kỹ sư chuyển ngành tại Đà Nẵng",
        "target_audience": "Sinh viên CNTT, Kỹ sư điện tử, Người quan tâm tới định hướng công nghệ cao",
        "recommended_format": "Kịch bản Livestream / Podcast",
        "viral_score": 83,
        "status": "ready",
        "keywords": ["Bán dẫn", "Thiết kế Vi mạch", "Đà Nẵng", "Chuyển ngành CNTT", "Học bổng"],
        "outline": """Mục 1: Mở đầu - Cơn khát chip toàn cầu và vị thế chiến lược của miền Trung Việt Nam.
Mục 2: Chính sách miễn thuế 5 năm tại Đà Nẵng có thực sự đủ sức kéo nhân tài việt kiều trở về?
Mục 3: Hành trình chuyển ngành từ Web Developer sang kỹ sư Thiết kế vi mạch: Mất bao lâu và cần học những gì?
Mục 4: Lời khuyên cho các bạn sinh viên năm 3-4 muốn đón đầu làn sóng đầu tư FDI năm 2026.""",
        "source_article_id": 4,
        "source_article": "Đà Nẵng thúc đẩy các trung tâm vi mạch bán dẫn và vườn ươm nhân tài...",
        "target_product_id": 3,
        "target_product_name": "Web Blog Công Nghệ AI & Tự Động Hóa",
        "target_platform": "blog",
        "ai_prompt_used": "Thiết kế đề cương talkshow phỏng vấn về cơ hội việc làm ngành bán dẫn",
        "notes": "Dự kiến thu âm tập 12 của chuỗi Tech Talks hàng tuần.",
        "created_at": "2026-11-11 12:15",
        "updated_at": "2026-11-11 12:15",
    },
    {
        "id": 7,
        "title": "Bản tin Email: Chi phí nuôi xe điện mini sau 10.000km: Con số thực tế khiến nhiều người giật mình",
        "angle": "Minh bạch tài chính gia đình, tính toán chi li từng đồng tiền điện, bảo hiểm và chi phí sạc pin",
        "target_audience": "Người đi làm trong phố, Người cân nhắc mua ô tô đầu tiên, Độc giả Newsletter",
        "recommended_format": "Bản tin Email (Newsletter)",
        "viral_score": 89,
        "status": "drafting",
        "keywords": ["Xe điện mini", "Chi phí nuôi xe", "Sạc pin nội đô", "Tiết kiệm", "Ô tô điện"],
        "outline": """Tiêu đề thư: Bạn tốn bao nhiêu cho tiền xăng mỗi tháng? Hãy xem bảng kê này của tôi...
Nội dung chính:
- Tổng tiền điện sạc tại nhà trong 6 tháng: Chỉ tương đương 3 cốc trà sữa mỗi tuần.
- Chi phí bảo dưỡng mốc 10.000km: Tại sao rẻ hơn xe xăng tới 70%?
- 2 điều phiền toái chưa ai kể cho bạn: Tìm chỗ sạc khi đi xa và thời gian chờ đợi.
- Bảng đối chiếu: Xe điện mini vs Xe máy tay ga cao cấp vs Xe xăng hạng A.
- Lời khuyên cuối: Ai nên mua ngay và ai nên chờ thêm?""",
        "source_article_id": 7,
        "source_article": "Chi phí sở hữu và nuôi xe điện mini nội đô sau 1 năm sử dụng thực tế...",
        "target_product_id": 4,
        "target_product_name": "Facebook Fanpage Review Công Nghệ Tiêu Dùng",
        "target_platform": "facebook",
        "ai_prompt_used": "Chuyển dữ liệu review xe điện thành bản tin email thân mật, tin cậy",
        "notes": "Gửi cho danh sách 4.500 subscribers vào 8h sáng thứ Bảy.",
        "created_at": "2026-11-11 11:45",
        "updated_at": "2026-11-11 11:45",
    },
    {
        "id": 8,
        "title": "Infographic Carousel: 7 nguyên tắc tối giản phong cách Wabi Sabi giúp căn hộ nhỏ thoáng gấp đôi",
        "angle": "Ý tưởng thiết kế nội thất nhà ở, tối ưu không gian sống với kinh phí tiết kiệm",
        "target_audience": "Chủ căn hộ chung cư 45-70m2, Người yêu thích phong cách sống tối giản Zen",
        "recommended_format": "Infographic Carousel (Fanpage / Threads)",
        "viral_score": 91,
        "status": "ready",
        "keywords": ["Wabi Sabi", "Nội thất tối giản", "Căn hộ nhỏ", "Decor phòng", "Zen"],
        "outline": """Slide 1: Nhà nhỏ nhưng không hề chật: Triết lý Wabi Sabi ứng dụng vào căn hộ hiện đại.
Slide 2: Quy tắc 1: Chọn màu sơn đất mộc mạc (Beige, Xám ấm, Nâu đất) thay vì màu trắng tinh lạnh lẽo.
Slide 3: Quy tắc 2: Tận dụng ánh sáng tự nhiên qua rèm lanh thay cho đèn chùm cầu kỳ.
Slide 4: Quy tắc 3: Ưu tiên vật liệu tự nhiên: Gỗ thô, gốm mộc, vải đay.
Slide 5: Quy tắc 4: Bỏ bớt 50% đồ đạc không cần thiết trên sàn nhà.
Slide 6: Bộ ảnh phối cảnh trước và sau khi cải tạo.""",
        "source_article_id": 8,
        "source_article": "Cẩm nang thiết kế căn hộ phong cách Wabi Sabi mộc mạc...",
        "target_product_id": 6,
        "target_product_name": "Pinterest Ý Tưởng Decor & Nhà Đẹp",
        "target_platform": "pinterest",
        "ai_prompt_used": "Tóm tắt cẩm nang nội thất thành 6 slide Pinterest Carousel bắt mắt",
        "notes": "Đã xuất kho ảnh mẫu 3D độ phân giải cao sẵn sàng render.",
        "created_at": "2026-11-11 11:20",
        "updated_at": "2026-11-11 11:20",
    },
]

# Singleton repository instance
_repo = BaseMongoRepository(COLLECTION_NAME, id_field="id")


def format_idea_display(item: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich an AI Idea document with display badges, formats, and tags."""
    doc = dict(item)

    status_key = doc.get("status", "ready")
    status_meta = IDEA_STATUS_METADATA.get(
        status_key,
        {
            "label": "Sẵn sàng",
            "badge_color": "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
            "dot_color": "bg-slate-400",
        },
    )
    doc["status_label"] = status_meta["label"]
    doc["status_color"] = status_meta["badge_color"]
    doc["status_badge"] = status_meta["badge_color"]
    doc["dot_color"] = status_meta.get("dot_color", "bg-emerald-500")

    # Keywords array check
    kw = doc.get("keywords", [])
    if isinstance(kw, str):
        kw_list = [k.strip() for k in re.split(r"[,;\n]+", kw) if k.strip()]
        doc["keywords"] = kw_list
    elif not isinstance(kw, list):
        doc["keywords"] = []

    # Viral score normalization
    try:
        doc["viral_score"] = int(doc.get("viral_score", 80))
    except (ValueError, TypeError):
        doc["viral_score"] = 80

    return doc


async def init_ideas_collection(db: Optional[Any] = None) -> bool:
    """Ensure indexes for ai_ideas collection (no auto-seeding on page load)."""
    col = _repo.get_collection(db)
    if col is not None:
        try:
            await _repo.ensure_indexes([("id", True), "status", "viral_score", "target_product_id"], db=db)
        except Exception as exc:
            logger.warning(f"Failed to ensure indexes for ai_ideas: {exc}")
    return True


async def list_ideas(
    db: Optional[Any] = None,
    search: str = "",
    status_filter: str = "all",
    format_filter: str = "all",
    product_filter: str = "all",
    page: int = 1,
    page_size: int = 6,
    sort_by: str = "newest",
) -> Dict[str, Any]:
    """Query, filter, and paginate AI ideas from MongoDB with in-memory fallback.

    Returns:
        dict with keys: items, total, pagination, stats, db_connected
    """
    await init_ideas_collection(db=db)

    query: Dict[str, Any] = {}

    if status_filter and status_filter != "all":
        query["status"] = status_filter

    if format_filter and format_filter != "all":
        query["recommended_format"] = format_filter

    if product_filter and product_filter != "all":
        try:
            prod_id = int(product_filter)
            query["target_product_id"] = prod_id
        except ValueError:
            pass

    if search and search.strip():
        term = search.strip()
        regex_pattern = {"$regex": term, "$options": "i"}
        query["$or"] = [
            {"title": regex_pattern},
            {"angle": regex_pattern},
            {"target_audience": regex_pattern},
            {"keywords": regex_pattern},
            {"source_article": regex_pattern},
            {"outline": regex_pattern},
            {"target_product_name": regex_pattern},
        ]

    # Sort direction
    sort_field = "id"
    sort_dir = -1
    if sort_by == "viral":
        sort_field = "viral_score"
        sort_dir = -1
    elif sort_by == "title":
        sort_field = "title"
        sort_dir = 1
    elif sort_by == "newest":
        sort_field = "id"
        sort_dir = -1

    page = max(1, page)
    page_size = max(1, min(100, page_size))

    items, pagination, is_connected = await _repo.find_paginated(
        query=query,
        sort_field=sort_field,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
        db=db,
    )

    enriched_items = [format_idea_display(item) for item in items]
    stats = await get_ideas_kpis(db)

    return {
        "items": enriched_items,
        "total": pagination.total_items,
        "pagination": pagination,
        "stats": stats,
        "db_connected": is_connected,
    }


async def get_ideas_kpis(db: Optional[Any] = None) -> Dict[str, Any]:
    """Calculate KPI summary metrics for the AI Ideas library."""
    all_ideas, _ = await _repo.find_all(db=db)

    total = len(all_ideas)
    ready_count = sum(1 for i in all_ideas if i.get("status") == "ready")
    drafting_count = sum(1 for i in all_ideas if i.get("status") == "drafting")
    published_count = sum(1 for i in all_ideas if i.get("status") == "published")
    high_viral_count = sum(1 for i in all_ideas if int(i.get("viral_score", 0)) >= 90)

    # Format breakdown
    formats: Dict[str, int] = {}
    for i in all_ideas:
        fmt = i.get("recommended_format", "Bài viết dài")
        formats[fmt] = formats.get(fmt, 0) + 1

    return {
        "total_ideas": total,
        "ready_count": ready_count,
        "drafting_count": drafting_count,
        "published_count": published_count,
        "high_viral_count": high_viral_count,
        "formats": formats,
    }


async def get_idea_by_id(idea_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single AI Idea by its integer ID."""
    await init_ideas_collection(db=db)
    raw = await _repo.find_by_id(idea_id, db=db)
    if raw:
        return format_idea_display(raw)
    return None


async def create_idea(idea_data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Create a new AI Idea in the database."""
    await init_ideas_collection(db=db)

    # Generate next integer ID
    all_ideas, _ = await _repo.find_all(db=db)
    max_id = max([int(item.get("id", 0)) for item in all_ideas], default=0)
    new_id = max_id + 1

    # Keywords normalize
    keywords = idea_data.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in re.split(r"[,;\n]+", keywords) if k.strip()]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = {
        "id": new_id,
        "title": idea_data.get("title", "").strip(),
        "angle": idea_data.get("angle", "").strip(),
        "target_audience": idea_data.get("target_audience", "").strip(),
        "recommended_format": idea_data.get("recommended_format", "Bài viết dài (Blog / Website)"),
        "viral_score": int(idea_data.get("viral_score", 85)),
        "status": idea_data.get("status", "ready"),
        "keywords": keywords,
        "outline": idea_data.get("outline", ""),
        "source_article_id": int(idea_data["source_article_id"]) if idea_data.get("source_article_id") else None,
        "source_article": idea_data.get("source_article", "").strip(),
        "target_product_id": int(idea_data["target_product_id"]) if idea_data.get("target_product_id") else None,
        "target_product_name": idea_data.get("target_product_name", "").strip(),
        "target_platform": idea_data.get("target_platform", "").strip(),
        "ai_prompt_used": idea_data.get("ai_prompt_used", ""),
        "notes": idea_data.get("notes", ""),
        "created_at": now_str,
        "updated_at": now_str,
    }

    # Validate with model
    model = AIIdeaModel(**doc)
    doc_dict = model.to_mongo_doc()

    created = await _repo.insert(doc_dict, auto_id=False, db=db)
    return format_idea_display(created)


async def update_idea(idea_id: int, update_data: Dict[str, Any], db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Update fields of an existing AI Idea."""
    await init_ideas_collection(db=db)

    clean_data = dict(update_data)
    clean_data.pop("id", None)
    clean_data.pop("_id", None)

    if "keywords" in clean_data and isinstance(clean_data["keywords"], str):
        clean_data["keywords"] = [k.strip() for k in re.split(r"[,;\n]+", clean_data["keywords"]) if k.strip()]

    if "viral_score" in clean_data and clean_data["viral_score"] is not None:
        try:
            clean_data["viral_score"] = int(clean_data["viral_score"])
        except ValueError:
            pass

    if "target_product_id" in clean_data and clean_data["target_product_id"]:
        try:
            clean_data["target_product_id"] = int(clean_data["target_product_id"])
        except ValueError:
            pass

    if "source_article_id" in clean_data and clean_data["source_article_id"]:
        try:
            clean_data["source_article_id"] = int(clean_data["source_article_id"])
        except ValueError:
            pass

    clean_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    updated = await _repo.update(idea_id, clean_data, db=db)
    if updated:
        return format_idea_display(updated)
    return None


async def delete_idea(idea_id: int, db: Optional[Any] = None) -> bool:
    """Delete an AI Idea by its ID."""
    await init_ideas_collection(db=db)
    return await _repo.delete(idea_id, db=db)


async def update_idea_status(idea_id: int, new_status: str, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Quickly update the workflow status of an AI Idea (ready -> drafting -> reviewing -> published)."""
    return await update_idea(idea_id, {"status": new_status}, db=db)


async def assign_product_to_idea(
    idea_id: int,
    product_id: int,
    product_name: str,
    platform: Optional[str] = None,
    db: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Assign an AI Idea to a target user product / channel."""
    update_fields = {
        "target_product_id": product_id,
        "target_product_name": product_name,
    }
    if platform:
        update_fields["target_platform"] = platform
    return await update_idea(idea_id, update_fields, db=db)


async def generate_idea_from_article(article: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Simulate AI generation of a creative angle & outline from a crawled article."""
    art_title = article.get("title", "")
    art_id = article.get("id")
    category = article.get("category", "Tổng hợp")
    viral_pot = int(article.get("viral_potential", 85))

    new_idea_data = {
        "title": f"Phân tích chuyên sâu: {art_title}",
        "angle": f"Góc nhìn đa chiều về {category}, phân tích ảnh hưởng trực tiếp tới người tiêu dùng Việt Nam",
        "target_audience": "Độc giả trẻ, Nhà đầu tư cá nhân, Cộng đồng trực tuyến",
        "recommended_format": "Bài viết dài (Blog / Website)",
        "viral_score": min(98, max(75, viral_pot + 2)),
        "status": "ready",
        "keywords": article.get("tags", [category, "AI", "Xu hướng"]),
        "outline": f"""1. Tổng quan vấn đề được nêu trong bài viết '{art_title}'.
2. 3 phát hiện quan trọng nhất và số liệu thực tế cần lưu tâm.
3. Dự báo xu hướng phát triển trong 6-12 tháng tới.
4. Lời khuyên hành động cụ thể cho người đọc.""",
        "source_article_id": art_id,
        "source_article": art_title,
        "target_product_id": article.get("target_product_id"),
        "target_product_name": article.get("target_product_name", ""),
        "ai_prompt_used": "Trích xuất ý tưởng và phác thảo dàn ý nội dung từ tin tức thu thập thời gian thực",
        "notes": f"Sinh tự động từ bài thu thập #{art_id}",
    }
    return await create_idea(new_idea_data, db=db)


async def reset_demo_ideas(db: Optional[Any] = None) -> int:
    """Reset the AI Ideas collection back to DEFAULT_IDEAS seed data."""
    all_ideas, _ = await _repo.find_all(db=db)
    for item in all_ideas:
        await _repo.delete(item["id"], db=db)
    for seed in DEFAULT_IDEAS:
        await _repo.insert(dict(seed), auto_id=False, db=db)
    return len(DEFAULT_IDEAS)
