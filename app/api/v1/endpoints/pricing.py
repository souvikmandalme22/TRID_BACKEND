from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.pricing import PricingRequest, PricingBreakdownResponse, PricingPublicResponse
from app.services.pricing_service import calculate_and_save_price, get_pricing_snapshot

router = APIRouter()


@router.post("/pricing/{model_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def calculate_price(
    model_id: str,
    body: PricingRequest,
    db: AsyncSession = Depends(get_db),
):
    record = await calculate_and_save_price(model_id, body, db)
    # Return customer-visible response only
    return APIResponse(
        message="Price calculated.",
        data=PricingPublicResponse.from_orm_model(record).model_dump(),
    )


@router.get("/pricing/{model_id}/{material_slug}", response_model=APIResponse)
async def get_price(model_id: str, material_slug: str, db: AsyncSession = Depends(get_db)):
    record = await get_pricing_snapshot(model_id, material_slug, db)
    return APIResponse(data=PricingPublicResponse.from_orm_model(record).model_dump())


# Internal/admin route — full breakdown including platform fee
@router.get("/pricing/internal/{model_id}/{material_slug}", response_model=APIResponse)
async def get_price_internal(model_id: str, material_slug: str, db: AsyncSession = Depends(get_db)):
    record = await get_pricing_snapshot(model_id, material_slug, db)
    return APIResponse(data=PricingBreakdownResponse.from_orm_model(record).model_dump())
