"""Services and database operations for Crawled Articles Management (Kho Bài Viết Thu Thập)."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.mongo_base import BaseMongoRepository
from app.core.pagination import PaginationMeta
from app.articles.models import (
    ARTICLE_STATUS_METADATA,
    SENTIMENT_METADATA,
    CrawledArticleModel,
)
from app.sources.models import SOURCE_TYPE_METADATA

logger = logging.getLogger(__name__)

COLLECTION_NAME = "crawled_articles"

# Rich default seed dataset of crawled articles representing various sources and platforms
DEFAULT_ARTICLES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Doanh nghiệp vừa và nhỏ chuyển mình: Ứng dụng AI Agent để tối ưu hóa phòng kinh doanh",
        "summary": "Xu hướng đưa các mô hình ngôn ngữ lớn (LLM) và AI Agent vào chăm sóc khách hàng và lập báo cáo tài chính tự động đang gia tăng mạnh mẽ trong quý 1/2026...",
        "content": """Tại diễn đàn 'Chuyển đổi số doanh nghiệp 2026', các chuyên gia hàng đầu nhấn mạnh rằng AI Agent không còn là sân chơi độc quyền của các tập đoàn công nghệ lớn. Các doanh nghiệp vừa và nhỏ (SMBs) tại Hà Nội và TP.HCM đang tích cực triển khai các agent cục bộ chạy trên máy tính nội bộ.

Ưu điểm nổi bật được ghi nhận:
1. Bảo mật tuyệt đối dữ liệu khách hàng và bí mật kinh doanh, không lo rò rỉ lên cloud công cộng.
2. Tiết kiệm tới 60% chi phí vận hành tổng đài và hỗ trợ kỹ thuật ban đầu.
3. Tích hợp trực tiếp vào Zalo OA, Messenger và hệ thống quản trị nội bộ ERP.

Nhiều chuyên gia dự báo trong vòng 6 tháng tới, việc trang bị tối thiểu một 'nhân viên AI ảo' sẽ trở thành tiêu chuẩn cạnh tranh bắt buộc đối với các nhà bán hàng và doanh nghiệp dịch vụ.""",
        "url": "https://vnexpress.net/doanh-nghiep-ai-agent-2026",
        "source": "VnExpress Kinh Doanh",
        "source_id": 1,
        "source_type": "website",
        "source_icon": "globe",
        "author": "Hoàng Nam",
        "location": "Hà Nội",
        "category": "Công nghệ & AI",
        "tags": ["AI Agent", "Doanh nghiệp SMB", "Tự động hóa", "LLM"],
        "sentiment": "Tích cực",
        "viral_potential": 94,
        "has_ai_idea": True,
        "target_product_id": 3,
        "target_product_name": "Web Blog Công Nghệ AI & Tự Động Hóa",
        "status": "has_idea",
        "crawled_at": "12 phút trước",
        "created_at": "2026-11-11 14:15",
        "updated_at": "2026-11-11 14:20",
    },
    {
        "id": 2,
        "title": "Bảng giá đất mới tại các thành phố lớn: Chuyên gia phân tích độ trễ và tác động thị trường",
        "summary": "Nhiều hộ gia đình đang tranh thủ hoàn tất thủ tục cấp sổ đỏ và chuyển đổi mục đích sử dụng đất trước thời điểm áp dụng quy định mới nhằm tối ưu hóa chi phí...",
        "content": """Thị trường bất động sản ghi nhận làn sóng người dân nộp hồ sơ xin cấp giấy chứng nhận quyền sử dụng đất và chuyển mục đích từ đất nông nghiệp sang đất ở tăng vọt trong tháng vừa qua.

