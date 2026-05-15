from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation_service import get_recommendations

router = APIRouter()


@router.post("/recommend", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def recommend_materials(
    body: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await get_recommendations(body, db)
    return APIResponse(
        message=f"{len(result.recommended)} material(s) recommended.",
        data=result.model_dump(),
    )
