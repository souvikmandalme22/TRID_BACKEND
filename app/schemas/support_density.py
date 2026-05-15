from pydantic import BaseModel, field_validator
from datetime import datetime
from app.utils.support_density import MaterialCategory, SupportDensityProfile


class SupportDensityRequest(BaseModel):
    material_category: MaterialCategory
    density_profile: SupportDensityProfile = SupportDensityProfile.normal


class SupportDensityResponse(BaseModel):
    model_id: str
    raw_support_volume: float
    density_profile: str
    material_category: str
    density_factor: float
    effective_support_material: float
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj) -> "SupportDensityResponse":
        return cls(
            model_id=obj.model_id,
            raw_support_volume=obj.raw_support_volume,
            density_profile=obj.density_profile,
            material_category=obj.material_category,
            density_factor=obj.density_factor,
            effective_support_material=obj.effective_support_material,
            created_at=obj.created_at,
        )
