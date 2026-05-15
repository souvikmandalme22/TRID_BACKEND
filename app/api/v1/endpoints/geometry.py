from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.services.geometry_service import run_geometry_analysis, get_analysis_by_model_id

router = APIRouter()


@router.post("/analyse/{model_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def analyse_model(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await run_geometry_analysis(model_id, db)
    return APIResponse(message="Analysis complete.", data=result.model_dump())


@router.get("/analyse/{model_id}", response_model=APIResponse)
async def get_analysis(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_analysis_by_model_id(model_id, db)
    return APIResponse(data=result.model_dump())
