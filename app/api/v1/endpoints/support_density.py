from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.support_density import SupportDensityRequest
from app.services.support_density_service import run_support_density, get_support_density

router = APIRouter()


@router.post("/support-density/{model_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def calculate_density(
    model_id: str,
    body: SupportDensityRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await run_support_density(model_id, body, db)
    return APIResponse(message="Support density calculated.", data=result.model_dump())


@router.get("/support-density/{model_id}", response_model=APIResponse)
async def get_density(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_support_density(model_id, db)
    return APIResponse(data=result.model_dump())
