from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EffectiveMaterialRequest(BaseModel):
    material_slug:   str
    infill_profile:  Optional[str] = "20"    # ignored for resin
    density_profile: Optional[str] = "normal"


class EffectiveMaterialResponse(BaseModel):
    model_id:                  str
    material_slug:             str
    model_volume:              float
    infill_factor:             float
    effective_model_material:  float
    raw_support_volume:        float
    support_density_factor:    float
    effective_support_material: float
    final_effective_material:  float
    is_resin:                  bool
    created_at:                datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj) -> "EffectiveMaterialResponse":
        return cls(
            model_id=obj.model_id,
            material_slug=obj.material_slug,
            model_volume=obj.model_volume,
            infill_factor=obj.infill_factor,
            effective_model_material=obj.effective_model_material,
            raw_support_volume=obj.raw_support_volume,
            support_density_factor=obj.support_density_factor,
            effective_support_material=obj.effective_support_material,
            final_effective_material=obj.final_effective_material,
            is_resin=obj.is_resin,
            created_at=obj.created_at,
        )
