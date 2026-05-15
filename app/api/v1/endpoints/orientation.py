from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.services.orientation_service import run_orientation_analysis, get_orientation_by_model_id

router = APIRouter()


@router.post("/orientation/{model_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def analyse_orientation(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await run_orientation_analysis(model_id, db)
    return APIResponse(message="Orientation analysis complete.", data=result.model_dump())


@router.get("/orientation/{model_id}", response_model=APIResponse)
async def get_orientation(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_orientation_by_model_id(model_id, db)
    return APIResponse(data=result.model_dump())
