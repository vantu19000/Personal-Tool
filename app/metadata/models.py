"""Data models for Metadata management with MongoDB."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class BaseDocumentModel(BaseModel):
    """Base MongoDB document model for metadata and other system collections."""
    id: Optional[Any] = None
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self) -> dict:
        return self.model_dump()


class CountryModel(BaseDocumentModel):
    """Country metadata model stored in MongoDB collection 'metadata_countries'.

    Fields:
        id: Integer ID
        name: Country common name (e.g. 'Việt Nam', 'Hoa Kỳ')
        country_code: ISO Country Code (e.g. 'VN', 'US', 'JP')
        phone_code: Calling code (e.g. '+84', '+1', '+81')
        native_name: Local language name (e.g. 'Việt Nam', 'United States')
        flag_emoji: Emoji flag symbol (e.g. '🇻🇳', '🇺🇸')
        currency_code: Currency code (e.g. 'VND', 'USD', 'JPY')
        status: 'active' or 'inactive'
        created_at: Formatted creation timestamp
        updated_at: Formatted last update timestamp
    """
    id: int
    name: str
    country_code: str
    phone_code: str
    native_name: Optional[str] = None
    flag_emoji: Optional[str] = "🌐"
    currency_code: Optional[str] = None
    status: str = "active"


class AdministrativeRegionModel(BaseDocumentModel):
    """Administrative Region metadata model stored in collection 'metadata_administrative_regions'.

    8 regions of Vietnam:
    - 1: Đông Bắc Bộ (Northeast)
    - 2: Tây Bắc Bộ (Northwest)
    - 3: Đồng bằng sông Hồng (Red River Delta)
    - 4: Bắc Trung Bộ (North Central Coast)
    - 5: Duyên hải Nam Trung Bộ (South Central Coast)
    - 6: Tây Nguyên (Central Highlands)
    - 7: Đông Nam Bộ (Southeast)
    - 8: Đồng bằng sông Cửu Long (Mekong River Delta)
    """
    id: int
    name: str
    name_en: Optional[str] = None
    code_name: Optional[str] = None
    code_name_en: Optional[str] = None
    status: str = "active"


class AdministrativeUnitModel(BaseDocumentModel):
    """Administrative Unit Level model stored in collection 'metadata_administrative_units'.

    5 administrative unit types in Vietnam's two-tier system:
    - 1: Thành phố trực thuộc trung ương (Municipality)
    - 2: Tỉnh (Province)
    - 3: Phường (Ward)
    - 4: Xã (Commune)
    - 5: Đặc khu tại hải đảo (Special administrative region)
    """
    id: int
    full_name: str
    full_name_en: Optional[str] = None
    short_name: str
    short_name_en: Optional[str] = None
    code_name: Optional[str] = None
    code_name_en: Optional[str] = None
    status: str = "active"


class ProvinceModel(BaseDocumentModel):
    """Province / Municipality metadata model stored in collection 'metadata_provinces'.

    34 provinces & centrally-governed cities:
        id: Integer ID (1..34)
        code: Administrative GSO code (e.g. '01', '79', '31')
        name: Name (e.g. 'Hà Nội', 'Hồ Chí Minh', 'Quảng Ninh')
        name_en: English name (e.g. 'Hanoi', 'Ho Chi Minh')
        full_name: Official full name (e.g. 'Thành phố Hà Nội', 'Tỉnh Cao Bằng')
        full_name_en: Official English name (e.g. 'Hanoi City', 'Cao Bang Province')
        code_name: Slug / code name (e.g. 'ha_noi')
        administrative_unit_id: Reference to AdministrativeUnitModel.id (1: Thành phố TW, 2: Tỉnh)
        administrative_unit_name: Name of unit level (e.g. 'Thành phố trực thuộc trung ương', 'Tỉnh')
        administrative_region_id: Reference to AdministrativeRegionModel.id (1..8)
        region: Region name (e.g. 'Đồng bằng sông Hồng', 'Đông Nam Bộ')
        region_en: Region English name (e.g. 'Red River Delta')
        type: Administrative unit type string ('Thành phố trực thuộc trung ương' or 'Tỉnh')
        postal_code_prefix: Postal prefix range (e.g. '10, 11, 12, 13, 14')
        postal_code: Standard postal code (e.g. '100000')
        phone_code: Landline area phone code (e.g. '024', '028')
        country_code: Country ISO code (default 'VN')
        merged_from: Reorganization note
        wards_count: Total subordinate wards/communes
        status: 'active' or 'inactive'
    """
    id: int
    name: str
    code: str
    name_en: Optional[str] = None
    full_name: Optional[str] = None
    full_name_en: Optional[str] = None
    code_name: Optional[str] = None
    administrative_unit_id: Optional[int] = None
    administrative_unit_name: Optional[str] = None
    administrative_region_id: Optional[int] = None
    country_code: str = "VN"
    type: str = "Tỉnh"
    region: Optional[str] = None
    region_en: Optional[str] = None
    postal_code_prefix: Optional[str] = None
    postal_code: Optional[str] = None
    phone_code: Optional[str] = None
    merged_from: Optional[str] = None
    wards_count: Optional[int] = 0
    status: str = "active"


class WardModel(BaseDocumentModel):
    """Ward / Commune / Island Zone metadata model stored in collection 'metadata_wards'.

    3,321 wards, communes & island special zones across 34 provinces:
        id: Integer ID (1..3321)
        code: Administrative GSO code (e.g. '00004', '31078')
        name: Name (e.g. 'Ba Đình', 'Phú Quốc', 'Trường Sa')
        name_en: English name (e.g. 'Ba Dinh', 'Phu Quoc')
        full_name: Full name with unit (e.g. 'Phường Ba Đình', 'Đặc khu Phú Quốc')
        full_name_en: English full name (e.g. 'Ba Dinh Ward')
        code_name: Slug / code name (e.g. 'ba_dinh')
        type: Classification ('Phường', 'Xã', 'Đặc khu' or 'Đặc khu tại hải đảo')
        administrative_unit_id: Reference to AdministrativeUnitModel.id (3: Phường, 4: Xã, 5: Đặc khu)
        administrative_unit_name: Full unit level name
        province_code: Code mapping to ProvinceModel.code (e.g. '01', '79')
        province_id: Integer ID mapping to ProvinceModel.id
        province_name: Province name (e.g. 'Hà Nội', 'TP. Hà Nội')
        province_full_name: Province full name (e.g. 'Thành phố Hà Nội')
        postal_code: Specific zip code (e.g. '11120')
        old_province_name: Former province name before reorganization (if applicable)
        district_name: Former district name (if applicable)
        merged_note: Reorganization notes
        status: 'active' or 'inactive'
    """
    id: int
    code: str
    name: str
    name_en: Optional[str] = None
    full_name: Optional[str] = None
    full_name_en: Optional[str] = None
    code_name: Optional[str] = None
    type: str = "Xã"
    administrative_unit_id: Optional[int] = None
    administrative_unit_name: Optional[str] = None
    province_id: Optional[int] = None
    province_code: Optional[str] = None
    province_name: Optional[str] = None
    province_full_name: Optional[str] = None
    postal_code: Optional[str] = None
    old_province_name: Optional[str] = None
    district_name: Optional[str] = None
    merged_note: Optional[str] = None
    status: str = "active"
