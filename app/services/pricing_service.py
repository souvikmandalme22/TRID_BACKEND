"""
TRID Smart Pricing Engine — UPDATED
app/services/pricing_engine.py

Changes from original Step16_pricing_engine.py:
  1. Added ALL materials to PRICING_CHART (was only PLA)
  2. Added calculate_from_geometry() — new main entry point
     that handles effective volume internally
  3. Machine time cost is added into final price for large parts
  4. Backward-compatible: old calculate_price() still works

Drop this file into app/services/pricing_engine.py
"""

import uuid
import logging
from enum import Enum
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

# Import the volume calculator (new file)
from app.services.effective_volume_calculator import (
    EffectiveVolumeCalculator,
    STLGeometry,
    VolumeResult,
    PartType,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class ComplexityLevel(str, Enum):
    SIMPLE = "simple"

class MachineTier(str, Enum):
    DESKTOP      = "desktop"
    MID_INDUSTRY = "mid_industry"
    INDUSTRY     = "industry"

class DeliveryType(str, Enum):
    STANDARD = "standard"
    EXPRESS  = "express"


# ─────────────────────────────────────────────
# PRICING CHART (₹ per CC)
#
# Logic: rate × effective_CC = material cost
# Effective CC is now calculated properly (hollow/infill-aware)
# so rates do NOT need to be scaled down — they're correct.
#
# (min_rate, max_rate) — mid is used for display, range shown to user
# ─────────────────────────────────────────────

PRICING_CHART: dict = {

    "PLA": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (3,  6),
            MachineTier.MID_INDUSTRY: (10, 18),
            MachineTier.INDUSTRY:     (55, 90),
        },
    },

    "ABS": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (4,  8),
            MachineTier.MID_INDUSTRY: (12, 22),
            MachineTier.INDUSTRY:     (65, 110),
        },
    },

    "PETG": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (5,  9),
            MachineTier.MID_INDUSTRY: (14, 24),
            MachineTier.INDUSTRY:     (70, 120),
        },
    },

    "TPU": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (8,  14),
            MachineTier.MID_INDUSTRY: (20, 35),
            MachineTier.INDUSTRY:     (90, 150),
        },
    },

    "NYLON_PA12": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (15, 25),
            MachineTier.MID_INDUSTRY: (40, 70),
            MachineTier.INDUSTRY:     (150, 250),
        },
    },

    "RESIN": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (10, 18),
            MachineTier.MID_INDUSTRY: (30, 55),
            MachineTier.INDUSTRY:     (120, 200),
        },
    },
}


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

GST_RATE   = Decimal("0.18")
BASE_COST  = Decimal("50")

DELIVERY_CHARGES = {
    DeliveryType.STANDARD: Decimal("0"),
    DeliveryType.EXPRESS:  Decimal("149"),
}

# Machine time is added for large parts (machine time cost from volume calculator)
# This ensures large hollow parts are priced correctly even at low CC rates
MACHINE_TIME_COST_THRESHOLD_CC = 500.0  # above this CC → add machine time component


# ─────────────────────────────────────────────
# REQUEST SCHEMA
# ─────────────────────────────────────────────

class PricingRequest(BaseModel):
    model_id:                    str
    material_key:                str
    complexity:                  ComplexityLevel
    machine_tier:                MachineTier
    final_effective_material_cc: float
    quantity:                    int = Field(default=1, ge=1)
    delivery_type:               DeliveryType = DeliveryType.STANDARD
    # Optional — passed from VolumeResult if using calculate_from_geometry()
    machine_time_cost_inr:       float = 0.0
    print_time_hrs:              float = 0.0
    part_type:                   str = "solid"


# ─────────────────────────────────────────────
# RESPONSE SCHEMA
# ─────────────────────────────────────────────

class PricingResult(BaseModel):
    snapshot_id:        str
    model_id:           str
    material_key:       str
    complexity:         str
    machine_tier:       str
    quantity:           int
    delivery_type:      str

    material_cc:        float
    material_grams:     float
    print_time_hrs:     float
    part_type:          str

    material_cost:      float   # CC × rate
    machine_time_cost:  float   # print time × hourly rate
    platform_fee:       float
    base_cost:          float
    gst_amount:         float
    delivery_charges:   float

    base_display_price: float   # subtotal before GST
    final_price:        float   # total for 1 unit
    final_price_total:  float   # × quantity

    price_range_min:    float
    price_range_max:    float

    is_estimated:       bool = True
    confidence_level:   str  = "approximate"
    tooltip:            str  = "All values are approximate and may vary based on machine settings"
    created_at:         datetime


# ─────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────

