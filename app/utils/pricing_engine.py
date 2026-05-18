from dataclasses import dataclass
from typing import Dict, Tuple
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

# 🔥 MARKET BALANCING (NEW CORE FIX)
MARKET_BLEND_ALPHA = 0.62  # cost weight vs market expectation


def get_market_anchor_rate(volume_cc: float) -> float:
    """
    Market expectation curve (IMPORTANT FIX)
    Reduces extreme pricing variance
    """
    if volume_cc <= 1000:
        return 2.2
    elif volume_cc <= 3000:
        return 1.8
    elif volume_cc <= 7000:
        return 1.45
    elif volume_cc <= 15000:
        return 1.15
    elif volume_cc <= 30000:
        return 0.95
    else:
        return 0.80


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

FLOW_RATE_CC_PER_HR = {
    "pla": 18,
}

MATERIAL_DENSITY = {
    "pla": 1.24,
}


# =========================================================
# PRICE BREAKDOWN
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
    market_adjusted_cost: float   # 🔥 NEW

    platform_fee: float
    packaging_fee: float
    delivery_fee: float

    subtotal: float
    gst_amount: float
    final_price: float

    estimated_print_time_hrs: float


# =========================================================
# HELPERS
# =========================================================

def get_infill_factor(infill_percent: int) -> float:
    safe_percent = max(0, min(infill_percent, 100))
    return round(0.30 + (0.70 * (safe_percent / 100)), 4)


def apply_large_part_discount(rate: float, volume: float) -> float:
    """
    FIXED: softer discount (earlier was too aggressive)
    """
    r = rate

    if volume > 30000:
        r *= 0.55
    elif volume > 20000:
        r *= 0.65
    elif volume > 10000:
        r *= 0.75
    elif volume > 5000:
        r *= 0.88

    return round(max(r, 0.35), 2)


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


def estimate_print_time(volume: float) -> float:
    flow = 18
    return round((volume / flow) + SETUP_OVERHEAD_HRS, 2)


# =========================================================
# MAIN ENGINE (FIXED LOGIC)
# =========================================================

def calculate_price(
    model_volume_cc: float,
    support_volume_cc: float,
    material_slug: str,
    infill_percent: int,
    quantity: int,
    machine_tier: str = "desktop",
) -> PriceBreakdown:

    tier = MachineTier(machine_tier)

    # infill cap
    if model_volume_cc > 5000:
        infill_percent = min(infill_percent, 5)

    infill_factor = get_infill_factor(infill_percent)

    effective_volume = (model_volume_cc * infill_factor) + support_volume_cc

    # base rate
    chart = PRICING_CHART.get(material_slug, DEFAULT_PRICING)
    mn, mx = chart[ComplexityLevel.SIMPLE][tier]

    t = min(max((effective_volume - 50) / 2000, 0), 1)
    rate = mx - (mx - mn) * t

    # apply discount
    rate = apply_large_part_discount(rate, effective_volume)

    # cost-based
    cost_based = effective_volume * rate

    # =====================================================
    # 🔥 MARKET BALANCING CORE FIX
    # =====================================================
    market_rate = get_market_anchor_rate(effective_volume)
    market_based = effective_volume * market_rate

    # blend cost + market expectation
    adjusted_cost = (
        MARKET_BLEND_ALPHA * cost_based +
        (1 - MARKET_BLEND_ALPHA) * market_based
    )

    adjusted_cost += float(BASE_COST)

    platform_fee = get_platform_fee(adjusted_cost)
    packaging_fee = get_packaging_fee(effective_volume)
    delivery_fee = 0

    subtotal = adjusted_cost + platform_fee + packaging_fee
    gst = subtotal * float(GST_RATE)

    final = (subtotal + gst) * quantity

    return PriceBreakdown(
        model_volume_cc=model_volume_cc,
        support_volume_cc=support_volume_cc,
        effective_volume_cc=effective_volume,

        material_slug=material_slug,
        machine_tier=tier.value,
        complexity_level="simple",

        material_rate_per_cc=rate,
        material_grams=effective_volume * MATERIAL_DENSITY.get(material_slug, 1),

        base_manufacturing_cost=cost_based,
        market_adjusted_cost=adjusted_cost,

        platform_fee=platform_fee,
        packaging_fee=packaging_fee,
        delivery_fee=delivery_fee,

        subtotal=subtotal,
        gst_amount=gst,
        final_price=final,

        estimated_print_time_hrs=estimate_print_time(effective_volume),
    )
