"""
TRID Smart Pricing Engine
app/services/pricing_engine.py
"""

import uuid
import logging
from enum import Enum
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class ComplexityLevel(str, Enum):
    SIMPLE = "simple"
    MID_COMPLEX = "mid_complex"
    COMPLEX = "complex"


class MachineTier(str, Enum):
    DESKTOP = "desktop"
    MID_INDUSTRY = "mid_industry"
    INDUSTRY = "industry"


class DeliveryType(str, Enum):
    STANDARD = "standard"
    EXPRESS = "express"


# ─────────────────────────────────────────────
# PRICING CHART (₹ per CC)
# ─────────────────────────────────────────────

PRICING_CHART: dict = {
    "PLA": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (3, 6),
            MachineTier.MID_INDUSTRY: (10, 18),
            MachineTier.INDUSTRY: (55, 90)
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP: (6, 12),
            MachineTier.MID_INDUSTRY: (18, 30),
            MachineTier.INDUSTRY: (90, 150)
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP: (12, 22),
            MachineTier.MID_INDUSTRY: (30, 55),
            MachineTier.INDUSTRY: (150, 250)
        },
    }
}


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

GST_RATE = Decimal("0.18")
BASE_COST = Decimal("50")

DELIVERY_CHARGES = {
    DeliveryType.STANDARD: Decimal("0"),
    DeliveryType.EXPRESS: Decimal("149"),
}


# ─────────────────────────────────────────────
# REQUEST SCHEMA
# ─────────────────────────────────────────────

class PricingRequest(BaseModel):
    model_id: str
    material_key: str
    complexity: ComplexityLevel
    machine_tier: MachineTier
    final_effective_material_cc: float
    quantity: int = Field(default=1, ge=1)
    delivery_type: DeliveryType = DeliveryType.STANDARD


# ─────────────────────────────────────────────
# RESPONSE SCHEMA (CUSTOMER)
# ─────────────────────────────────────────────

class PricingResult(BaseModel):
    snapshot_id: str
    model_id: str
    material_key: str
    complexity: str
    machine_tier: str
    quantity: int
    delivery_type: str

    material_cc: float
    material_grams: float

    base_display_price: float
    gst_amount: float
    delivery_charges: float
    final_price: float

    price_range_min: float
    price_range_max: float

    is_estimated: bool = True
    confidence_level: str = "approximate"
    tooltip: str = "All values are approximate and may vary based on machine settings"

    created_at: datetime


# ─────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────

class PricingEngine:

    # ── RATE FETCH ──
    def get_material_rate(self, material_key, complexity, machine_tier):
        material_key = material_key.upper()

        if material_key not in PRICING_CHART:
            raise ValueError("Material not supported")

        return PRICING_CHART[material_key][complexity][machine_tier]

    def _mid_rate(self, mn, mx):
        return (mn + mx) / 2

    # ── CC → GRAMS ──
    def convert_cc_to_grams(self, material_key: str, cc: float) -> float:
        density = {
            "PLA": 1.24,
            "ABS": 1.04,
            "PETG": 1.27,
            "TPU": 1.20,
            "NYLON_PA12": 1.01,
        }
        return round(cc * density.get(material_key.upper(), 1.0), 2)

    # ── PLATFORM FEE (PSYCHOLOGY MODEL) ──
    def _calculate_platform_fee(self, cost: Decimal):

        c = float(cost)

        if c <= 300:
            fee = 20
        elif c <= 1500:
            fee = 60
        elif c <= 5000:
            fee = 180
        else:
            fee = min(500, c * 0.05)

        return Decimal(str(fee)).quantize(Decimal("0.01")), 0.0

    # ── MAIN CALC ──
    def calculate_price(self, request: PricingRequest):

        min_r, max_r = self.get_material_rate(
            request.material_key,
            request.complexity,
            request.machine_tier
        )

        rate = self._mid_rate(min_r, max_r)

        cc = Decimal(str(request.final_effective_material_cc))

        material_cost = (cc * Decimal(str(rate))).quantize(Decimal("0.01"))

        base = BASE_COST

        platform_fee, _ = self._calculate_platform_fee(material_cost)

        delivery = DELIVERY_CHARGES[request.delivery_type]

        subtotal = material_cost + base + platform_fee + delivery

        gst = (subtotal * GST_RATE).quantize(Decimal("0.01"))

        final = subtotal + gst

        qty = Decimal(str(request.quantity))

        final_total = (final * qty).quantize(Decimal("0.01"))

        range_min = float((cc * Decimal(str(min_r)) + base) * (1 + GST_RATE))
        range_max = float((cc * Decimal(str(max_r)) + base) * (1 + GST_RATE))

        grams = self.convert_cc_to_grams(
            request.material_key,
            float(cc)
        )

        return PricingResult(
            snapshot_id=str(uuid.uuid4()),
            model_id=request.model_id,
            material_key=request.material_key,
            complexity=request.complexity.value,
            machine_tier=request.machine_tier.value,
            quantity=request.quantity,
            delivery_type=request.delivery_type.value,

            material_cc=float(cc),
            material_grams=grams,

            base_display_price=float(subtotal),
            gst_amount=float(gst),
            delivery_charges=float(delivery),
            final_price=float(final_total),

            price_range_min=round(range_min, 2),
            price_range_max=round(range_max, 2),

            created_at=datetime.utcnow(),
        )
