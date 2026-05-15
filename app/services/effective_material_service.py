import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.effective_material import EffectiveMaterial
from app.models.geometry import GeometryAnalysis
from app.models.support import SupportAnalysis
from app.models.material import Material
from app.models.material_family import MaterialFamily
from app.schemas.effective_material import EffectiveMaterialRequest, EffectiveMaterialResponse
from app.utils.infill_engine import InfillProfile, INFILL_FACTORS, calculate_infill
from app.utils.support_density import (
    MaterialCategory, SupportDensityProfile, DENSITY_FACTORS, calculate_support_density,
)

logger = logging.getLogger("trid")

RESIN_FAMILY_SLUG = "resin"


async def _fetch_geometry(model_id: str, db: AsyncSession) -> GeometryAnalysis:
    res = await db.execute(select(GeometryAnalysis).where(
        GeometryAnalysis.model_id == model_id,
        GeometryAnalysis.analysis_status == "completed",
    ))
    geo = res.scalar_one_or_none()
    if not geo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geometry analysis must be completed first.",
        )
    return geo


async def _fetch_support(model_id: str, db: AsyncSession) -> SupportAnalysis:
    res = await db.execute(select(SupportAnalysis).where(
        SupportAnalysis.model_id == model_id,
        SupportAnalysis.analysis_status == "completed",
    ))
    sup = res.scalar_one_or_none()
    if not sup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support analysis must be completed first.",
        )
    return sup


async def _fetch_material(slug: str, db: AsyncSession) -> tuple[Material, MaterialFamily]:
    res = await db.execute(
        select(Material, MaterialFamily)
        .join(MaterialFamily, Material.family_id == MaterialFamily.id)
        .where(Material.slug == slug, Material.is_active == True)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Material '{slug}' not found.")
    return row


async def calculate_effective_material(
    model_id: str,
    request: EffectiveMaterialRequest,
    db: AsyncSession,
) -> EffectiveMaterialResponse:

    geo      = await _fetch_geometry(model_id, db)
    sup      = await _fetch_support(model_id, db)
    mat, fam = await _fetch_material(request.material_slug, db)

    is_resin  = fam.slug == RESIN_FAMILY_SLUG
    mat_cat   = MaterialCategory.resin if is_resin else MaterialCategory.filament

    # --- Infill ---
    infill_profile = InfillProfile.solid if is_resin else InfillProfile(request.infill_profile or "20")
    infill_result  = calculate_infill(geo.volume, infill_profile, is_resin=is_resin)

    # --- Support density ---
    density_str  = mat.default_support_density if is_resin else (request.density_profile or "normal")
    try:
        density_profile = SupportDensityProfile(density_str)
    except ValueError:
        density_profile = SupportDensityProfile.normal

    density_result = calculate_support_density(
        raw_support_volume=sup.raw_support_volume,
        material_category=mat_cat,
        density_profile=density_profile,
    )

    # --- Final formula ---
    final = round(infill_result.effective_model_material + density_result.effective_support_material, 4)

    # Upsert
    existing = await db.execute(select(EffectiveMaterial).where(
        EffectiveMaterial.model_id == model_id,
        EffectiveMaterial.material_slug == request.material_slug,
    ))
    record = existing.scalar_one_or_none()
    if not record:
        record = EffectiveMaterial(model_id=model_id, material_slug=request.material_slug)
        db.add(record)

    record.model_volume               = infill_result.model_volume
    record.infill_factor              = infill_result.infill_factor
    record.effective_model_material   = infill_result.effective_model_material
    record.raw_support_volume         = density_result.raw_support_volume
    record.support_density_factor     = density_result.density_factor
    record.effective_support_material = density_result.effective_support_material
    record.final_effective_material   = final
    record.is_resin                   = is_resin

    await db.flush()
    await db.refresh(record)

    logger.info(
        f"EffectiveMaterial [{model_id}] mat={request.material_slug} "
        f"model={infill_result.effective_model_material} + support={density_result.effective_support_material} "
        f"= final={final} mm³"
    )
    return EffectiveMaterialResponse.from_orm_model(record)


async def get_effective_material(model_id: str, material_slug: str, db: AsyncSession) -> EffectiveMaterialResponse:
    res = await db.execute(select(EffectiveMaterial).where(
        EffectiveMaterial.model_id == model_id,
        EffectiveMaterial.material_slug == material_slug,
    ))
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effective material record not found.")
    return EffectiveMaterialResponse.from_orm_model(record)
