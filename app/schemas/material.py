from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class MaterialCreate(BaseModel):
    family_id:              UUID
    name:                   str
    short_description:      Optional[str] = None
    price_per_cc:           float
    strength_category:      str           # low / medium / high / ultra
    flexibility_category:   str           # rigid / semi-flex / flexible
    outdoor_suitable:       bool = False
    heat_resistance:        bool = False
    supports_infill:        bool = True
    default_support_density: str = "normal"
    tags:                   Optional[str] = None
    icon_ref:               Optional[str] = None
    sort_order:             int = 0
    is_active:              bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty.")
        return v

    @field_validator("price_per_cc")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price_per_cc must be positive.")
        return v

    @field_validator("strength_category")
    @classmethod
    def valid_strength(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "ultra"}
        if v not in allowed:
            raise ValueError(f"strength_category must be one of {allowed}.")
        return v

    @field_validator("flexibility_category")
    @classmethod
    def valid_flexibility(cls, v: str) -> str:
        allowed = {"rigid", "semi-flex", "flexible"}
        if v not in allowed:
            raise ValueError(f"flexibility_category must be one of {allowed}.")
        return v

    @field_validator("default_support_density")
    @classmethod
    def valid_density(cls, v: str) -> str:
        allowed = {"light", "normal", "dense"}
        if v not in allowed:
            raise ValueError(f"default_support_density must be one of {allowed}.")
        return v


class MaterialUpdate(BaseModel):
    family_id:               Optional[UUID] = None
    name:                    Optional[str] = None
    short_description:       Optional[str] = None
    price_per_cc:            Optional[float] = None
    strength_category:       Optional[str] = None
    flexibility_category:    Optional[str] = None
    outdoor_suitable:        Optional[bool] = None
    heat_resistance:         Optional[bool] = None
    supports_infill:         Optional[bool] = None
    default_support_density: Optional[str] = None
    tags:                    Optional[str] = None
    icon_ref:                Optional[str] = None
    sort_order:              Optional[int] = None
    is_active:               Optional[bool] = None


class MaterialResponse(BaseModel):
    id:                      UUID
    family_id:               UUID
    name:                    str
    slug:                    str
    short_description:       Optional[str]
    price_per_cc:            float
    strength_category:       str
    flexibility_category:    str
    outdoor_suitable:        bool
    heat_resistance:         bool
    supports_infill:         bool
    default_support_density: str
    tags:                    Optional[str]
    icon_ref:                Optional[str]
    sort_order:              int
    is_active:               bool
    created_at:              datetime
    updated_at:              datetime

    class Config:
        from_attributes = True
