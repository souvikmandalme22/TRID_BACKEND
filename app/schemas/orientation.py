from pydantic import BaseModel
from datetime import datetime


class DirectionVector(BaseModel):
    x: float
    y: float
    z: float


class OrientationResultResponse(BaseModel):
    model_id: str
    best_direction: DirectionVector
    support_area: float
    print_height: float
    bed_stability: float
    overhang_risk: float
    orientation_score: float
    n_samples_evaluated: int
    analysis_status: str
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj) -> "OrientationResultResponse":
        return cls(
            model_id=obj.model_id,
            best_direction=DirectionVector(
                x=obj.best_direction_x,
                y=obj.best_direction_y,
                z=obj.best_direction_z,
            ),
            support_area=obj.support_area,
            print_height=obj.print_height,
            bed_stability=obj.bed_stability,
            overhang_risk=obj.overhang_risk,
            orientation_score=obj.orientation_score,
            n_samples_evaluated=obj.n_samples_evaluated,
            analysis_status=obj.analysis_status,
            created_at=obj.created_at,
        )
