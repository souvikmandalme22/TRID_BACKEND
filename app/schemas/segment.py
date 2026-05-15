from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
import re


class SegmentCreate(BaseModel):
    name:        str
    icon_ref:    Optional[str] = None
    description: Optional[str] = None
    sort_order:  int = 0
    is_active:   bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty.")
        return v


class SegmentUpdate(BaseModel):
    name:        Optional[str] = None
    icon_ref:    Optional[str] = None
    description: Optional[str] = None
    sort_order:  Optional[int] = None
    is_active:   Optional[bool] = None


class SegmentResponse(BaseModel):
    id:          UUID
    name:        str
    slug:        str
    icon_ref:    Optional[str]
    description: Optional[str]
    sort_order:  int
    is_active:   bool
    created_at:  datetime
    updated_at:  datetime

    class Config:
        from_attributes = True
