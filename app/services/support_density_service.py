import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.support import SupportAnalysis
from app.models.support_density import SupportDensityResult
from app.schemas.support_density import SupportDensityRequest, SupportDensityResponse
from app.utils.support_density import (
    MaterialCategory,
    SupportDensityProfile,
    calculate_support_density,
)

logger = logging.getLogger("trid")


async def run_support_density(
    model_id: str,
    request: SupportDensityRequest,
    db: AsyncSession,
) -> SupportDensityResponse:

    # Require support analysis first
    res = await db.execute(select(SupportAnalysis).where(SupportAnalysis.model_id == model_id))
    support = res.scalar_one_or_none()
    if not support or support.analysis_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support analysis must be completed before density calculation.",
        )

    result = calculate_support_density(
        raw_support_volume=support.raw_support_volume,
        material_category=request.material_category,
        density_profile=request.density_profile,
    )

    # Upsert — recalculate if params change
    existing = await db.execute(select(SupportDensityResult).where(SupportDensityResult.model_id == model_id))
    record = existing.scalar_one_or_none()

    if not record:
        record = SupportDensityResult(model_id=model_id)
        db.add(record)

    record.raw_support_volume         = result.raw_support_volume
    record.density_profile            = result.density_profile.value
    record.material_category          = result.material_category.value
    record.density_factor             = result.density_factor
    record.effective_support_material = result.effective_support_material

    await db.flush()
    await db.refresh(record)

    logger.info(
        f"Support density [{model_id}]: {result.density_profile} | "
        f"factor={result.density_factor} | eff={result.effective_support_material} mm³"
    )
    return SupportDensityResponse.from_orm_model(record)


async def get_support_density(model_id: str, db: AsyncSession) -> SupportDensityResponse:
    result = await db.execute(select(SupportDensityResult).where(SupportDensityResult.model_id == model_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support density result not found.")
    return SupportDensityResponse.from_orm_model(record)
