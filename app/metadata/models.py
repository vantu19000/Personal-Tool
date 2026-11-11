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


class ProvinceModel(BaseDocumentModel):
    """Province / City metadata model stored in MongoDB collection 'metadata_provinces'.

    Fields:
        id: Integer ID
        name: Name of province / municipality (e.g. 'Hà Nội', 'TP. Hồ Chí Minh')
        code: Administrative or short code (e.g. '01', '79', 'HN', 'HCM')
        country_code: Country ISO code (default 'VN')
        type: Administrative unit type (e.g. 'Thành phố Trung ương', 'Tỉnh')
        region: Geographic region (e.g. 'Miền Bắc', 'Miền Trung', 'Miền Nam')
        phone_code: Landline area phone code (e.g. '024', '028', '0236')
        postal_code: Postal zip code (e.g. '100000', '700000')
        status: 'active' or 'inactive'
        created_at: Formatted creation timestamp
        updated_at: Formatted last update timestamp
    """
    id: int
    name: str
    code: str
    country_code: str = "VN"
    type: str = "Tỉnh"
    region: Optional[str] = None
    phone_code: Optional[str] = None
    postal_code: Optional[str] = None
    status: str = "active"

