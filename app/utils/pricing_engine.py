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

    "abs": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (4, 8),
            MachineTier.MID_INDUSTRY: (12, 22),
            MachineTier.INDUSTRY: (60, 100),
        },
    },

    "petg": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (5, 9),
            MachineTier.MID_INDUSTRY: (12, 22),
            MachineTier.INDUSTRY: (60, 100),
        },
    },

    "tpu": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (6, 12),
            MachineTier.MID_INDUSTRY: (15, 28),
            MachineTier.INDUSTRY: (70, 120),
        },
    },

    "nylon": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (8, 18),
            MachineTier.MID_INDUSTRY: (32, 45),
            MachineTier.INDUSTRY: (80, 140),
        },
    },

    "standard-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (25, 40),
            MachineTier.MID_INDUSTRY: (35, 60),
            MachineTier.INDUSTRY: (90, 160),
        },
    },

    "tough-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (40, 70),
            MachineTier.MID_INDUSTRY: (60, 95),
            MachineTier.INDUSTRY: (120, 210),
        },
    },

    "clear-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (40, 70),
            MachineTier.MID_INDUSTRY: (60, 95),
            MachineTier.INDUSTRY: (120, 210),
        },
    },

    "castable-wax-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (60, 110),
            MachineTier.MID_INDUSTRY: (90, 150),
            MachineTier.INDUSTRY: (200, 380),
        },
    },

    "pa12": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP: (8, 18),
            MachineTier.MID_INDUSTRY: (32, 45),
            MachineTier.INDUSTRY: (80, 130),
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
    "abs": 15,
    "petg": 16,
    "tpu": 10,
    "nylon": 12,
    "standard-resin": 8,
    "tough-resin": 7,
    "clear-resin": 8,
    "castable-wax-resin": 6,
    "pa12": 25,
}

MATERIAL_DENSITY = {
    "pla": 1.24,
    "abs": 1.04,
    "petg": 1.27,
    "tpu": 1.20,
    "nylon": 1.01,
    "standard-resin": 1.10,
    "tough-resin": 1.15,
    "clear-resin": 1.10,
    "castable-wax-resin": 1.05,
    "pa12": 1.01,
}

# =========================================================
# PRICE BREAKDOWN
# =========================================================

@dataclass
class PriceBreakdown:
    model_volume_cc: float
    support_volume_cc: float
    effective_volume_cc: float

    infill_factor: float
    support_factor: float

    material_slug: str
    machine_tier: str
    complexity_level: str

    material_rate_per_cc: float
    material_grams: float

    base_manufacturing_cost: float
    adjusted_manufacturing_cost: float

    platform_fee: float
    packaging_fee: float
    delivery_fee: float

    subtotal: float
    gst_amount: float
    final_price: float

    price_range_min: float
    price_range_max: float

    quantity: int
    delivery_tier: str
    estimated_print_time_hrs: float


# =========================================================
# HELPERS
# =========================================================

def get_infill_factor(infill_percent: int) -> float:
    safe_percent = max(0, min(infill_percent, 100))
    return round(0.28 + (0.72 * (safe_percent / 100)), 4)


def get_support_factor(material_slug: str, support_volume_cc: float) -> float:
    return 1.0


# =========================================================
# LARGE PART DISCOUNT
# =========================================================

def apply_large_part_discount(
    material_rate: float,
    effective_volume_cc: float,
    material_slug: str,
) -> float:

    rate = material_rate

    # HUGE PARTS
if effective_volume_cc > 30000:
    rate *= 0.22

elif effective_volume_cc > 20000:
    rate *= 0.30

elif effective_volume_cc > 10000:
    rate *= 0.42

elif effective_volume_cc > 5000:
    rate *= 0.60

    # Cheap bulk materials
    if material_slug in ["pla", "petg", "abs"]:

        if effective_volume_cc > 10000:
            rate *= 0.7

    return round(max(rate, 0.35), 2)


# =========================================================
# MATERIAL RATE
# =========================================================

def get_material_rate(
    material_slug: str,
    complexity_level: ComplexityLevel,
    machine_tier: MachineTier,
    volume_cc: float = 0,
) -> Tuple[float, float, float]:

    chart = PRICING_CHART.get(
        material_slug,
        DEFAULT_PRICING
    )

    mn, mx = chart[complexity_level][machine_tier]

    if volume_cc <= 50:
        t = 0.0

    elif volume_cc >= 2000:
        t = 1.0

    else:
        t = (volume_cc - 50) / (2000 - 50)

    rate = mx - (mx - mn) * t

    return round(rate, 2), float(mn), float(mx)


# =========================================================
# PLATFORM FEE
# =========================================================

def get_platform_fee(adjusted_cost: float) -> float:

    if adjusted_cost <= 300:
        return 20

    if adjusted_cost <= 1500:
        return 60

    if adjusted_cost <= 5000:
        return 180

    if adjusted_cost <= 15000:
        return 400

    if adjusted_cost <= 50000:
        return 800

    return min(1200, adjusted_cost * 0.02)


# =========================================================
# PACKAGING
# =========================================================

def get_packaging_fee(
    effective_volume_cc: float,
    material_slug: str
) -> float:

    if "resin" in material_slug:
        return 25

    if effective_volume_cc > 5000:
        return 150

    if effective_volume_cc > 1000:
        return 80

    if effective_volume_cc > 300:
        return 20

    if effective_volume_cc > 100:
        return 10

    return 5


