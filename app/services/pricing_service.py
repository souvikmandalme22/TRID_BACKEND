import logging

from fastapi import HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pricing import PricingSnapshot
from app.schemas.pricing import PricingRequest

from app.utils.pricing_engine import calculate_price


logger = logging.getLogger("trid")


# =========================================================
# CREATE / UPDATE PRICING
# =========================================================

async def calculate_and_save_price(
    model_id: str,
    request: PricingRequest,
    db: AsyncSession,
) -> PricingSnapshot:

    # =====================================================
    # CALCULATE PRICE
    # =====================================================

    breakdown = calculate_price(
        model_volume_cc=request.model_volume_cc,
        support_volume_cc=request.support_volume_cc,
        material_slug=request.material_slug,
        infill_percent=request.infill_percent,
        quantity=request.quantity,
        delivery_tier=request.delivery_tier.value,
        complexity_features=request.complexity_features.model_dump(),
        orientation_analysis=request.orientation_analysis.model_dump(),
    )

    # =====================================================
    # FIND EXISTING SNAPSHOT
    # =====================================================

    existing = await db.execute(
        select(PricingSnapshot).where(
            PricingSnapshot.model_id == model_id,
            PricingSnapshot.material_slug == request.material_slug,
        )
    )

    record = existing.scalar_one_or_none()

    # =====================================================
    # CREATE NEW
    # =====================================================

    if not record:
        record = PricingSnapshot(
            model_id=model_id,
            material_slug=request.material_slug,
        )

        db.add(record)

    # =====================================================
    # BASIC INPUTS
    # =====================================================

    record.quantity = request.quantity

    record.delivery_tier = request.delivery_tier.value

    # =====================================================
    # GEOMETRY
    # =====================================================

    record.model_volume_cc = request.model_volume_cc

    record.support_volume_cc = request.support_volume_cc

    record.effective_volume_cc = breakdown.effective_volume_cc

    record.infill_percent = request.infill_percent

    record.layer_height = request.layer_height

    record.estimated_print_time_hours = (
        request.estimated_print_time_hours
    )

    # =====================================================
    # COMPLEXITY FLAGS
    # =====================================================

    record.thin_wall = int(
        request.complexity_features.thin_wall
    )

    record.internal_channels = int(
        request.complexity_features.internal_channels
    )

    record.text_or_logo = int(
        request.complexity_features.text_or_logo
    )

    record.high_support = int(
        request.complexity_features.high_support
    )

    record.orientation_sensitive = int(
        request.complexity_features.orientation_sensitive
    )

    record.tiny_features = int(
        request.complexity_features.tiny_features
    )

    record.tolerance_critical = int(
        request.complexity_features.tolerance_critical
    )

    # =====================================================
    # ORIENTATION ANALYSIS
    # =====================================================

    record.stability_score = (
        request.orientation_analysis.stability_score
    )

    record.failure_risk = (
        request.orientation_analysis.failure_risk
    )

    record.tall_geometry = int(
        request.orientation_analysis.tall_geometry
    )

    record.warp_risk = int(
        request.orientation_analysis.warp_risk
    )

    # =====================================================
    # MULTIPLIERS
    # =====================================================

    record.material_rate_per_cc = (
        breakdown.material_rate_per_cc
    )

    record.complexity_multiplier = (
        breakdown.complexity_multiplier
    )

    record.orientation_multiplier = (
        breakdown.orientation_multiplier
    )

    record.support_factor = (
        breakdown.support_factor
    )

    record.infill_factor = (
        breakdown.infill_factor
    )

    # =====================================================
    # COSTS
    # =====================================================

    record.base_manufacturing_cost = (
        breakdown.base_manufacturing_cost
    )

    record.adjusted_manufacturing_cost = (
        breakdown.adjusted_manufacturing_cost
    )

    record.platform_fee = (
        breakdown.platform_fee
    )

    record.packaging_fee = (
        breakdown.packaging_fee
    )

    record.delivery_fee = (
        breakdown.delivery_fee
    )

    record.subtotal = (
        breakdown.subtotal
    )

    record.gst_amount = (
        breakdown.gst_amount
    )

    record.final_price = (
        breakdown.final_price
    )

    # =====================================================
    # SAVE
    # =====================================================

    await db.flush()

    await db.refresh(record)

    # =====================================================
    # LOGGING
    # =====================================================

    logger.info(
        f"""
        Pricing Calculated
        model_id={model_id}
        material={request.material_slug}
        quantity={request.quantity}
        final_price=₹{breakdown.final_price}
        """
    )

    return record


# =========================================================
# GET SNAPSHOT
# =========================================================

async def get_pricing_snapshot(
    model_id: str,
    material_slug: str,
    db: AsyncSession,
) -> PricingSnapshot:

    res = await db.execute(
        select(PricingSnapshot).where(
            PricingSnapshot.model_id == model_id,
            PricingSnapshot.material_slug == material_slug,
        )
    )

    record = res.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing snapshot not found",
        )

    return record
