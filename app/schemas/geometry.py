from pydantic import BaseModel
from datetime import datetime


class BoundingBox(BaseModel):
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float


class Dimensions(BaseModel):
    x: float
    y: float
    z: float


class GeometryAnalysisResponse(BaseModel):
    model_id: str
    dimensions: Dimensions
    bounding_box: BoundingBox
    volume: float
    surface_area: float
    is_watertight: bool
    analysis_status: str
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj) -> "GeometryAnalysisResponse":
        return cls(
            model_id=obj.model_id,
            dimensions=Dimensions(x=obj.dim_x, y=obj.dim_y, z=obj.dim_z),
            bounding_box=BoundingBox(
                min_x=obj.bbox_min_x, min_y=obj.bbox_min_y, min_z=obj.bbox_min_z,
                max_x=obj.bbox_max_x, max_y=obj.bbox_max_y, max_z=obj.bbox_max_z,
            ),
            volume=obj.volume,
            surface_area=obj.surface_area,
            is_watertight=obj.is_watertight,
            analysis_status=obj.analysis_status,
            created_at=obj.created_at,
        )