Theo nhận định của các chuyên gia pháp lý bất động sản:
- Giá đất theo bảng giá mới tiệm cận hơn với giá thị trường, khiến nghĩa vụ tài chính và thuế phí chuyển nhượng trong tương lai có xu hướng tăng.
- Các khu vực ven đô Hà Nội và TP.HCM có sự phân hóa mạnh mẽ: các lô đất có pháp lý sạch, hạ tầng kết nối tốt tiếp tục giữ giá và tăng nhẹ, trong khi đất nền phân lô thiếu tiện ích có dấu hiệu chững lại.
- Lời khuyên cho nhà đầu tư cá nhân: Cần kiểm tra kỹ quy hoạch phân khu 1/2000 và tính toán kỹ bài toán đòn bẩy tài chính.""",
        "url": "https://tuoitre.vn/bang-gia-dat-moi-tac-dong-2026",
        "source": "Báo Tuổi Trẻ",
        "source_id": 2,
        "source_type": "rss",
        "source_icon": "rss",
        "author": "Minh Khôi",
        "location": "TP. Hồ Chí Minh",
        "category": "Bất động sản",
        "tags": ["Bảng giá đất", "Luật Đất Đai", "Sổ đỏ", "Pháp lý"],
        "sentiment": "Sôi nổi",
        "viral_potential": 89,
        "has_ai_idea": True,
        "target_product_id": 1,
        "target_product_name": "Kênh YouTube BĐS & Quy Hoạch Thủ Đô",
        "status": "has_idea",
        "crawled_at": "26 phút trước",
        "created_at": "2026-11-11 14:00",
        "updated_at": "2026-11-11 14:05",
    },
    {
        "id": 3,
        "title": "Hiện tượng bán hàng online bằng người ảo AI Livestream: Chi phí rẻ, tương tác ổn định",
        "summary": "Các phiên live AI kéo dài 24/7 không cần nghỉ ngơi, giọng đọc tự nhiên như người thật đang giúp nhiều shop thời trang và đồ gia dụng gặt hái đơn hàng ổn định ban đêm...",
        "content": """Trào lưu Shoppertainment và Livestream bán hàng bằng Avatar ảo đang bùng nổ trên các nền tảng video ngắn tại Việt Nam. Không ít chủ gian hàng cho biết chỉ cần đầu tư một bộ kịch bản và mô hình người ảo được huấn luyện giọng đọc địa phương, họ có thể duy trì phát sóng xuyên đêm.

Các con số thực tế:
- Tỷ lệ chuyển đổi đơn hàng vào khung giờ 0h - 5h sáng tăng 35% so với việc chỉ chạy quảng cáo video tĩnh.
- Tiết kiệm 70% chi phí thuê KOL/KOC trong các phiên live thường nhật.
- Tuy nhiên, nhiều chuyên gia cảnh báo người mua hàng vẫn thích sự tương tác cảm xúc thật khi mua các mặt hàng giá trị cao như trang sức hoặc đồ điện tử đắt tiền.""",
        "url": "https://tiktok.com/@trend/ai-stream",
        "source": "TikTok Business Trends",
        "source_id": 5,
        "source_type": "tiktok",
        "source_icon": "video",
        "author": "Trends Hub VN",
        "location": "Toàn quốc",
        "category": "E-Commerce",
        "tags": ["TikTok", "AI Livestream", "Shoppertainment", "KOL"],
        "sentiment": "Tích cực",
        "viral_potential": 87,
        "has_ai_idea": True,
        "target_product_id": 2,
        "target_product_name": "TikTok GenZ Đầu Tư & Tài Chính Cá Nhân",
        "status": "has_idea",
        "crawled_at": "35 phút trước",
        "created_at": "2026-11-11 13:50",
        "updated_at": "2026-11-11 13:55",
    },
    {
        "id": 4,
        "title": "Đà Nẵng thúc đẩy các trung tâm vi mạch bán dẫn và vườn ươm nhân tài công nghệ cao",
        "summary": "Thành phố công bố chính sách hỗ trợ học bổng và thu hút chuyên gia vi mạch toàn cầu với mức đãi ngộ hấp dẫn và cơ sở vật chất đạt chuẩn quốc tế...",
        "content": """Sáng nay, UBND TP. Đà Nẵng đã chính thức thông qua gói giải pháp đột phá nhằm đưa thành phố trở thành cứ điểm nghiên cứu, thiết kế vi mạch hàng đầu khu vực miền Trung.

