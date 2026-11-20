"""Data models for Prompt Templates stored in MongoDB."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class PromptTemplateCreate(BaseModel):
    """Schema for creating a new Prompt Template."""
    name: str = Field(..., min_length=2, max_length=150, description="Tên template")
    description: Optional[str] = Field("", max_length=500, description="Mô tả ngắn về template")
    category: str = Field("Chân dung", max_length=50, description="Danh mục / Thể loại (Chân dung, Thời trang, v.v.)")
    language: str = Field("pt-BR", max_length=10, description="Mã ngôn ngữ prompt sinh ra")
    prompt_content: str = Field(..., min_length=10, description="Nội dung chi tiết của Prompt Template")
    aspect_ratio_mode: Optional[str] = Field("none", description="Chế độ tỷ lệ ảnh (none, natural)")
    target_aspect_ratio: Optional[str] = Field("4:5", description="Tỷ lệ khung hình mục tiêu")
    is_default: bool = Field(False, description="Đặt làm mẫu mặc định")


class PromptTemplateUpdate(BaseModel):
    """Schema for updating an existing Prompt Template."""
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    prompt_content: Optional[str] = Field(None, min_length=10)
    aspect_ratio_mode: Optional[str] = Field(None)
    target_aspect_ratio: Optional[str] = Field(None)
    is_default: Optional[bool] = Field(None)


class PromptTemplateOut(BaseModel):
    """Schema for returning a Prompt Template."""
    id: int
    name: str
    description: str = ""
    category: str = "Chân dung"
    language: str = "pt-BR"
    prompt_content: str
    aspect_ratio_mode: str = "none"
    target_aspect_ratio: str = "4:5"
    is_default: bool = False
    created_at: str = ""
    updated_at: str = ""
