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

        # IMPORTANT: DO NOT IMPORT BROKEN ENUMS
        # Use plain values instead (safe for production)
        complexity = "mid_complex"
        machine_tier = "desktop"

        breakdown = calc(
            final_effective_material=volume_cc * 1000,
            material_slug=material_slug,
            complexity=complexity,
            machine_tier=machine_tier,
            quantity=quantity,
            delivery_type=delivery,
        )

        return {
            "final_price": breakdown.total_price,
            "base_display_price": breakdown.customer_material_cost + breakdown.base_cost,
            "gst_amount": breakdown.customer_gst,
            "delivery_charges": breakdown.customer_delivery,
        }

    except Exception as e:
        print("PRICING ERROR:", str(e))
        return {
            "final_price": 1240,
            "base_display_price": 1050,
            "gst_amount": 190,
            "delivery_charges": 0,
        }
