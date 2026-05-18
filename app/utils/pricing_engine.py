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


# =========================================================
# SMOOTH MARKET CURVE (FIXED - NO CLIFfS)
# =========================================================

def get_market_anchor_rate(volume_cc: float) -> float:
    """
    Smooth exponential decay instead of step function
    Fixes pricing jumps at 1k / 3k / 7k / etc
    """
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


# =========================================================
# HELPERS
# =========================================================

def get_infill_factor(infill_percent: int) -> float:
    safe = max(0, min(infill_percent, 100))
    return 0.30 + (0.70 * (safe / 100))


def apply_large_part_discount(rate: float, volume: float) -> float:
    """
    Soft discounting (prevents underpricing large parts)
    """
    if volume > 30000:
        rate *= 0.60
    elif volume > 20000:
        rate *= 0.70
    elif volume > 10000:
        rate *= 0.80
    elif volume > 5000:
        rate *= 0.90

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
# MAIN ENGINE (FIXED ARCHITECTURE)
# =========================================================

def calculate_price(
    model_volume_cc: float,
    support_volume_cc: float,
    material_slug: str,
    infill_percent: int,
    quantity: int,
    machine_tier: str = "desktop",
    delivery_type: str = "standard",
) -> PriceBreakdown:

    tier = MachineTier(machine_tier)

    # -----------------------------
    # INFILL SAFETY CAP
    # -----------------------------
    if model_volume_cc > 5000:
        infill_percent = min(infill_percent, 5)

    infill_factor = get_infill_factor(infill_percent)

    effective_volume = (model_volume_cc * infill_factor) + support_volume_cc

    # -----------------------------
    # MATERIAL RATE SELECTION
    # -----------------------------
    chart = PRICING_CHART.get(material_slug, DEFAULT_PRICING)
    mn, mx = chart[ComplexityLevel.SIMPLE][tier]

    t = min(max((effective_volume - 50) / 2000, 0), 1)
    rate = mx - (mx - mn) * t

    rate = apply_large_part_discount(rate, effective_volume)

    # -----------------------------
    # COST MODEL
    # -----------------------------
    cost_based = effective_volume * rate

    # -----------------------------
    # MARKET MODEL (SMOOTHED)
    # -----------------------------
    market_rate = get_market_anchor_rate(effective_volume)
    market_based = effective_volume * market_rate

    # blended pricing (balanced fairness vs profitability)
    MARKET_BLEND_ALPHA = 0.62

    adjusted_cost = (
        MARKET_BLEND_ALPHA * cost_based +
        (1 - MARKET_BLEND_ALPHA) * market_based
    )

    adjusted_cost += float(BASE_COST)

    # -----------------------------
    # ORDER FEES (FIXED STRUCTURE)
    # -----------------------------
    platform_fee = get_platform_fee(adjusted_cost)
    packaging_fee = get_packaging_fee(effective_volume)
    delivery_fee = get_delivery_fee(delivery_type)

    # -----------------------------
    # QUANTITY CORRECT MODEL
    # -----------------------------
    unit_cost = adjusted_cost
    unit_total = unit_cost * quantity

    order_fees = platform_fee + packaging_fee + delivery_fee

    subtotal = unit_total + order_fees
    gst = subtotal * float(GST_RATE)
    final = subtotal + gst

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
