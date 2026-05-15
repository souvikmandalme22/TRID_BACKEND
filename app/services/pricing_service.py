import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.pricing import PricingSnapshot
from app.models.effective_material import EffectiveMaterial
from app.models.material import Material
from app.schemas.pricing import PricingRequest, PricingBreakdownResponse, PricingPublicResponse
from app.utils.pricing_engine import calculate_price, DeliveryTier

logger = logging.getLogger("trid")


async def _fetch_effective(model_id: str, material_slug: str, db: AsyncSession) -> EffectiveMaterial:
    res = await db.execute(select(EffectiveMaterial).where(
        EffectiveMaterial.model_id == model_id,
        EffectiveMaterial.material_slug == material_slug,
    ))
    rec = res.scalar_one_or_none()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Effective material must be calculated before pricing.",
        )
    return rec


async def _fetch_material(slug: str, db: AsyncSession) -> Material:
    res = await db.execute(select(Material).where(Material.slug == slug, Material.is_active == True))
    mat = res.scalar_one_or_none()
    if not mat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Material '{slug}' not found.")
    return mat


async def calculate_and_save_price(
    model_id: str,
    request: PricingRequest,
    db: AsyncSession,
) -> PricingSnapshot:

    effective = await _fetch_effective(model_id, request.material_slug, db)
    material  = await _fetch_material(request.material_slug, db)

    breakdown = calculate_price(
        final_effective_material_mm3=effective.final_effective_material,
        price_per_cc=material.price_per_cc,
        quantity=request.quantity,
        delivery_tier=request.delivery_tier,
    )

    # Upsert snapshot per model+material+qty+delivery
    existing = await db.execute(select(PricingSnapshot).where(
        PricingSnapshot.model_id == model_id,
        PricingSnapshot.material_slug == request.material_slug,
    ))
    record = existing.scalar_one_or_none()
    if not record:
        record = PricingSnapshot(model_id=model_id, material_slug=request.material_slug)
        db.add(record)

    record.final_effective_material_mm3 = breakdown.final_effective_material_mm3
    record.final_effective_material_cm3 = breakdown.final_effective_material_cm3
    record.price_per_cc                 = breakdown.price_per_cc
    record.quantity                     = breakdown.quantity
    record.material_cost                = breakdown.material_cost
    record.material_cost_total          = breakdown.material_cost_total
    record.base_cost                    = breakdown.base_cost
    record.platform_fee_rate            = breakdown.platform_fee_rate
    record.platform_fee                 = breakdown.platform_fee
    record.delivery_tier                = breakdown.delivery_tier.value
    record.delivery_charge              = breakdown.delivery_charge
    record.subtotal_before_tax          = breakdown.subtotal_before_tax
    record.gst_rate                     = breakdown.gst_rate
    record.gst_amount                   = breakdown.gst_amount
    record.final_price                  = breakdown.final_price

    await db.flush()
    await db.refresh(record)

    logger.info(
        f"Pricing [{model_id}] mat={request.material_slug} qty={request.quantity} "
        f"delivery={request.delivery_tier} final=₹{breakdown.final_price}"
    )
    return record


async def get_pricing_snapshot(model_id: str, material_slug: str, db: AsyncSession) -> PricingSnapshot:
    res = await db.execute(select(PricingSnapshot).where(
        PricingSnapshot.model_id == model_id,
        PricingSnapshot.material_slug == material_slug,
    ))
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing snapshot not found.")
    return record
