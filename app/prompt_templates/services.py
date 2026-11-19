"""Services and repository layer for managing Prompt Templates in MongoDB."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.mongo_base import BaseMongoRepository, current_timestamp_str
from app.prompt_templates.models import PromptTemplateCreate, PromptTemplateUpdate
from app.tools.image_to_prompt.services import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE_COLLECTION = "prompt_templates"

# Initial seed templates
INITIAL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Chân dung Nữ & Nam Chuẩn SEO (Mặc định)",
        "description": "Mẫu chuẩn tạo 5 tiêu đề SEO dưới 80 ký tự, slug URL chuẩn SEO và prompt chi tiết chia theo từng phần (Subject, Pose, Expression, Clothing, Background, Lighting, Camera, Style) bằng tiếng Bồ Đào Nha.",
        "category": "Chân dung",
        "language": "pt-BR",
        "aspect_ratio_mode": "none",
        "target_aspect_ratio": "4:5",
        "prompt_content": DEFAULT_SYSTEM_PROMPT,
        "is_default": True,
        "created_at": current_timestamp_str(),
        "updated_at": current_timestamp_str(),
    },
    {
        "id": 2,
        "name": "Chân dung Thời trang & Editorial Nghệ thuật",
        "description": "Phong cách ảnh bìa tạp chí thời trang (Vogue/Harper's Bazaar), tạo dáng nghệ thuật cao cấp, ánh sáng studio tương phản cao và trang phục ấn tượng.",
        "category": "Thời trang",
        "language": "pt-BR",
        "aspect_ratio_mode": "none",
        "target_aspect_ratio": "4:5",
        "prompt_content": (
            "Dịch ngược bức ảnh thành prompt tạo ảnh thời trang nghệ thuật (Fashion Editorial) chi tiết cao cấp.\n\n"
            "YÊU CẦU QUAN TRỌNG VỀ KHUÔN MẶT THAM CHIẾU:\n"
            "Khuôn mặt và đường nét nhận diện của người mẫu (nam hoặc nữ) BẮT BUỘC phải dựa chính xác trên ảnh tham chiếu đính kèm "
            "(o rosto e os traços faciais devem ser exatamente baseados na imagem de referência anexada). "
            "Không mô tả chi tiết khuôn mặt gốc để người dùng dễ thay thế.\n\n"
            "GỢI Ý 5 TIÊU ĐỀ CHO PROMPT & SLUG (TỐI ƯU SEO):\n"
            "Gợi ý 5 tiêu đề ảnh thời trang nghệ thuật bằng {output_language}, mỗi tiêu đề BẮT BUỘC DƯỚI 80 KÝ TỰ:\n"
            "[Loại ảnh: Foto Editorial / Ensaio de Moda] + [Chủ thể: Feminina / Masculino] + [Điểm nhấn nghệ thuật]\n\n"
            "CẤU TRÚC PHẦN PROMPT (BẮT BUỘC CHIA THEO TỪNG PHẦN, MỖI PHẦN XUỐNG DÒNG):\n"
            "Trong mục 'Prompt:', BẮT BUỘC phải chia theo từng phần rõ ràng, mỗi phần nằm trên một dòng riêng biệt:\n"
            "- Subject: Người mẫu thời trang (nam/nữ), thần thái cuốn hút, khuôn mặt dựa trên ảnh tham chiếu bằng {output_language}.\n"
            "- Pose: Tư thế tạo dáng thời trang editorial ấn tượng, chuyển động cơ thể mềm mại hoặc góc cạnh sắc sảo bằng {output_language}.\n"
            "- Expression: Ánh mắt hút hồn, thần thái high-fashion sang trọng bằng {output_language}.\n"
            "- Clothing: Trang phục thời trang cao cấp (Haute Couture), chất liệu vải tinh xảo, phụ kiện sang trọng bằng {output_language}.\n"
            "- Background: Phông nền studio tối giản, bối cảnh kiến trúc hiện đại hoặc mỹ thuật ấn tượng với bokeh mịn bằng {output_language}.\n"
            "- Lighting: Ánh sáng studio nghệ thuật (chiaroscuro / dramatic rim light), tương phản sắc nét bằng {output_language}.\n"
            "- Camera: Góc chụp chuyên nghiệp, ống kính chân dung 85mm f/1.4 sắc nét từng chi tiết bằng {output_language}.\n"
            "- Style: Phong cách nhiếp ảnh thời trang cao cấp, màu sắc điện ảnh, chất lượng 8k bằng {output_language}.\n\n"
            "NGÔN NGỮ ĐẦU RA:\n"
            "- Cả 5 Tiêu đề và Nội dung Prompt BẮT BUỘC viết bằng: {output_language}.\n"
            "- Slug: là slug URL chuẩn SEO viết thường, không dấu, ngăn cách bằng dấu gạch ngang (-).\n\n"
            "ĐỊNH DẠNG TRẢ VỀ:\n"
            "Title:\n"
            "1. <Tiêu đề 1 dưới 80 ký tự>\n"
            "2. <Tiêu đề 2 dưới 80 ký tự>\n"
            "3. <Tiêu đề 3 dưới 80 ký tự>\n"
            "4. <Tiêu đề 4 dưới 80 ký tự>\n"
            "5. <Tiêu đề 5 dưới 80 ký tự>\n\n"
            "Slug:\n"
            "1. <slug-tieu-de-1>\n"
            "2. <slug-tieu-de-2>\n"
            "3. <slug-tieu-de-3>\n"
            "4. <slug-tieu-de-4>\n"
            "5. <slug-tieu-de-5>\n\n"
            "Prompt:\n"
            "Subject: <mô tả>\n"
            "Pose: <mô tả>\n"
            "Expression: <mô tả>\n"
            "Clothing: <mô tả>\n"
            "Background: <mô tả>\n"
            "Lighting: <mô tả>\n"
            "Camera: <mô tả>\n"
            "Style: <mô tả>"
        ),
        "is_default": False,
        "created_at": current_timestamp_str(),
        "updated_at": current_timestamp_str(),
    },
    {
        "id": 3,
        "name": "Chân dung Doanh nhân & Chuyên nghiệp (Corporate)",
        "description": "Ảnh phong thái lãnh đạo, doanh nhân thành đạt (Executive Portrait / LinkedIn Headshot), trang phục vest thanh lịch, bối cảnh văn phòng cao cấp.",
        "category": "Doanh nhân",
        "language": "pt-BR",
        "aspect_ratio_mode": "none",
        "target_aspect_ratio": "4:5",
        "prompt_content": (
            "Dịch ngược bức ảnh thành prompt ảnh chân dung doanh nhân chuyên nghiệp (Executive Headshot / Corporate Portrait).\n\n"
            "YÊU CẦU QUAN TRỌNG VỀ KHUÔN MẶT THAM CHIẾU:\n"
            "Khuôn mặt và đường nét nhận diện của nhân vật doanh nhân (nam hoặc nữ) BẮT BUỘC phải dựa chính xác trên ảnh tham chiếu đính kèm "
            "(o rosto e os traços faciais devem ser exatamente baseados na imagem de referência anexada). "
            "Không mô tả chi tiết khuôn mặt gốc để người dùng dễ thay thế.\n\n"
            "GỢI Ý 5 TIÊU ĐỀ CHO PROMPT & SLUG (TỐI ƯU SEO):\n"
            "Gợi ý 5 tiêu đề ảnh doanh nhân bằng {output_language}, mỗi tiêu đề BẮT BUỘC DƯỚI 80 KÝ TỰ:\n"
            "[Loại ảnh: Retrato Corporativo / Foto Executiva] + [Chủ thể: de uma mulher de negócios / de um executivo] + [Phong thái/Bối cảnh]\n\n"
            "CẤU TRÚC PHẦN PROMPT (BẮT BUỘC CHIA THEO TỪNG PHẦN, MỖI PHẦN XUỐNG DÒNG):\n"
            "Trong mục 'Prompt:', BẮT BUỘC phải chia theo từng phần rõ ràng, mỗi phần nằm trên một dòng riêng biệt:\n"
            "- Subject: Doanh nhân thành đạt, chuyên gia uy tín (nam/nữ), khuôn mặt dựa trên ảnh tham chiếu bằng {output_language}.\n"
            "- Pose: Tư thế tự tin, đĩnh đạc, khoanh tay nhẹ hoặc một tay trong túi, tư thế đứng/ngồi sang trọng bằng {output_language}.\n"
            "- Expression: Nụ cười thân thiện, ánh mắt kiên định nhìn thẳng vào ống kính bằng {output_language}.\n"
            "- Clothing: Vest / blazer may đo cao cấp, áo sơ mi trang nhã, đồng hồ tinh tế bằng {output_language}.\n"
            "- Background: Văn phòng hiện đại, tòa nhà kính, phòng hội nghị sang trọng với hậu cảnh làm mờ bokeh dịu mắt bằng {output_language}.\n"
            "- Lighting: Ánh sáng cửa sổ tự nhiên kết hợp softbox studio dịu nhẹ, nhiệt độ màu trung tính ấm bằng {output_language}.\n"
            "- Camera: Trung cận cảnh (medium close-up), ngang tầm mắt (eye-level) sắc nét bằng {output_language}.\n"
            "- Style: Nhiếp ảnh thương mại chân thực, đẳng cấp doanh nghiệp bằng {output_language}.\n\n"
            "NGÔN NGỮ ĐẦU RA:\n"
            "- Cả 5 Tiêu đề và Nội dung Prompt BẮT BUỘC viết bằng: {output_language}.\n"
            "- Slug: là slug URL chuẩn SEO viết thường, không dấu, ngăn cách bằng dấu gạch ngang (-).\n\n"
            "ĐỊNH DẠNG TRẢ VỀ:\n"
            "Title:\n"
            "1. <Tiêu đề 1 dưới 80 ký tự>\n"
            "2. <Tiêu đề 2 dưới 80 ký tự>\n"
            "3. <Tiêu đề 3 dưới 80 ký tự>\n"
            "4. <Tiêu đề 4 dưới 80 ký tự>\n"
            "5. <Tiêu đề 5 dưới 80 ký tự>\n\n"
            "Slug:\n"
            "1. <slug-tieu-de-1>\n"
            "2. <slug-tieu-de-2>\n"
            "3. <slug-tieu-de-3>\n"
            "4. <slug-tieu-de-4>\n"
            "5. <slug-tieu-de-5>\n\n"
            "Prompt:\n"
            "Subject: <mô tả>\n"
            "Pose: <mô tả>\n"
            "Expression: <mô tả>\n"
            "Clothing: <mô tả>\n"
            "Background: <mô tả>\n"
            "Lighting: <mô tả>\n"
            "Camera: <mô tả>\n"
            "Style: <mô tả>"
        ),
        "is_default": False,
        "created_at": current_timestamp_str(),
        "updated_at": current_timestamp_str(),
    },
    {
        "id": 4,
        "name": "Nhiếp ảnh Đường phố Điện ảnh (Cinematic Street Style)",
        "description": "Khoảnh khắc đời thường sống động ngoài trời, ánh sáng tự nhiên hoàng hôn rực rỡ, màu sắc phim điện ảnh cổ điển và độ sâu trường ảnh sâu.",
        "category": "Điện ảnh",
        "language": "pt-BR",
        "aspect_ratio_mode": "none",
        "target_aspect_ratio": "4:5",
        "prompt_content": (
            "Dịch ngược bức ảnh thành prompt ảnh đường phố điện ảnh (Cinematic Street Portrait / Film Aesthetic).\n\n"
            "YÊU CẦU QUAN TRỌNG VỀ KHUÔN MẶT THAM CHIẾU:\n"
            "Khuôn mặt và đường nét nhận diện của nhân vật (nam hoặc nữ) BẮT BUỘC phải dựa chính xác trên ảnh tham chiếu đính kèm "
            "(o rosto e os traços faciais devem ser exatamente baseados na imagem de referência anexada). "
            "Không mô tả chi tiết khuôn mặt gốc để người dùng dễ thay thế.\n\n"
            "GỢI Ý 5 TIÊU ĐỀ CHO PROMPT & SLUG (TỐI ƯU SEO):\n"
            "Gợi ý 5 tiêu đề ảnh đường phố bằng {output_language}, mỗi tiêu đề BẮT BUỘC DƯỚI 80 KÝ TỰ:\n"
            "[Loại ảnh: Retrato Urbano / Estilo de Rua] + [Chủ thể: Feminina / Masculino] + [Bối cảnh đường phố/Thời khắc]\n\n"
            "CẤU TRÚC PHẦN PROMPT (BẮT BUỘC CHIA THEO TỪNG PHẦN, MỖI PHẦN XUỐNG DÒNG):\n"
            "Trong mục 'Prompt:', BẮT BUỘC phải chia theo từng phần rõ ràng, mỗi phần nằm trên một dòng riêng biệt:\n"
            "- Subject: Nhân vật phong cách (nam/nữ), khuôn mặt dựa trên ảnh tham chiếu bằng {output_language}.\n"
            "- Pose: Tư thế tự nhiên khi sải bước trên phố, dừng chân ngắm cảnh hoặc quay đầu nhìn camera bằng {output_language}.\n"
            "- Expression: Biểu cảm tự nhiên, ánh mắt giàu cảm xúc hoặc suy tư bằng {output_language}.\n"
            "- Clothing: Phong cách thời trang dạo phố (streetwear), áo khoác sành điệu, khăn choàng hoặc túi xách bằng {output_language}.\n"
            "- Background: Đại lộ nhộn nhịp, góc quán cà phê ngoài trời, đèn phố lung linh, hiệu ứng mờ nhòe quang sai màu (chromatic bokeh) bằng {output_language}.\n"
            "- Lighting: Ánh sáng giờ vàng (golden hour) ấm áp hoặc ánh sáng chiều tà phản chiếu lung linh bằng {output_language}.\n"
            "- Camera: Toàn thân hoặc 3/4 người, ống kính 35mm hoặc 50mm f/1.8 tạo cảm giác điện ảnh bằng {output_language}.\n"
            "- Style: Phong cách phim 35mm chân thực, hạt phim mịn (fine grain), độ phân giải cao bằng {output_language}.\n\n"
            "NGÔN NGỮ ĐẦU RA:\n"
            "- Cả 5 Tiêu đề và Nội dung Prompt BẮT BUỘC viết bằng: {output_language}.\n"
            "- Slug: là slug URL chuẩn SEO viết thường, không dấu, ngăn cách bằng dấu gạch ngang (-).\n\n"
            "ĐỊNH DẠNG TRẢ VỀ:\n"
            "Title:\n"
            "1. <Tiêu đề 1 dưới 80 ký tự>\n"
            "2. <Tiêu đề 2 dưới 80 ký tự>\n"
            "3. <Tiêu đề 3 dưới 80 ký tự>\n"
            "4. <Tiêu đề 4 dưới 80 ký tự>\n"
            "5. <Tiêu đề 5 dưới 80 ký tự>\n\n"
            "Slug:\n"
            "1. <slug-tieu-de-1>\n"
            "2. <slug-tieu-de-2>\n"
            "3. <slug-tieu-de-3>\n"
            "4. <slug-tieu-de-4>\n"
            "5. <slug-tieu-de-5>\n\n"
            "Prompt:\n"
            "Subject: <mô tả>\n"
            "Pose: <mô tả>\n"
            "Expression: <mô tả>\n"
            "Clothing: <mô tả>\n"
            "Background: <mô tả>\n"
            "Lighting: <mô tả>\n"
            "Camera: <mô tả>\n"
            "Style: <mô tả>"
        ),
        "is_default": False,
        "created_at": current_timestamp_str(),
        "updated_at": current_timestamp_str(),
    },
    {
        "id": 5,
        "name": "Chụp Ảnh Sản Phẩm & Lookbook Thương Mại (Lookbook)",
        "description": "Ảnh lookbook thương mại sản phẩm sạch sẽ, phông nền studio trung tính, chi tiết trang phục rõ nét, tối ưu cho quảng cáo và e-commerce.",
        "category": "Sản phẩm",
        "language": "pt-BR",
        "aspect_ratio_mode": "none",
        "target_aspect_ratio": "4:5",
        "prompt_content": (
            "Dịch ngược bức ảnh thành prompt ảnh lookbook thương mại (Commercial Product & Fashion Lookbook).\n\n"
            "YÊU CẦU QUAN TRỌNG VỀ KHUÔN MẶT THAM CHIẾU:\n"
            "Khuôn mặt và đường nét nhận diện của người mẫu (nam hoặc nữ) BẮT BUỘC phải dựa chính xác trên ảnh tham chiếu đính kèm "
            "(o rosto e os traços faciais devem ser exatamente baseados na imagem de referência anexada). "
            "Không mô tả chi tiết khuôn mặt gốc để người dùng dễ thay thế.\n\n"
            "GỢI Ý 5 TIÊU ĐỀ CHO PROMPT & SLUG (TỐI ƯU SEO):\n"
            "Gợi ý 5 tiêu đề ảnh lookbook bằng {output_language}, mỗi tiêu đề BẮT BUỘC DƯỚI 80 KÝ TỰ:\n"
            "[Loại ảnh: Lookbook Comercial / Catálogo] + [Chủ thể: Feminina / Masculino] + [Sản phẩm/Phong cách]\n\n"
            "CẤU TRÚC PHẦN PROMPT (BẮT BUỘC CHIA THEO TỪNG PHẦN, MỖI PHẦN XUỐNG DÒNG):\n"
            "Trong mục 'Prompt:', BẮT BUỘC phải chia theo từng phần rõ ràng, mỗi phần nằm trên một dòng riêng biệt:\n"
            "- Subject: Người mẫu lookbook (nam/nữ), khuôn mặt dựa trên ảnh tham chiếu bằng {output_language}.\n"
            "- Pose: Dáng đứng thẳng hoặc nghiêng góc 45 độ làm nổi bật phom dáng trang phục bằng {output_language}.\n"
            "- Expression: Nét mặt trung tính chuyên nghiệp hoặc nụ cười tự nhiên bằng {output_language}.\n"
            "- Clothing: Chi tiết sắc nét từng đường may, chất liệu vải cao cấp, phụ kiện hài hòa bằng {output_language}.\n"
            "- Background: Phông studio tối giản màu be, xám nhạt hoặc trắng sạch sẽ, không có chi tiết thừa bằng {output_language}.\n"
            "- Lighting: Ánh sáng studio đều, tản sáng dịu nhẹ (soft light), không có bóng đổ gắt bằng {output_language}.\n"
            "- Camera: Chụp toàn thân (full body) hoặc 3/4 người, tiêu cự 70-200mm không méo hình bằng {output_language}.\n"
            "- Style: Phong cách chụp hình catalogue thương mại sắc nét, màu sắc chuẩn xác bằng {output_language}.\n\n"
            "NGÔN NGỮ ĐẦU RA:\n"
            "- Cả 5 Tiêu đề và Nội dung Prompt BẮT BUỘC viết bằng: {output_language}.\n"
            "- Slug: là slug URL chuẩn SEO viết thường, không dấu, ngăn cách bằng dấu gạch ngang (-).\n\n"
            "ĐỊNH DẠNG TRẢ VỀ:\n"
            "Title:\n"
            "1. <Tiêu đề 1 dưới 80 ký tự>\n"
            "2. <Tiêu đề 2 dưới 80 ký tự>\n"
            "3. <Tiêu đề 3 dưới 80 ký tự>\n"
            "4. <Tiêu đề 4 dưới 80 ký tự>\n"
            "5. <Tiêu đề 5 dưới 80 ký tự>\n\n"
            "Slug:\n"
            "1. <slug-tieu-de-1>\n"
            "2. <slug-tieu-de-2>\n"
            "3. <slug-tieu-de-3>\n"
            "4. <slug-tieu-de-4>\n"
            "5. <slug-tieu-de-5>\n\n"
            "Prompt:\n"
            "Subject: <mô tả>\n"
            "Pose: <mô tả>\n"
            "Expression: <mô tả>\n"
            "Clothing: <mô tả>\n"
            "Background: <mô tả>\n"
            "Lighting: <mô tả>\n"
            "Camera: <mô tả>\n"
            "Style: <mô tả>"
        ),
        "is_default": False,
        "created_at": current_timestamp_str(),
        "updated_at": current_timestamp_str(),
    },
]


class PromptTemplateRepository(BaseMongoRepository):
    """Repository handling CRUD operations for Prompt Templates in MongoDB."""

    def __init__(self) -> None:
        super().__init__(collection_name=PROMPT_TEMPLATE_COLLECTION, id_field="id")

    async def ensure_seeded(self, db: Optional[Any] = None) -> None:
        """Seed initial templates if collection is empty."""
        try:
            await self.seed_if_empty(
                default_items=INITIAL_TEMPLATES,
                index_specs=["name", "category", "is_default"],
                db=db,
            )
        except Exception as exc:
            logger.warning(f"Failed to seed prompt templates: {exc}")

    async def get_all_templates(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve list of prompt templates with optional search and category filters."""
        await self.ensure_seeded(db=db)

        query: Dict[str, Any] = {}
        if category and category != "all":
            query["category"] = category
        if search and search.strip():
            s = search.strip()
            query["$or"] = [
                {"name": {"$regex": s, "$options": "i"}},
                {"description": {"$regex": s, "$options": "i"}},
                {"prompt_content": {"$regex": s, "$options": "i"}},
            ]

        # Prioritize default template first, then descending by id
        items, _ = await self.find_all(
            query=query,
            sort_field="is_default",
            sort_dir=-1,
            limit=1000,
            db=db,
        )

        # In-memory sorting secondary by updated_at or id
        return sorted(items, key=lambda x: (not x.get("is_default", False), -int(x.get("id", 0))))

    async def get_template_by_id(self, template_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Get a specific template by its ID."""
        await self.ensure_seeded(db=db)
        return await self.find_by_id(template_id, db=db)

    async def get_default_template(self, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Find the designated default template."""
        await self.ensure_seeded(db=db)
        found = await self.find_one({"is_default": True}, db=db)
        if not found:
            items = await self.get_all_templates(db=db)
            if items:
                return items[0]
        return found

    async def create_template(self, data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
        """Create a new prompt template. If is_default is True, reset other defaults."""
        await self.ensure_seeded(db=db)

        if data.get("is_default"):
            await self._clear_other_defaults(db=db)

        # Generate unique auto-increment id
        items, _ = await self.find_all(limit=1000, db=db)
        max_id = max([int(x.get("id", 0)) for x in items], default=0)
        data["id"] = max_id + 1

        created = await self.insert(data, db=db)
        return created

    async def update_template(
        self,
        template_id: int,
        data: Dict[str, Any],
        db: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing prompt template."""
        await self.ensure_seeded(db=db)

        if data.get("is_default"):
            await self._clear_other_defaults(exclude_id=template_id, db=db)

        updated = await self.update(template_id, data, db=db)
        return updated

    async def delete_template(self, template_id: int, db: Optional[Any] = None) -> bool:
        """Delete a prompt template by ID."""
        await self.ensure_seeded(db=db)
        return await self.delete(template_id, db=db)

    async def set_default_template(self, template_id: int, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Set a given template as the default and unset all others."""
        await self.ensure_seeded(db=db)
        await self._clear_other_defaults(exclude_id=template_id, db=db)
        return await self.update(template_id, {"is_default": True}, db=db)

    async def _clear_other_defaults(self, exclude_id: Optional[int] = None, db: Optional[Any] = None) -> None:
        """Helper to ensure only one template is marked as is_default."""
        col = self.get_collection(db)
        if col is not None:
            query: Dict[str, Any] = {"is_default": True}
            if exclude_id is not None:
                query["id"] = {"$ne": exclude_id}
            try:
                await col.update_many(query, {"$set": {"is_default": False, "updated_at": current_timestamp_str()}})
            except Exception as e:
                logger.warning(f"Error resetting is_default flags: {e}")

        # Sync fallback memory cache
        for item in self._memory_cache:
            if exclude_id is None or item.get("id") != exclude_id:
                item["is_default"] = False

    async def reset_defaults(self, db: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Reset collection to initial built-in templates."""
        col = self.get_collection(db)
        if col is not None:
            try:
                await col.delete_many({})
            except Exception as e:
                logger.warning(f"Error clearing collection for reset: {e}")
        self._memory_cache = []
        self._initialized = False
        await self.seed_if_empty(INITIAL_TEMPLATES, db=db)
        return await self.get_all_templates(db=db)


# Global singleton instance
prompt_template_repo = PromptTemplateRepository()