Gói chính sách bao gồm:
- Miễn thuế thu nhập cá nhân trong 5 năm cho các kỹ sư thiết kế chip cấp cao về làm việc tại Khu Công viên Phần mềm số 2.
- Tài trợ 100% học phí cho các chương trình đào tạo chuyển đổi từ kỹ sư CNTT sang thiết kế vi mạch bán dẫn.
- Hợp tác trực tiếp với các trường đại học quốc tế tại Đài Loan, Nhật Bản và Hoa Kỳ để cấp chứng chỉ chuẩn ngành.""",
        "url": "https://baodanang.vn/ban-dan-vi-mach",
        "source": "Báo Đà Nẵng",
        "source_id": 1,
        "source_type": "website",
        "source_icon": "globe",
        "author": "Thanh Hải",
        "location": "Đà Nẵng",
        "category": "Công nghệ & Giáo dục",
        "tags": ["Bán dẫn", "Đà Nẵng", "Vi mạch", "Đào tạo nhân lực"],
        "sentiment": "Tích cực",
        "viral_potential": 78,
        "has_ai_idea": False,
        "target_product_id": 3,
        "target_product_name": "Web Blog Công Nghệ AI & Tự Động Hóa",
        "status": "new",
        "crawled_at": "45 phút trước",
        "created_at": "2026-11-11 13:40",
        "updated_at": "2026-11-11 13:40",
    },
    {
        "id": 5,
        "title": "Người trẻ chuộng 'Du lịch tái tạo năng lượng': Tìm về thiên nhiên, cai nghiện thiết bị số",
        "summary": "Kỳ nghỉ cuối tuần ngắn ngày tại các trang trại, khu glamping tách biệt đang trở thành phong cách sống mới của giới văn phòng sau những ngày làm việc căng thẳng...",
        "content": """Không còn hứng thú với việc chen chúc tại các điểm du lịch đông đúc, một bộ phận lớn giới trẻ Gen Z và dân văn phòng tại Hà Nội, TP.HCM đang tìm tới các tour trải nghiệm 'Digital Detox'.

Đặc điểm của xu hướng này:
- Du khách chủ động tắt thông báo công việc, gửi lại điện thoại cho ban quản lý trong 24 giờ đầu.
- Tham gia các hoạt động trồng rau, thu hoạch trà, thiền chuông và thưởng thức ẩm thực hữu cơ bản địa.
- Ngân sách cho mỗi chuyến đi 2 ngày 1 đêm chỉ dao động từ 800.000đ đến 1.500.000đ, phù hợp túi tiền đa số người trẻ.""",
        "url": "https://cafebiz.vn/du-lich-chua-lanh-2026",
        "source": "CafeBiz Đời Sống",
        "source_id": 2,
        "source_type": "rss",
        "source_icon": "rss",
        "author": "Thuỳ Linh",
        "location": "Lâm Đồng - Hà Nội",
        "category": "Đời sống & Du lịch",
        "tags": ["Du lịch chữa lành", "Glamping", "Work-life balance", "Gen Z"],
        "sentiment": "Bình yên",
        "viral_potential": 84,
        "has_ai_idea": True,
        "target_product_id": 5,
        "target_product_name": "Instagram Không Gian & Phong Cách Sống Đẹp",
        "status": "has_idea",
        "crawled_at": "1 giờ trước",
        "created_at": "2026-11-11 13:20",
        "updated_at": "2026-11-11 13:25",
    },
    {
        "id": 6,
        "title": "Chuyển động 24h: Cảnh báo chiêu trò thổi giá bất động sản vùng ven trước kỳ quy hoạch mới",
        "summary": "Phóng sự điều tra của VTV24 vạch trần các hội nhóm cò đất tạo sốt ảo, cắm cọc phân lô đất trồng cây lâu năm khi chưa có phê duyệt hạ tầng chính thức...",
        "content": """Bản tin Tiêu điểm Chuyển động 24h hôm nay phát sóng phóng sự ghi nhận thực tế tại các huyện vùng ven đang chờ lên quận. Lợi dụng thông tin quy hoạch mở đường vành đai, một số nhóm môi giới đã tổ chức các màn kịch dàn cảnh mua bán tấp nập, đặt cọc ảo nhằm lôi kéo người mua thiếu kinh nghiệm.