# =========================================================
# DELIVERY
# =========================================================

def get_delivery_fee(delivery_tier: str) -> float:
    return 0


# =========================================================
# PRINT TIME
# =========================================================

def estimate_print_time(
    effective_volume_cc: float,
    material_slug: str,
) -> float:

    base_flow = FLOW_RATE_CC_PER_HR.get(
        material_slug,
        15
    )

    # Faster assumption for huge prints
    if effective_volume_cc > 30000:
        flow_rate = base_flow * 18

    elif effective_volume_cc > 20000:
        flow_rate = base_flow * 14

    elif effective_volume_cc > 10000:
        flow_rate = base_flow * 10

    elif effective_volume_cc > 5000:
        flow_rate = base_flow * 6

    elif effective_volume_cc > 1000:
        flow_rate = base_flow * 3

    else:
        flow_rate = base_flow

    base_time = effective_volume_cc / flow_rate

    total = base_time + SETUP_OVERHEAD_HRS

    return round(total * 2) / 2


# =========================================================
# MAIN ENGINE
# =========================================================

def calculate_price(
    model_volume_cc: float,
    support_volume_cc: float,
    material_slug: str,
    infill_percent: int,
    quantity: int,
    delivery_tier: str,
    complexity_features: Dict,
    orientation_analysis: Dict,
    machine_tier: str = "desktop",
) -> PriceBreakdown:

    if model_volume_cc <= 0:
        raise ValueError("model_volume_cc must be positive")

    if quantity < 1:
        raise ValueError("quantity must be at least 1")

    # Resolve tier
    try:
        tier = MachineTier(machine_tier)

    except ValueError:
        tier = MachineTier.DESKTOP

    # AUTO LOW INFILL FOR HUGE SHOWPIECES
    if model_volume_cc > 5000:
        infill_percent = min(infill_percent, 5)

    infill_factor = get_infill_factor(infill_percent)

    support_factor = get_support_factor(
        material_slug,
        support_volume_cc
    )

    complexity_level = ComplexityLevel.SIMPLE

    effective_volume_cc = round(
        (
            model_volume_cc * infill_factor
        ) +
        (
            support_volume_cc * support_factor
        ),
        2
    )

    material_rate, range_min_rate, range_max_rate = get_material_rate(
        material_slug,
        complexity_level,
        tier,
        effective_volume_cc,
    )

    # APPLY LARGE PART ECONOMICS
    material_rate = apply_large_part_discount(
        material_rate,
        effective_volume_cc,
        material_slug,
    )

    # Material weight
    density = MATERIAL_DENSITY.get(
        material_slug,
        1.0
    )

    material_grams = round(
        effective_volume_cc * density,
        2
    )

    # Core manufacturing
    base_manufacturing_cost = round(
        effective_volume_cc * material_rate,
        2
    )

    adjusted_manufacturing_cost = base_manufacturing_cost

    # Add base order cost
    adjusted_with_base = (
        adjusted_manufacturing_cost +
        float(BASE_COST)
    )

    platform_fee = get_platform_fee(
        adjusted_with_base
    )

    packaging_fee = get_packaging_fee(
        effective_volume_cc,
        material_slug
    )

    delivery_fee = get_delivery_fee(
        delivery_tier
    )

    subtotal = round(
        adjusted_with_base +
        platform_fee +
        packaging_fee +
        delivery_fee,
        2
    )

    gst_amount = round(
        subtotal * float(GST_RATE),
        2
    )

    final_price = round(
        (
            subtotal + gst_amount
        ) * quantity,
        2
    )

    # PRICE RANGE
    scaled_min = apply_large_part_discount(
        range_min_rate,
        effective_volume_cc,
        material_slug,
    )

    scaled_max = apply_large_part_discount(
        range_max_rate,
        effective_volume_cc,
        material_slug,
    )

    price_range_min = round(
        effective_volume_cc *
        scaled_min *
        (1 + float(GST_RATE)),
        2
    )

    price_range_max = round(
        effective_volume_cc *
        scaled_max *
        (1 + float(GST_RATE)),
        2
    )

    estimated_print_time_hrs = estimate_print_time(
        effective_volume_cc,
        material_slug,
    )

    return PriceBreakdown(
        model_volume_cc=model_volume_cc,
        support_volume_cc=support_volume_cc,
        effective_volume_cc=effective_volume_cc,

        infill_factor=infill_factor,
        support_factor=support_factor,

        material_slug=material_slug,
        machine_tier=tier.value,
        complexity_level=complexity_level.value,

        material_rate_per_cc=material_rate,
        material_grams=material_grams,

        base_manufacturing_cost=base_manufacturing_cost,
        adjusted_manufacturing_cost=adjusted_manufacturing_cost,

        platform_fee=platform_fee,
        packaging_fee=packaging_fee,
        delivery_fee=delivery_fee,

        subtotal=subtotal,
        gst_amount=gst_amount,
        final_price=final_price,

        price_range_min=price_range_min,
        price_range_max=price_range_max,

        quantity=quantity,
        delivery_tier=delivery_tier,

        estimated_print_time_hrs=estimated_print_time_hrs,
    )
