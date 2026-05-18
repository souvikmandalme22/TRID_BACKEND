from fastapi import APIRouter, Body, HTTPException, status
from app.utils.pricing_engine import calculate_price as calc

router = APIRouter()


def _as_float(value, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a number",
        )


def _as_int(value, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be an integer",
        )


@router.post("/pricing/quick-calculate")
async def quick_calculate(request: dict = Body(...)):
    try:
        material_slug = (
            request.get("material_slug") or request.get("material_key") or "pla"
        ).lower().replace("_", "-")

        model_volume_cc = _as_float(
            request.get("model_volume_cc", request.get("final_effective_material_cc")),
            "model_volume_cc",
        )
        support_volume_cc = _as_float(request.get("support_volume_cc", 0), "support_volume_cc")
        quantity          = _as_int(request.get("quantity", 1), "quantity")
        delivery          = request.get("delivery_tier") or request.get("delivery_type") or "standard"
        infill_percent    = _as_int(request.get("infill_percent", 20), "infill_percent")
        machine_tier      = request.get("machine_tier") or "desktop"

        breakdown = calc(
            model_volume_cc=model_volume_cc,
            support_volume_cc=support_volume_cc,
            material_slug=material_slug,
            infill_percent=infill_percent,
            quantity=quantity,
            delivery_tier=delivery,
            complexity_features=request.get("complexity_features") or {},
            orientation_analysis=request.get("orientation_analysis") or {},
            machine_tier=machine_tier,
        )

        return {
            "material_slug":              breakdown.material_slug,
            "machine_tier":               breakdown.machine_tier,
            "complexity_level":           breakdown.complexity_level,
            "model_volume_cc":            breakdown.model_volume_cc,
            "support_volume_cc":          breakdown.support_volume_cc,
            "effective_volume_cc":        breakdown.effective_volume_cc,
            "material_grams":             breakdown.material_grams,
            "material_rate_per_cc":       breakdown.material_rate_per_cc,
            "base_display_price":         breakdown.base_manufacturing_cost,
            "base_manufacturing_cost":    breakdown.base_manufacturing_cost,
            "adjusted_manufacturing_cost": breakdown.adjusted_manufacturing_cost,
            "platform_fee":               breakdown.platform_fee,
            "packaging_fee":              breakdown.packaging_fee,
            "subtotal":                   breakdown.subtotal,
            "gst_amount":                 breakdown.gst_amount,
            "delivery_charges":           breakdown.delivery_fee,
            "delivery_fee":               breakdown.delivery_fee,
            "final_price":                breakdown.final_price,
            "price_range_min":            breakdown.price_range_min,
            "price_range_max":            breakdown.price_range_max,
            "estimated_print_time_hrs":   breakdown.estimated_print_time_hrs,
        }

    except HTTPException:
        raise
    except Exception as e:
        print("PRICING ERROR:", str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Pricing calculation failed: {e}",
        )
