import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.infill import InfillSelection
from app.models.geometry import GeometryAnalysis
from app.models.material import Material
from app.models.material_family import MaterialFamily
from app.schemas.infill import InfillRequest, InfillResponse, InfillOptionsResponse, InfillOptionItem
from app.utils.infill_engine import (
    InfillProfile, INFILL_FACTORS, INFILL_LABELS,
    calculate_infill,
)

logger = logging.getLogger("trid")

RESIN_FAMILY_SLUG = "resin"


async def _get_model_volume(model_id: str, db: AsyncSession) -> float:
    res = await db.execute(select(GeometryAnalysis).where(
        GeometryAnalysis.model_id == model_id,
        GeometryAnalysis.analysis_status == "completed",
    ))
    geo = res.scalar_one_or_none()
    if not geo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geometry analysis must be completed before infill calculation.",
        )
    return geo.volume


async def _is_resin_material(material_slug: str, db: AsyncSession) -> bool:
    res = await db.execute(
        select(Material, MaterialFamily)
        .join(MaterialFamily, Material.family_id == MaterialFamily.id)
        .where(Material.slug == material_slug, Material.is_active == True)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Material '{material_slug}' not found.")
    _, fam = row
    return fam.slug == RESIN_FAMILY_SLUG


async def calculate_and_save_infill(
    model_id: str,
    request: InfillRequest,
    db: AsyncSession,
) -> InfillResponse:

    model_volume = await _get_model_volume(model_id, db)
    is_resin     = await _is_resin_material(request.material_slug, db)

    profile = InfillProfile.solid if is_resin else (request.infill_profile or InfillProfile.standard)
    result  = calculate_infill(model_volume, profile, is_resin=is_resin)

    # Upsert per model+material
    existing = await db.execute(select(InfillSelection).where(
        InfillSelection.model_id == model_id,
        InfillSelection.material_slug == request.material_slug,
    ))
    record = existing.scalar_one_or_none()

    if not record:
        record = InfillSelection(model_id=model_id, material_slug=request.material_slug)
        db.add(record)

    record.infill_profile           = result.infill_profile.value
    record.infill_percentage        = result.infill_percentage
    record.infill_factor            = result.infill_factor
    record.model_volume             = result.model_volume
    record.effective_model_material = result.effective_model_material
    record.is_resin                 = result.is_resin

    await db.flush()
    await db.refresh(record)

    logger.info(
        f"Infill [{model_id}] material={request.material_slug} "
        f"profile={result.infill_profile} eff={result.effective_model_material} mm³ resin={is_resin}"
    )
    return InfillResponse.from_orm_model(record)


async def get_infill(model_id: str, material_slug: str, db: AsyncSession) -> InfillResponse:
    res = await db.execute(select(InfillSelection).where(
        InfillSelection.model_id == model_id,
        InfillSelection.material_slug == material_slug,
    ))
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infill selection not found.")
    return InfillResponse.from_orm_model(record)


def get_infill_options() -> InfillOptionsResponse:
    return InfillOptionsResponse(options=[
        InfillOptionItem(
            profile=p.value,
            percentage=int(p.value),
            label=INFILL_LABELS[p],
            factor=INFILL_FACTORS[p],
        )
        for p in InfillProfile
    ])