Cơ quan chức năng địa phương đã phát đi cảnh báo:
- Người dân cần tra cứu kỹ thông tin quy hoạch tại cổng thông tin điện tử của Sở Tài nguyên và Môi trường.
- Tuyệt đối không giao dịch qua giấy viết tay hoặc vi bằng với đất nông nghiệp chưa chuyển đổi mục đích sử dụng.
- Đã xử phạt hành chính nhiều đối tượng có hành vi căng băng rôn quảng cáo dự án 'ma'.""",
        "url": "https://youtube.com/@vtv24/quyhoach_canhbao",
        "source": "Kênh VTV24 Tiêu Điểm",
        "source_id": 4,
        "source_type": "youtube",
        "source_icon": "youtube",
        "author": "Ban Thời Sự VTV",
        "location": "Hà Nội",
        "category": "Bất động sản & Pháp lý",
        "tags": ["VTV24", "Cảnh báo", "Sốt đất ảo", "Pháp lý BĐS"],
        "sentiment": "Cảnh báo",
        "viral_potential": 92,
        "has_ai_idea": False,
        "target_product_id": 1,
        "target_product_name": "Kênh YouTube BĐS & Quy Hoạch Thủ Đô",
        "status": "new",
        "crawled_at": "2 giờ trước",
        "created_at": "2026-11-11 12:30",
        "updated_at": "2026-11-11 12:30",
    },
    {
        "id": 7,
        "title": "Báo cáo tiến độ đồ án quy hoạch phân khu đô thị Vành Đai 4 và chỉ tiêu đất dân cư",
        "summary": "Văn bản PDF tổng kết các chỉ tiêu kiến trúc, mật độ xây dựng và quỹ đất tái định cư phục vụ dự án đường cao tốc Vành Đai 4 vùng Thủ đô...",
        "content": """Tài liệu báo cáo chi tiết từ cơ quan quản lý đô thị cung cấp các số liệu quan trọng:
- Tổng diện tích đất thu hồi phục vụ dự án: hơn 1.300 ha đi qua 3 tỉnh thành.
- Tiến độ bàn giao mặt bằng thi công đã đạt 94.5%.
- Bố trí 14 khu tái định cư với đầy đủ hạ tầng trường học, trạm y tế và công viên cây xanh trước khi di dời người dân.
- Phê duyệt quy hoạch các nút giao liên thông và dải đất thương mại dịch vụ hai bên tuyến đường.""",
        "url": "https://soxaydung.danang.gov.vn/van-ban/quy-hoach-vanh-dai-4.pdf",
        "source": "Sở Xây Dựng - Báo cáo PDF",
        "source_id": 6,
        "source_type": "pdf",
        "source_icon": "file-text",
        "author": "Viện Quy Hoạch Xây Dựng",
        "location": "Hà Nội - Bắc Ninh",
        "category": "Quy hoạch & Hạ tầng",
        "tags": ["PDF", "Vành Đai 4", "Quy hoạch", "Tái định cư"],
        "sentiment": "Trung lập",
        "viral_potential": 81,
        "has_ai_idea": False,
        "target_product_id": 1,
        "target_product_name": "Kênh YouTube BĐS & Quy Hoạch Thủ Đô",
        "status": "new",
        "crawled_at": "3 giờ trước",
        "created_at": "2026-11-11 11:15",
        "updated_at": "2026-11-11 11:15",
    },
    {
        "id": 8,
        "title": "Cộng đồng cư dân thảo luận: Kinh nghiệm thực tế kiểm tra sổ đỏ và thủ tục sang tên năm 2026",
        "summary": "Bài viết tổng hợp chuỗi bình luận kinh nghiệm xương máu của các thành viên khi nộp hồ sơ đăng ký biến động đất đai trực tuyến trên cổng Dịch vụ công...",
        "content": """Trên nhóm thảo luận BĐS hơn 180.000 thành viên, chủ đề làm thủ tục sang tên sổ đỏ online thu hút hàng ngàn lượt tương tác.

