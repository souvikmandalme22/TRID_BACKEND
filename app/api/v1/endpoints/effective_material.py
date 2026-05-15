from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.effective_material import EffectiveMaterialRequest
from app.services.effective_material_service import calculate_effective_material, get_effective_material

router = APIRouter()


@router.post("/effective-material/{model_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def calc_effective(
    model_id: str,
    body: EffectiveMaterialRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await calculate_effective_material(model_id, body, db)
    return APIResponse(message="Effective material calculated.", data=result.model_dump())


@router.get("/effective-material/{model_id}/{material_slug}", response_model=APIResponse)
async def fetch_effective(model_id: str, material_slug: str, db: AsyncSession = Depends(get_db)):
    result = await get_effective_material(model_id, material_slug, db)
    return APIResponse(data=result.model_dump())
