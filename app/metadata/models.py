"""Data models for Metadata management with MongoDB."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CountryModel(BaseModel):
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
        created_at: ISO or formatted creation timestamp
        updated_at: ISO or formatted last update timestamp
    """
    id: int
    name: str
    country_code: str
    phone_code: str
    native_name: Optional[str] = None
    flag_emoji: Optional[str] = "🌐"
    currency_code: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self) -> dict:
        return self.model_dump()