Một số kinh nghiệm thực tế được chia sẻ nhiều nhất:
1. Chuẩn bị bản scan CCCD gắn chip và tài khoản VNeID cấp độ 2 trước khi nộp hồ sơ.
2. Kiểm tra kỹ số tờ, số thửa và tình trạng thế chấp ngân hàng tại Văn phòng Đăng ký Đất đai trước khi xuống tiền cọc.
3. Sử dụng biên lai điện tử để tra cứu tiến độ xử lý hồ sơ minh bạch, hạn chế việc phải đi lại nhiều lần.""",
        "url": "https://facebook.com/groups/bds.quyhoach.hanoi/post/1029384",
        "source": "Cộng đồng Quy hoạch & BĐS Hà Nội",
        "source_id": 3,
        "source_type": "facebook",
        "source_icon": "facebook",
        "author": "Admin Nhóm BĐS",
        "location": "Hà Nội",
        "category": "Bất động sản & Kinh nghiệm",
        "tags": ["Facebook Group", "Sổ đỏ", "Dịch vụ công", "Hỏi đáp"],
        "sentiment": "Sôi nổi",
        "viral_potential": 85,
        "has_ai_idea": True,
        "target_product_id": 4,
        "target_product_name": "Fanpage & Nhóm Cộng Đồng Nhà Đất Thực Chiến",
        "status": "has_idea",
        "crawled_at": "4 giờ trước",
        "created_at": "2026-11-11 10:00",
        "updated_at": "2026-11-11 10:10",
    },
    {
        "id": 9,
        "title": "Chỉ số xuất nhập khẩu và cán cân thương mại Việt Nam đạt mức tăng trưởng kỷ lục quý 1",
        "summary": "Dữ liệu JSON thời gian thực từ Cổng Dữ liệu Mở Quốc gia ghi nhận thặng dư thương mại đạt hơn 8.5 tỷ USD, động lực chính từ nhóm hàng điện tử và nông sản...",
        "content": """Báo cáo thống kê từ Tổng cục Hải quan qua Open Data API ghi nhận kim ngạch xuất nhập khẩu hàng hóa cả nước đạt mức tăng trưởng 18.2% so với cùng kỳ năm trước.

Các điểm nhấn đáng chú ý:
- Nhóm mặt hàng máy vi tính, sản phẩm điện tử và linh kiện đạt kim ngạch xuất khẩu cao nhất, chiếm 32% tổng kim ngạch.
- Nông sản xuất khẩu (gạo, cà phê, sầu riêng) tiếp tục lập kỷ lục về giá trị xuất khẩu nhờ mở rộng thị trường sang Trung Đông và EU.
- Cán cân thương mại tiếp tục duy trì trạng thái xuất siêu vững chắc, góp phần ổn định tỷ giá hối đoái.""",
        "url": "https://data.gov.vn/api/v1/indicators/trade-balance",
        "source": "Cổng Dữ Liệu Mở Quốc Gia (API)",
        "source_id": 9,
        "source_type": "api",
        "source_icon": "code-2",
        "author": "Hệ thống Open Data API",
        "location": "Toàn quốc",
        "category": "Kinh tế vĩ mô",
        "tags": ["API", "Dữ liệu mở", "Xuất nhập khẩu", "Thương mại"],
        "sentiment": "Tích cực",
        "viral_potential": 79,
        "has_ai_idea": False,
        "target_product_id": 3,
        "target_product_name": "Web Blog Công Nghệ AI & Tự Động Hóa",
        "status": "new",
        "crawled_at": "5 giờ trước",
        "created_at": "2026-11-11 09:00",
        "updated_at": "2026-11-11 09:00",
    },
]


class ArticleRepository(BaseMongoRepository):
    """Repository handling CRUD operations for crawled articles."""

    def __init__(self) -> None:
        super().__init__(collection_name=COLLECTION_NAME, id_field="id")


_repo = ArticleRepository()


async def init_articles_collection(db: Optional[Any] = None) -> None:
    """Ensure indexes and seed initial articles if empty."""
    col = _repo.get_collection(db)
    if col is not None:
        try:
            await _repo.ensure_indexes([
                ("id", True),
                "source_type",
                "category",
                "location",
                "sentiment",
                "status",
                "has_ai_idea",
                "target_product_id",
            ], db)
        except Exception as exc:
            logger.warning(f"Failed to ensure indexes for crawled_articles: {exc}")

    count = await _repo.count({}, db)
    if count == 0:
        logger.info(f"Seeding {len(DEFAULT_ARTICLES)} initial crawled articles...")
        await _repo.seed_if_empty(DEFAULT_ARTICLES, db)


def format_article_display(article: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich article dictionary with visual badges, icons, and sentiment colors."""
    a = dict(article)
    sent_key = a.get("sentiment", "Tích cực")
    st_meta = SENTIMENT_METADATA.get(sent_key, SENTIMENT_METADATA["Tích cực"])

    status_key = a.get("status", "new")
    status_meta = ARTICLE_STATUS_METADATA.get(status_key, ARTICLE_STATUS_METADATA["new"])

    src_type = a.get("source_type", "website")
    src_meta = SOURCE_TYPE_METADATA.get(src_type, SOURCE_TYPE_METADATA["website"])

    a["sentiment_badge"] = st_meta.get("badge_color", "bg-slate-100 text-slate-700")
    a["sentiment_dot"] = st_meta.get("dot_color", "bg-slate-400")
    a["status_label"] = status_meta.get("label", status_key.title())
    a["status_badge_color"] = status_meta.get("badge_color", "bg-slate-100 text-slate-700")
    a["source_type_label"] = src_meta.get("label", src_type.title())
    a["source_type_badge"] = src_meta.get("badge_color", "bg-slate-100 text-slate-700")
    a["source_icon"] = a.get("source_icon") or src_meta.get("icon", "globe")

    # Tags list
    if isinstance(a.get("tags"), str):
        raw_tags = a["tags"].replace(";", ",").split(",")
        a["tags"] = [t.strip() for t in raw_tags if t.strip()]
    elif not a.get("tags"):
        a["tags"] = []

    return a


