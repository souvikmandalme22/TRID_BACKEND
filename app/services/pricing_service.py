import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pricing import PricingSnapshot
from app.models.effective_material import EffectiveMaterial
from app.schemas.pricing import PricingRequest
from app.utils.pricing_engine import calculate_price, ComplexityTier, MachineTier

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


async def calculate_and_save_price(
    model_id: str,
    request: PricingRequest,
    db: AsyncSession,
) -> PricingSnapshot:
    effective = await _fetch_effective(model_id, request.material_slug, db)

    breakdown = calculate_price(
        final_effective_material=effective.final_effective_material,
        material_slug=request.material_slug,
        complexity=ComplexityTier.mid_complex,
        machine_tier=MachineTier.desktop,
        quantity=request.quantity,
        delivery_type=request.delivery_tier.value,
    )

    existing = await db.execute(select(PricingSnapshot).where(
        PricingSnapshot.model_id == model_id,
        PricingSnapshot.material_slug == request.material_slug,
    ))
    record = existing.scalar_one_or_none()
    if not record:
        record = PricingSnapshot(model_id=model_id, material_slug=request.material_slug)
        db.add(record)

    record.final_effective_material_mm3 = breakdown.final_effective_material
    record.final_effective_material_cm3 = breakdown.effective_cc
    record.price_per_cc                 = breakdown.material_rate_per_cc
    record.quantity                     = breakdown.quantity
    record.material_cost                = breakdown.material_cost
    record.material_cost_total          = breakdown.customer_material_cost
    record.base_cost                    = breakdown.base_cost
    record.platform_fee_rate            = 0.12
    record.platform_fee                 = breakdown.platform_fee
    record.delivery_tier                = breakdown.delivery_type
    record.delivery_charge              = breakdown.delivery_charge
    record.subtotal_before_tax          = breakdown.subtotal_before_gst
    record.gst_rate                     = 0.18
    record.gst_amount                   = breakdown.gst_amount
    record.final_price                  = breakdown.total_price

    await db.flush()
    await db.refresh(record)

    logger.info(
        f"Pricing [{model_id}] mat={request.material_slug} qty={request.quantity} "
        f"delivery={request.delivery_tier} final=₹{breakdown.total_price}"
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