class PricingEngine:

    _vol_calc = EffectiveVolumeCalculator()

    # ── NEW: Main entry point from STL geometry ────────────────────────────

    def calculate_from_geometry(
        self,
        geom: STLGeometry,
        model_id: str,
        complexity: ComplexityLevel,
        quantity: int = 1,
        delivery_type: DeliveryType = DeliveryType.STANDARD,
    ) -> PricingResult:
        """
        PREFERRED method. Takes raw STL geometry + user params.
        Internally computes correct effective volume, then prices.

        Usage in your upload/pricing route:
            result = PricingEngine().calculate_from_geometry(
                geom          = stl_geom,
                model_id      = str(model.id),
                complexity    = detected_complexity,
                quantity      = order.quantity,
                delivery_type = DeliveryType.STANDARD,
            )
        """
        vol: VolumeResult = self._vol_calc.calculate(geom)

        req = PricingRequest(
            model_id                    = model_id,
            material_key                = geom.material_key,
            complexity                  = complexity,
            machine_tier                = MachineTier(geom.machine_tier),
            final_effective_material_cc = vol.final_effective_material_cc,
            quantity                    = quantity,
            delivery_type               = delivery_type,
            machine_time_cost_inr       = vol.machine_time_cost_inr,
            print_time_hrs              = vol.print_time_hrs,
            part_type                   = vol.part_type.value,
        )
        return self._build_result(req)

    # ── ORIGINAL: Direct call (backward-compatible) ───────────────────────

    def calculate_price(self, request: PricingRequest) -> PricingResult:
        """
        Original method — still works if you pass final_effective_material_cc
        from outside. Now also accepts machine_time_cost_inr in request.
        """
        return self._build_result(request)

    # ── INTERNAL ──────────────────────────────────────────────────────────

    def _build_result(self, req: PricingRequest) -> PricingResult:
        min_r, max_r = self._get_rate(req.material_key, req.complexity, req.machine_tier)
        mid_r = (min_r + max_r) / 2

        cc = Decimal(str(req.final_effective_material_cc))

        # Material cost
        material_cost = (cc * Decimal(str(mid_r))).quantize(Decimal("0.01"))

        # Machine time cost (critical for large parts)
        machine_cost = Decimal(str(req.machine_time_cost_inr)).quantize(Decimal("0.01"))

        platform_fee, _ = self._platform_fee(material_cost + machine_cost)
        delivery         = DELIVERY_CHARGES[req.delivery_type]

        subtotal = material_cost + machine_cost + BASE_COST + platform_fee + delivery
        gst      = (subtotal * GST_RATE).quantize(Decimal("0.01"))
        final    = subtotal + gst

        qty          = Decimal(str(req.quantity))
        final_total  = (final * qty).quantize(Decimal("0.01"))

        # Price range (without machine cost for simplicity of range display)
        range_min = float((cc * Decimal(str(min_r)) + BASE_COST) * (1 + GST_RATE))
        range_max = float((cc * Decimal(str(max_r)) + BASE_COST) * (1 + GST_RATE))

        grams = self._to_grams(req.material_key, float(cc))

        return PricingResult(
            snapshot_id        = str(uuid.uuid4()),
            model_id           = req.model_id,
            material_key       = req.material_key,
            complexity         = req.complexity.value,
            machine_tier       = req.machine_tier.value,
            quantity           = req.quantity,
            delivery_type      = req.delivery_type.value,
            material_cc        = float(cc),
            material_grams     = grams,
            print_time_hrs     = req.print_time_hrs,
            part_type          = req.part_type,
            material_cost      = float(material_cost),
            machine_time_cost  = float(machine_cost),
            platform_fee       = float(platform_fee),
            base_cost          = float(BASE_COST),
            gst_amount         = float(gst),
            delivery_charges   = float(delivery),
            base_display_price = float(subtotal),
            final_price        = float(final),
            final_price_total  = float(final_total),
            price_range_min    = round(range_min, 2),
            price_range_max    = round(range_max, 2),
            created_at         = datetime.utcnow(),
        )

    # ── HELPERS ───────────────────────────────────────────────────────────

    def _get_rate(
        self, material_key: str, complexity: ComplexityLevel, machine_tier: MachineTier
    ) -> tuple[float, float]:
        key = material_key.upper()
        if key not in PRICING_CHART:
            raise ValueError(f"Material '{key}' not in pricing chart. "
                             f"Supported: {list(PRICING_CHART)}")
        return PRICING_CHART[key][complexity][machine_tier]

    def _platform_fee(self, cost: Decimal) -> tuple[Decimal, float]:
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

    def _to_grams(self, material_key: str, cc: float) -> float:
        density = {
            "PLA":        1.24,
            "ABS":        1.04,
            "PETG":       1.27,
            "TPU":        1.20,
            "NYLON_PA12": 1.01,
            "RESIN":      1.10,
        }
        return round(cc * density.get(material_key.upper(), 1.0), 2)