async def list_articles(
    db: Optional[Any] = None,
    search: str = "",
    category_filter: str = "all",
    location_filter: str = "all",
    source_type_filter: str = "all",
    sentiment_filter: str = "all",
    status_filter: str = "all",
    product_filter: str = "all",
    page: int = 1,
    page_size: int = 12,
    sort_by: str = "newest",
) -> Dict[str, Any]:
    """Retrieve filtered, paginated list of crawled articles."""
    await init_articles_collection(db)

    query: Dict[str, Any] = {}

    if category_filter and category_filter != "all":
        query["category"] = category_filter

    if location_filter and location_filter != "all":
        query["location"] = location_filter

    if source_type_filter and source_type_filter != "all":
        query["source_type"] = source_type_filter

    if sentiment_filter and sentiment_filter != "all":
        query["sentiment"] = sentiment_filter

    if status_filter and status_filter != "all":
        if status_filter == "has_idea":
            query["has_ai_idea"] = True
        elif status_filter == "no_idea":
            query["has_ai_idea"] = False
        else:
            query["status"] = status_filter

    if product_filter and product_filter != "all":
        try:
            query["target_product_id"] = int(product_filter)
        except ValueError:
            pass

    clean_search = (search or "").strip()
    if clean_search:
        regex_pattern = {"$regex": re.escape(clean_search), "$options": "i"}
        query["$or"] = [
            {"title": regex_pattern},
            {"summary": regex_pattern},
            {"source": regex_pattern},
            {"location": regex_pattern},
            {"category": regex_pattern},
            {"tags": regex_pattern},
        ]

    # Sort logic
    sort_field = "id"
    sort_dir = -1
    if sort_by == "viral":
        sort_field = "viral_potential"
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

    enriched_items = [format_article_display(item) for item in items]
    stats = await get_articles_kpis(db)

    return {
        "items": enriched_items,
        "total": pagination.total_items,
        "pagination": pagination,
        "stats": stats,
        "db_connected": is_connected,
    }


async def get_articles_kpis(db: Optional[Any] = None) -> Dict[str, Any]:
    """Calculate KPI metrics for crawled articles."""
    all_articles, _ = await _repo.find_all(db=db)

    total = len(all_articles)
    crawled_today = total  # Default/demo value
    has_idea_count = sum(1 for a in all_articles if a.get("has_ai_idea") is True)
    high_viral_count = sum(1 for a in all_articles if int(a.get("viral_potential", 0)) >= 85)

    # Categories breakdown
    categories: Dict[str, int] = {}
    for a in all_articles:
        cat = a.get("category", "Tổng hợp")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_articles": total,
        "crawled_today": crawled_today,
        "has_idea_count": has_idea_count,
        "high_viral_count": high_viral_count,
        "categories": categories,
    }


