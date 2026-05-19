from dataclasses import dataclass
from typing import Dict
from decimal import Decimal
from enum import Enum
import math

# =========================================================
# ENUMS
# =========================================================

class MachineTier(str, Enum):
    DESKTOP = "desktop"
    MID_INDUSTRY = "mid_industry"
    INDUSTRY = "industry"


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"


# =========================================================
# CONSTANTS
# =========================================================

GST_RATE = Decimal("0.18")
BASE_COST = Decimal("50")
SETUP_OVERHEAD_HRS = 0.5

# realistic machine hourly rates (India market)
MACHINE_HOURLY_RATE = {
    MachineTier.DESKTOP: 35,
    MachineTier.MID_INDUSTRY: 80,
    MachineTier.INDUSTRY: 180,
}


# =========================================================
# SMOOTH MARKET CURVE
# =========================================================

def get_market_anchor_rate(volume_cc: float) -> float:
    return 2.3 * math.exp(-volume_cc / 18000) + 0.65


# =========================================================
# PRICING CHART
# =========================================================

PRICING_CHART: Dict = {
    "pla": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (3, 6),
            MachineTier.MID_INDUSTRY: (10, 18),
            MachineTier.INDUSTRY: (55, 90),
        },
    },
}

DEFAULT_PRICING = {
    ComplexityLevel.SIMPLE: {
        MachineTier.DESKTOP: (10, 20),
        MachineTier.MID_INDUSTRY: (30, 50),
        MachineTier.INDUSTRY: (100, 180),
    },
}

MATERIAL_DENSITY = {
    "pla": 1.24,
}

FLOW_RATE_CC_PER_HR = 18


# =========================================================
# OUTPUT STRUCTURE
# =========================================================

@dataclass
class PriceBreakdown:
    model_volume_cc: float
    support_volume_cc: float
    effective_volume_cc: float

    material_slug: str
    machine_tier: str
    complexity_level: str

    material_rate_per_cc: float
    material_grams: float

    base_manufacturing_cost: float
    market_adjusted_cost: float

    platform_fee: float
    packaging_fee: float
    delivery_fee: float

    subtotal: float
    gst_amount: float
    final_price: float

    estimated_print_time_hrs: float

    complexity_multiplier: float = 1.0
    orientation_multiplier: float = 1.0

    hollowing_applied: bool = False
    hollowing_factor: float = 1.0


# =========================================================
# HELPERS
# =========================================================

def apply_hollowing_factor(volume_cc: float) -> tuple:

    HOLLOWING_THRESHOLD = 5000

    if volume_cc <= HOLLOWING_THRESHOLD:
        return volume_cc, 1.0, False

    if volume_cc <= 10000:
        hollow_factor = 0.25
    elif volume_cc <= 20000:
        hollow_factor = 0.20
    else:
        hollow_factor = 0.15

    effective_volume = volume_cc * hollow_factor

    return effective_volume, hollow_factor, True


def get_infill_factor(infill_percent: int) -> float:
    safe = max(0, min(infill_percent, 100))
    return 0.30 + (0.70 * (safe / 100))


def apply_large_part_discount(rate: float, volume: float) -> float:

    if volume > 30000:
        rate *= 0.50
    elif volume > 20000:
        rate *= 0.60
    elif volume > 10000:
        rate *= 0.72
    elif volume > 5000:
        rate *= 0.85

    return max(round(rate, 2), 0.35)


def get_platform_fee(cost: float) -> float:

    if cost <= 500:
        return 40

    if cost <= 2000:
        return 90

    if cost <= 5000:
        return 180

    if cost <= 15000:
        return 350

    return min(900, cost * 0.03)


def get_packaging_fee(volume: float) -> float:

    if volume > 5000:
        return 120

    if volume > 1000:
        return 60

    if volume > 300:
        return 25

    return 10


def get_delivery_fee(delivery_type: str) -> float:
    return 149 if delivery_type == "express" else 0


def estimate_print_time(volume: float) -> float:
    return round((volume / FLOW_RATE_CC_PER_HR) + SETUP_OVERHEAD_HRS, 2)


# =========================================================
# COMPLEXITY & ORIENTATION MULTIPLIERS
# =========================================================

def calculate_complexity_multiplier(complexity_features: dict) -> float:

    if not complexity_features:
        return 1.0

    multiplier = 1.0

    feature_costs = {
        "thin_wall": 0.05,
        "internal_channels": 0.08,
        "text_or_logo": 0.05,
        "high_support": 0.08,
        "orientation_sensitive": 0.05,
        "tiny_features": 0.08,
        "tolerance_critical": 0.08,
    }

    for feature, cost in feature_costs.items():
        if complexity_features.get(feature, False):
            multiplier += cost

    return round(multiplier, 2)


def calculate_orientation_multiplier(orientation_analysis: dict) -> float:

    if not orientation_analysis:
        return 1.0

    multiplier = 1.0

    if orientation_analysis.get("warp_risk", False):
        multiplier += 0.05

    if orientation_analysis.get("tall_geometry", False):
        multiplier += 0.03

    failure_risk = orientation_analysis.get("failure_risk", 0.0)

    if failure_risk > 0:
        multiplier += (failure_risk * 0.10)

    return round(multiplier, 2)


# =========================================================
# MAIN ENGINE
# =========================================================

