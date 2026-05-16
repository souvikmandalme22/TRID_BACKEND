from fastapi import APIRouter, Body
from app.utils.pricing_engine import calculate_price as calc

router = APIRouter()


@router.post("/pricing/quick-calculate")
async def quick_calculate(request: dict = Body(...)):
    try:
        material_slug = request.get("material_key", "pla").lower().replace("_", "-")

        volume_cc = float(request.get("final_effective_material_cc", 10))
        quantity = int(request.get("quantity", 1))
        delivery = request.get("delivery_type", "standard")

        # optional (frontend later send karega)
        infill_percent = int(request.get("infill_percent", 20))

        breakdown = calc(
            model_volume_cc=volume_cc,
            support_volume_cc=0,  # MVP: no support calculation yet
            material_slug=material_slug,
            infill_percent=infill_percent,
            quantity=quantity,
            delivery_tier=delivery,
            complexity_features={},      # MVP safe default
            orientation_analysis={},     # MVP safe default
        )

        return {
            "final_price": breakdown.final_price,
            "base_display_price": breakdown.base_manufacturing_cost,
            "gst_amount": breakdown.gst_amount,
            "delivery_charges": breakdown.delivery_fee,
        }

    except Exception as e:
        print("PRICING ERROR:", str(e))

        return {
            "final_price": 1240,
            "base_display_price": 1050,
            "gst_amount": 190,
            "delivery_charges": 0,
        }
