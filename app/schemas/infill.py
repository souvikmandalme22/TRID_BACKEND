from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.utils.infill_engine import InfillProfile, INFILL_LABELS


class InfillRequest(BaseModel):
    material_slug:  str
    infill_profile: Optional[InfillProfile] = InfillProfile.standard  # ignored for resin

    @field_validator("material_slug")
    @classmethod
    def slug_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("material_slug cannot be empty.")
        return v.strip()


class InfillOptionItem(BaseModel):
    profile:    str
    percentage: int
    label:      str
    factor:     float


class InfillOptionsResponse(BaseModel):
    options: list[InfillOptionItem]


class InfillResponse(BaseModel):
    model_id:                str
    material_slug:           str
    infill_profile:          str
    infill_percentage:       int
    infill_factor:           float
    model_volume:            float
    effective_model_material: float
    is_resin:                bool
    created_at:              datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj) -> "InfillResponse":
        return cls(
            model_id=obj.model_id,
            material_slug=obj.material_slug,
            infill_profile=obj.infill_profile,
            infill_percentage=obj.infill_percentage,
            infill_factor=obj.infill_factor,
            model_volume=obj.model_volume,
            effective_model_material=obj.effective_model_material,
            is_resin=obj.is_resin,
            created_at=obj.created_at,
        )
