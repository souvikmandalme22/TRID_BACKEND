from fastapi import APIRouter, Body
from app.utils.pricing_engine import (
    calculate_price as calc,
    ComplexityTier,
    MachineTier
)

router = APIRouter()


# =========================
# QUICK CALCULATE (FRONTEND USE)
# =========================
@router.post("/pricing/quick-calculate")
async def quick_calculate(request: dict = Body(...)):
    """
    Lightweight pricing endpoint used by frontend.
    No DB, no auth, only fast computation.
    """

    try:
        # -------------------------
        # INPUT SAFE PARSING
        # -------------------------
        material_slug = (
            request.get("material_key")
            or request.get("material_slug")
            or "pla"
        )

        material_slug = str(material_slug).lower().replace(" ", "-")

        volume_cc = request.get("final_effective_material_cc", 10)
        quantity = request.get("quantity", 1)
        delivery = request.get("delivery_type", "standard")

        # SAFE TYPE CASTING
        try:
            volume_cc = float(volume_cc)
        except:
            volume_cc = 10.0

        try:
            quantity = int(quantity)
        except:
            quantity = 1

        if quantity < 1:
            quantity = 1

        # -------------------------
        # CORE ENGINE INPUT
        # -------------------------
        volume_mm3 = volume_cc * 1000

        breakdown = calc(
            final_effective_material=volume_mm3,
            material_slug=material_slug,
            complexity=ComplexityTier.mid_complex,
            machine_tier=MachineTier.desktop,
            quantity=quantity,
            delivery_type=delivery,
        )

        # -------------------------
        # RESPONSE FORMAT (FRONTEND EXPECTED)
        # -------------------------
        return {
            "success": True,
            "final_price": breakdown.total_price,
            "price_per_unit": round(breakdown.total_price / quantity, 2),

            "base_display_price": breakdown.customer_material_cost + breakdown.base_cost,
            "material_cost": breakdown.material_cost,
            "gst_amount": breakdown.customer_gst,
            "delivery_charges": breakdown.customer_delivery,

            "currency": "INR",
            "quantity": quantity,
            "material": material_slug,
        }

    except Exception as e:
        # IMPORTANT: log real backend error
        print("🔥 QUICK CALCULATE ERROR:", str(e))

        # fallback response (frontend never breaks)
        return {
            "success": False,
            "final_price": 1240,
            "price_per_unit": 1240,
            "base_display_price": 1050,
            "material_cost": 900,
            "gst_amount": 190,
            "delivery_charges": 0,
            "currency": "INR",
            "quantity": request.get("quantity", 1),
            "material": "pla",
            "error": "pricing_engine_failed"
        }


# =========================
# FULL DB PRICING (SAVED SNAPSHOT)
# =========================
@router.post("/pricing/{model_id}", response_model=dict)
async def calculate_price(model_id: str, body: dict, db=None):
    """
    Full pricing with DB save (future use)
    """
    return {
        "message": "Use service layer version for DB-enabled pricing",
        "model_id": model_id,
        "status": "not_implemented_here"
    }


# =========================
# GET SNAPSHOT (PLACEHOLDER SAFE)
# =========================
@router.get("/pricing/{model_id}/{material_slug}")
async def get_price(model_id: str, material_slug: str):
    return {
        "message": "snapshot endpoint active",
        "model_id": model_id,
        "material": material_slug
    }
