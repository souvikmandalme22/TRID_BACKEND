from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

VALID_DURABILITY   = {"low", "medium", "high", "extreme"}
VALID_STRENGTH     = {"low", "medium", "high", "ultra"}


class UseCaseCreate(BaseModel):
    name:                 str
    description:          Optional[str] = None
    durability_level:     str
    recommended_strength: str
    sort_order:           int = 0
    is_active:            bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty.")
        return v

    @field_validator("durability_level")
    @classmethod
    def valid_durability(cls, v: str) -> str:
        if v not in VALID_DURABILITY:
            raise ValueError(f"durability_level must be one of {VALID_DURABILITY}.")
        return v

    @field_validator("recommended_strength")
    @classmethod
    def valid_strength(cls, v: str) -> str:
        if v not in VALID_STRENGTH:
            raise ValueError(f"recommended_strength must be one of {VALID_STRENGTH}.")
        return v


class UseCaseUpdate(BaseModel):
    name:                 Optional[str] = None
    description:          Optional[str] = None
    durability_level:     Optional[str] = None
    recommended_strength: Optional[str] = None
    sort_order:           Optional[int] = None
    is_active:            Optional[bool] = None


class UseCaseResponse(BaseModel):
    id:                   UUID
    name:                 str
    slug:                 str
    description:          Optional[str]
    durability_level:     str
    recommended_strength: str
    sort_order:           int
    is_active:            bool
    created_at:           datetime
    updated_at:           datetime

    class Config:
        from_attributes = True