def calculate_price(
    model_volume_cc: float,
    support_volume_cc: float,
    material_slug: str,
    infill_percent: int,
    quantity: int,
    machine_tier: str = "desktop",
    delivery_type: str = "standard",
    complexity_features: dict = None,
    orientation_analysis: dict = None,
) -> PriceBreakdown:

    if complexity_features is None:
        complexity_features = {}

    if orientation_analysis is None:
        orientation_analysis = {}

    tier = MachineTier(machine_tier)

    # =====================================================
    # HOLLOWING
    # =====================================================

    model_volume_effective, hollowing_factor, hollowing_applied = apply_hollowing_factor(
        model_volume_cc
    )

    # =====================================================
    # INFILL SAFETY
    # =====================================================

    if model_volume_effective > 5000:
        infill_percent = min(infill_percent, 5)

    infill_factor = get_infill_factor(infill_percent)

    # support should NOT cost full material rate
    support_effective = support_volume_cc * 0.35

    effective_volume = (
        (model_volume_effective * infill_factor)
        + support_effective
    )

    # =====================================================
    # MATERIAL RATE
    # =====================================================

    chart = PRICING_CHART.get(material_slug, DEFAULT_PRICING)

    mn, mx = chart[ComplexityLevel.SIMPLE][tier]

    t = min(max((effective_volume - 50) / 2000, 0), 1)

    rate = mx - (mx - mn) * t

    rate = apply_large_part_discount(rate, effective_volume)

    # =====================================================
    # MATERIAL COST
    # =====================================================

    material_cost = effective_volume * rate

    # =====================================================
    # MACHINE TIME COST
    # =====================================================

    estimated_print_time = estimate_print_time(effective_volume)

    machine_hour_rate = MACHINE_HOURLY_RATE[tier]

    machine_time_cost = estimated_print_time * machine_hour_rate

    # =====================================================
    # MARKET ADJUSTMENT
    # =====================================================

    market_rate = get_market_anchor_rate(effective_volume)

    market_based = effective_volume * market_rate

    # =====================================================
    # HYBRID COST MODEL
    # =====================================================

    adjusted_cost = (
        (material_cost * 0.55)
        + (machine_time_cost * 0.35)
        + (market_based * 0.10)
    )

    adjusted_cost += float(BASE_COST)

    # =====================================================
    # COMPLEXITY MULTIPLIERS
    # =====================================================

    complexity_mult = calculate_complexity_multiplier(
        complexity_features
    )

    orientation_mult = calculate_orientation_multiplier(
        orientation_analysis
    )

    adjusted_cost = (
        adjusted_cost
        * complexity_mult
        * orientation_mult
    )

    # =====================================================
    # ORDER FEES
    # =====================================================

    platform_fee = get_platform_fee(adjusted_cost)

    packaging_fee = get_packaging_fee(effective_volume)

    delivery_fee = get_delivery_fee(delivery_type)

    # =====================================================
    # QUANTITY OPTIMIZATION
    # =====================================================

    if quantity > 1:
        quantity_discount_factor = max(
            0.72,
            1 - ((quantity - 1) * 0.03)
        )
    else:
        quantity_discount_factor = 1.0

    unit_cost = adjusted_cost

    total_manufacturing_cost = (
        unit_cost
        * quantity
        * quantity_discount_factor
    )

    # =====================================================
    # FINAL CALCULATION
    # =====================================================

    subtotal = (
        total_manufacturing_cost
        + platform_fee
        + packaging_fee
        + delivery_fee
    )

    gst = subtotal * float(GST_RATE)

    final = subtotal + gst

    # =====================================================
    # SAFETY ROUNDING
    # =====================================================

    subtotal = round(subtotal, 2)
    gst = round(gst, 2)
    final = round(final, 2)

    # =====================================================
    # DEBUG LOG
    # =====================================================

    print("============== PRICE DEBUG ==============")
    print("MODEL VOL:", model_volume_cc)
    print("SUPPORT VOL:", support_volume_cc)
    print("EFFECTIVE VOL:", effective_volume)
    print("RATE:", rate)
    print("MATERIAL COST:", material_cost)
    print("TIME COST:", machine_time_cost)
    print("MARKET COST:", market_based)
    print("ADJUSTED:", adjusted_cost)
    print("PLATFORM:", platform_fee)
    print("PACKAGING:", packaging_fee)
    print("DELIVERY:", delivery_fee)
    print("SUBTOTAL:", subtotal)
    print("GST:", gst)
    print("FINAL:", final)
    print("=========================================")

    return PriceBreakdown(
        model_volume_cc=model_volume_cc,
        support_volume_cc=support_volume_cc,
        effective_volume_cc=effective_volume,

        material_slug=material_slug,
        machine_tier=tier.value,
        complexity_level="simple",

        material_rate_per_cc=round(rate, 2),

        material_grams=round(
            effective_volume
            * MATERIAL_DENSITY.get(material_slug, 1),
            2
        ),

        base_manufacturing_cost=round(material_cost, 2),

        market_adjusted_cost=round(adjusted_cost, 2),

        platform_fee=round(platform_fee, 2),
        packaging_fee=round(packaging_fee, 2),
        delivery_fee=round(delivery_fee, 2),

        subtotal=subtotal,
        gst_amount=gst,
        final_price=final,

        estimated_print_time_hrs=estimated_print_time,

        complexity_multiplier=complexity_mult,
        orientation_multiplier=orientation_mult,

        hollowing_applied=hollowing_applied,
        hollowing_factor=hollowing_factor,
    )
