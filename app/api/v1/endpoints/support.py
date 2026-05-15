from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.services.support_service import run_support_analysis, get_support_by_model_id

router = APIRouter()


@router.post("/support/{model_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def analyse_support(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await run_support_analysis(model_id, db)
    return APIResponse(message="Support analysis complete.", data=result.model_dump())


@router.get("/support/{model_id}", response_model=APIResponse)
async def get_support(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_support_by_model_id(model_id, db)
    return APIResponse(data=result.model_dump())
