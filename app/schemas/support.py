from pydantic import BaseModel
from datetime import datetime


class SupportAnalysisResponse(BaseModel):
    model_id: str
    raw_support_volume: float
    support_area: float
    print_height: float
    overhang_face_count: int
    analysis_status: str
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj) -> "SupportAnalysisResponse":
        return cls(
            model_id=obj.model_id,
            raw_support_volume=obj.raw_support_volume,
            support_area=obj.support_area,
            print_height=obj.print_height,
            overhang_face_count=int(obj.overhang_face_count),
            analysis_status=obj.analysis_status,
            created_at=obj.created_at,
        )