async def get_article_by_id(article_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieve single article by integer ID."""
    doc = await _repo.find_by_id(article_id, db=db)
    if doc:
        return format_article_display(doc)
    return None


async def create_article(data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    """Create a new crawled article document."""
    await init_articles_collection(db)

    highest_id = await _repo.get_next_id(db=db)

    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
    elif not isinstance(tags, list):
        tags = []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    viral_score = 80
    if data.get("viral_potential") is not None:
        try:
            viral_score = int(data["viral_potential"])
        except (ValueError, TypeError):
            pass

    target_prod_id = None
    if data.get("target_product_id") is not None and str(data["target_product_id"]).strip():
        try:
            target_prod_id = int(data["target_product_id"])
        except (ValueError, TypeError):
            pass

    doc = {
        "id": highest_id,
        "title": (data.get("title") or "").strip(),
        "summary": (data.get("summary") or "").strip(),
        "content": (data.get("content") or "").strip(),
        "url": (data.get("url") or "").strip(),
        "source": (data.get("source") or "Website").strip(),
        "source_id": data.get("source_id"),
        "source_type": (data.get("source_type") or "website").strip().lower(),
        "source_icon": data.get("source_icon") or "globe",
        "author": (data.get("author") or "").strip(),
        "location": (data.get("location") or "Toàn quốc").strip(),
        "category": (data.get("category") or "Tổng hợp").strip(),
        "tags": tags,
        "sentiment": (data.get("sentiment") or "Tích cực").strip(),
        "viral_potential": viral_score,
        "has_ai_idea": bool(data.get("has_ai_idea", False)),
        "target_product_id": target_prod_id,
        "target_product_name": data.get("target_product_name"),
        "status": data.get("status") or "new",
        "crawled_at": "Vừa xong",
        "created_at": now_str,
        "updated_at": now_str,
    }

    inserted = await _repo.insert(doc, auto_id=False, db=db)
    return format_article_display(inserted)


async def update_article(article_id: int, data: Dict[str, Any], db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Update fields of an existing crawled article."""
    current = await _repo.find_by_id(article_id, db=db)
    if not current:
        return None

    update_payload: Dict[str, Any] = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    allowed_fields = [
        "title", "summary", "content", "url", "source", "source_type",
        "location", "category", "sentiment", "viral_potential",
        "has_ai_idea", "target_product_id", "target_product_name", "status",
    ]

    for field in allowed_fields:
        if field in data and data[field] is not None:
            val = data[field]
            if isinstance(val, str):
                val = val.strip()
            if field == "viral_potential":
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    val = current.get("viral_potential", 80)
            if field == "target_product_id":
                try:
                    val = int(val) if val else None
                except (ValueError, TypeError):
                    val = None
            update_payload[field] = val

    if "tags" in data and data["tags"] is not None:
        tags = data["tags"]
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
        elif not isinstance(tags, list):
            tags = []
        update_payload["tags"] = tags

    updated = await _repo.update(article_id, update_payload, db=db)
    if updated:
        return format_article_display(updated)
    return None


async def delete_article(article_id: int, db: Optional[Any] = None) -> bool:
    """Delete an article by integer ID."""
    return await _repo.delete(article_id, db=db)


async def assign_product_to_article(
    article_id: int,
    product_id: int,
    product_name: str,
    db: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Assign article to a target product / publishing channel."""
    return await update_article(
        article_id=article_id,
        data={
            "target_product_id": product_id,
            "target_product_name": product_name,
        },
        db=db,
    )


async def mark_as_has_idea(article_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Mark article as having generated AI ideas."""
    return await update_article(
        article_id=article_id,
        data={
            "has_ai_idea": True,
            "status": "has_idea",
        },
        db=db,
    )


async def reset_demo_articles(db: Optional[Any] = None) -> int:
    """Reset crawled articles collection to default rich seed data."""
    await init_articles_collection(db)
    all_current, _ = await _repo.find_all(db=db)
    for a in all_current:
        await _repo.delete(a["id"], db=db)
    for item in DEFAULT_ARTICLES:
        await _repo.insert(dict(item), auto_id=False, db=db)
    return len(DEFAULT_ARTICLES)


async def get_categories_dropdown(db: Optional[Any] = None) -> List[str]:
    """Retrieve distinct list of categories from articles in DB."""
    all_art, _ = await _repo.find_all(db=db)
    cats = {a.get("category", "Tổng hợp") for a in all_art if a.get("category")}
    return sorted(list(cats))


async def get_locations_dropdown(db: Optional[Any] = None) -> List[str]:
    """Retrieve distinct list of locations/provinces from articles in DB."""
    all_art, _ = await _repo.find_all(db=db)
    locs = {a.get("location", "Toàn quốc") for a in all_art if a.get("location")}
    return sorted(list(locs))
