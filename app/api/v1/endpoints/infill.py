from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.infill import InfillRequest
from app.services.infill_service import calculate_and_save_infill, get_infill, get_infill_options

router = APIRouter()


@router.get("/infill/options", response_model=APIResponse)
async def list_infill_options():
    data = get_infill_options()
    return APIResponse(data=data.model_dump())


@router.post("/infill/{model_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def set_infill(
    model_id: str,
    body: InfillRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await calculate_and_save_infill(model_id, body, db)
    return APIResponse(message="Infill calculated.", data=result.model_dump())


@router.get("/infill/{model_id}/{material_slug}", response_model=APIResponse)
async def fetch_infill(model_id: str, material_slug: str, db: AsyncSession = Depends(get_db)):
    result = await get_infill(model_id, material_slug, db)
    return APIResponse(data=result.model_dump())
