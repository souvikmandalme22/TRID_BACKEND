from pydantic import BaseModel, field_validator
from uuid import UUID
from typing import List, Optional


class RecommendationRequest(BaseModel):
    segment_slug:      str
    use_case_slug:     str
    family_slug:       Optional[str] = None        # filter by family (optional)
    environment_tags:  List[str] = []              # ["indoor","outdoor","near-heat"]

    @field_validator("environment_tags", mode="before")
    @classmethod
    def lowercase_tags(cls, v):
        return [t.lower().strip() for t in v]


class MaterialRecommendation(BaseModel):
    material_id:          UUID
    name:                 str
    slug:                 str
    family_slug:          str
    short_description:    Optional[str]
    price_per_cc:         float
    strength_category:    str
    flexibility_category: str
    tags:                 Optional[str]
    recommendation_score: float
    warnings:             List[str]
    suggestions:          List[str]


class RecommendationResponse(BaseModel):
    segment_slug:     str
    use_case_slug:    str
    environment_tags: List[str]
    recommended:      List[MaterialRecommendation]  # sorted best-first
    global_warnings:  List[str]
    global_suggestions: List[str]
