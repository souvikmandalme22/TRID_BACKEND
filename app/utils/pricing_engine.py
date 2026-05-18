from dataclasses import dataclass
from typing import Dict, Tuple
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import math
import uuid
from datetime import datetime

# =========================================================
# ENUMS
# =========================================================

class MachineTier(str, Enum):
    DESKTOP     = "desktop"
    MID_INDUSTRY = "mid_industry"
    INDUSTRY    = "industry"


class ComplexityLevel(str, Enum):
    SIMPLE      = "simple"
    MID_COMPLEX = "mid_complex"
    COMPLEX     = "complex"


# =========================================================
# CONSTANTS
# =========================================================

GST_RATE       = Decimal("0.18")
BASE_COST      = Decimal("50")
SETUP_OVERHEAD_HRS = 0.5

# =========================================================
# PRICING CHART  (min, max)  ₹/cc
# =========================================================

PRICING_CHART: Dict = {
    "pla": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (3,   6),
            MachineTier.MID_INDUSTRY: (10,  18),
            MachineTier.INDUSTRY:     (55,  90),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (6,   12),
            MachineTier.MID_INDUSTRY: (18,  30),
            MachineTier.INDUSTRY:     (90,  150),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (12,  22),
            MachineTier.MID_INDUSTRY: (30,  55),
            MachineTier.INDUSTRY:     (150, 250),
        },
    },
    "abs": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (4,   8),
            MachineTier.MID_INDUSTRY: (12,  22),
            MachineTier.INDUSTRY:     (60,  100),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (8,   15),
            MachineTier.MID_INDUSTRY: (22,  38),
            MachineTier.INDUSTRY:     (100, 170),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (15,  28),
            MachineTier.MID_INDUSTRY: (38,  65),
            MachineTier.INDUSTRY:     (170, 280),
        },
    },
    "petg": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (5,   9),
            MachineTier.MID_INDUSTRY: (12,  22),
            MachineTier.INDUSTRY:     (60,  100),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (9,   16),
            MachineTier.MID_INDUSTRY: (22,  38),
            MachineTier.INDUSTRY:     (100, 170),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (16,  28),
            MachineTier.MID_INDUSTRY: (38,  65),
            MachineTier.INDUSTRY:     (170, 280),
        },
    },
    "tpu": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (6,   12),
            MachineTier.MID_INDUSTRY: (15,  28),
            MachineTier.INDUSTRY:     (70,  120),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (12,  22),
            MachineTier.MID_INDUSTRY: (28,  45),
            MachineTier.INDUSTRY:     (120, 200),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (22,  38),
            MachineTier.MID_INDUSTRY: (45,  80),
            MachineTier.INDUSTRY:     (200, 320),
        },
    },
    "nylon": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (8,   18),
            MachineTier.MID_INDUSTRY: (32,  45),
            MachineTier.INDUSTRY:     (80,  140),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (18,  32),
            MachineTier.MID_INDUSTRY: (45,  75),
            MachineTier.INDUSTRY:     (140, 230),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (32,  55),
            MachineTier.MID_INDUSTRY: (75,  120),
            MachineTier.INDUSTRY:     (230, 380),
        },
    },
    "standard-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (25,  40),
            MachineTier.MID_INDUSTRY: (35,  60),
            MachineTier.INDUSTRY:     (90,  160),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (40,  65),
            MachineTier.MID_INDUSTRY: (60,  95),
            MachineTier.INDUSTRY:     (160, 260),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (65,  100),
            MachineTier.MID_INDUSTRY: (95,  150),
            MachineTier.INDUSTRY:     (260, 400),
        },
    },
    "tough-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (40,  70),
            MachineTier.MID_INDUSTRY: (60,  95),
            MachineTier.INDUSTRY:     (120, 210),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (70,  110),
            MachineTier.MID_INDUSTRY: (95,  150),
            MachineTier.INDUSTRY:     (210, 340),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (110, 170),
            MachineTier.MID_INDUSTRY: (150, 240),
            MachineTier.INDUSTRY:     (340, 540),
        },
    },
    "clear-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (40,  70),
            MachineTier.MID_INDUSTRY: (60,  95),
            MachineTier.INDUSTRY:     (120, 210),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (70,  110),
            MachineTier.MID_INDUSTRY: (95,  150),
            MachineTier.INDUSTRY:     (210, 340),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (110, 170),
            MachineTier.MID_INDUSTRY: (150, 240),
            MachineTier.INDUSTRY:     (340, 540),
        },
    },
    "castable-wax-resin": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (60,  110),
            MachineTier.MID_INDUSTRY: (90,  150),
            MachineTier.INDUSTRY:     (200, 380),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (110, 180),
            MachineTier.MID_INDUSTRY: (150, 240),
            MachineTier.INDUSTRY:     (380, 600),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (180, 280),
            MachineTier.MID_INDUSTRY: (240, 380),
            MachineTier.INDUSTRY:     (600, 950),
        },
    },
    "pa12": {
        ComplexityLevel.SIMPLE: {
            MachineTier.DESKTOP:      (8,   18),
            MachineTier.MID_INDUSTRY: (32,  45),
            MachineTier.INDUSTRY:     (80,  130),
        },
        ComplexityLevel.MID_COMPLEX: {
            MachineTier.DESKTOP:      (18,  32),
            MachineTier.MID_INDUSTRY: (45,  75),
            MachineTier.INDUSTRY:     (130, 210),
        },
        ComplexityLevel.COMPLEX: {
            MachineTier.DESKTOP:      (32,  55),
            MachineTier.MID_INDUSTRY: (75,  120),
            MachineTier.INDUSTRY:     (210, 340),
        },
    },
}

# Default fallback
DEFAULT_PRICING: Dict = {
    ComplexityLevel.SIMPLE: {
        MachineTier.DESKTOP:      (10,  20),
        MachineTier.MID_INDUSTRY: (30,  50),
        MachineTier.INDUSTRY:     (100, 180),
    },
    ComplexityLevel.MID_COMPLEX: {
        MachineTier.DESKTOP:      (20,  38),
        MachineTier.MID_INDUSTRY: (50,  85),
        MachineTier.INDUSTRY:     (180, 300),
    },
    ComplexityLevel.COMPLEX: {
        MachineTier.DESKTOP:      (38,  65),
        MachineTier.MID_INDUSTRY: (85,  140),
        MachineTier.INDUSTRY:     (300, 500),
    },
}

FLOW_RATE_CC_PER_HR = {
    "pla":               18,
    "abs":               15,
    "petg":              16,
    "tpu":               10,
    "nylon":             12,
    "standard-resin":    8,
    "tough-resin":       7,
    "clear-resin":       8,
    "castable-wax-resin": 6,
    "pa12":              25,
}

MATERIAL_DENSITY = {
    "pla":               1.24,
    "abs":               1.04,
    "petg":              1.27,
    "tpu":               1.20,
    "nylon":             1.01,
    "standard-resin":    1.10,
    "tough-resin":       1.15,
    "clear-resin":       1.10,
    "castable-wax-resin": 1.05,
    "pa12":              1.01,
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
    complexity_multiplier: float
    orientation_multiplier: float

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


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


# =========================================================
# COMPLEXITY LEVEL — derived from features
# =========================================================

def get_complexity_level(complexity_features: Dict) -> ComplexityLevel:
    score = 0
    if complexity_features.get("thin_wall"):          score += 1
    if complexity_features.get("internal_channels"):  score += 1
    if complexity_features.get("text_or_logo"):       score += 1
    if complexity_features.get("high_support"):       score += 1
    if complexity_features.get("orientation_sensitive"): score += 1
    if complexity_features.get("tiny_features"):      score += 1
    if complexity_features.get("tolerance_critical"): score += 2
    if score <= 1:
        return ComplexityLevel.SIMPLE
    if score <= 4:
        return ComplexityLevel.MID_COMPLEX
    return ComplexityLevel.COMPLEX


def get_complexity_multiplier(complexity_level: ComplexityLevel) -> float:
    return {
        ComplexityLevel.SIMPLE:      1.0,
        ComplexityLevel.MID_COMPLEX: 1.20,
        ComplexityLevel.COMPLEX:     1.50,
    }[complexity_level]


# =========================================================
# ORIENTATION MULTIPLIER
# =========================================================

def get_orientation_multiplier(orientation_analysis: Dict) -> float:
    WEIGHTS = {
        "failure_risk":      5,
        "warp_risk":         3,
        "tall_geometry":     2,
        "high_surface_area": 3,
        "overhang_complexity": 5,
        "thin_wall":         2,
        "tolerance_critical": 5,
    }
    score = 0.0
    for key in ["warp_risk", "tall_geometry", "thin_wall",
                "high_surface_area", "overhang_complexity", "tolerance_critical"]:
        if orientation_analysis.get(key):
            score += WEIGHTS[key]
    failure_risk = orientation_analysis.get("failure_risk", 0.0)
    score += failure_risk * WEIGHTS["failure_risk"]
    normalized = score / 18.0
    curve = _sigmoid((normalized - 0.5) * 6)
    multiplier = 1.0 + (curve * 0.40)
    return round(max(1.0, min(multiplier, 1.40)), 3)


# =========================================================
# MATERIAL RATE — mid of range, volume-weighted within tier
# =========================================================

def get_material_rate(
    material_slug: str,
    complexity_level: ComplexityLevel,
    machine_tier: MachineTier,
    volume_cc: float = 0,
) -> Tuple[float, float, float]:
    """Returns (rate, range_min_rate, range_max_rate)"""

    chart = PRICING_CHART.get(material_slug, DEFAULT_PRICING)
    mn, mx = chart[complexity_level][machine_tier]

    # Within-tier: larger volume → closer to min rate
    # < 50cc → max rate, > 2000cc → min rate, interpolated
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
    if adjusted_cost <= 300:   return 20
    if adjusted_cost <= 1500:  return 60
    if adjusted_cost <= 5000:  return 180
    if adjusted_cost <= 15000: return 400
    if adjusted_cost <= 50000: return 800
    return min(1200, adjusted_cost * 0.02)


# =========================================================
# PACKAGING
# =========================================================

def get_packaging_fee(effective_volume_cc: float, material_slug: str) -> float:
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
    complexity_features: Dict,
) -> float:
    base_flow = FLOW_RATE_CC_PER_HR.get(material_slug, 15)

    if effective_volume_cc > 10000:
        flow_rate = base_flow * 10
    elif effective_volume_cc > 5000:
        flow_rate = base_flow * 6
    elif effective_volume_cc > 1000:
        flow_rate = base_flow * 3
    elif effective_volume_cc > 300:
        flow_rate = base_flow * 1.5
    else:
        flow_rate = base_flow

    base_time = effective_volume_cc / flow_rate

    multiplier = 1.0
    if complexity_features.get("high_support"):     multiplier += 0.20
    if complexity_features.get("thin_wall") or complexity_features.get("tiny_features"):
        multiplier += 0.15
    if complexity_features.get("tolerance_critical"): multiplier += 0.10

    total = (base_time * multiplier) + SETUP_OVERHEAD_HRS
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

    # Resolve enums
    try:
        tier = MachineTier(machine_tier)
    except ValueError:
        tier = MachineTier.DESKTOP

    infill_factor   = get_infill_factor(infill_percent)
    support_factor  = get_support_factor(material_slug, support_volume_cc)
    complexity_level = get_complexity_level(complexity_features)
    complexity_mult  = get_complexity_multiplier(complexity_level)
    orientation_mult = get_orientation_multiplier(orientation_analysis)

    effective_volume_cc = round(
        (model_volume_cc * infill_factor) + (support_volume_cc * support_factor), 2
    )

    material_rate, range_min_rate, range_max_rate = get_material_rate(
        material_slug, complexity_level, tier, effective_volume_cc
    )

    # Grams
    density = MATERIAL_DENSITY.get(material_slug, 1.0)
    material_grams = round(effective_volume_cc * density, 2)

    base_manufacturing_cost = round(
        float(Decimal(str(effective_volume_cc)) * Decimal(str(material_rate))), 2
    )

    adjusted_manufacturing_cost = round(
        base_manufacturing_cost * complexity_mult * orientation_mult, 2
    )

    # Add base cost (fixed ₹50 per order)
    adjusted_with_base = adjusted_manufacturing_cost + float(BASE_COST)

    platform_fee = get_platform_fee(adjusted_with_base)
    packaging_fee = get_packaging_fee(effective_volume_cc, material_slug)
    delivery_fee = get_delivery_fee(delivery_tier)

    subtotal = round(
        adjusted_with_base + platform_fee + packaging_fee + delivery_fee, 2
    )

    gst_amount = round(subtotal * float(GST_RATE), 2)
    final_price = round((subtotal + gst_amount) * quantity, 2)

    # Price range
    price_range_min = round(
        effective_volume_cc * range_min_rate * (1 + float(GST_RATE)), 2
    )
    price_range_max = round(
        effective_volume_cc * range_max_rate * (1 + float(GST_RATE)), 2
    )

    estimated_print_time_hrs = estimate_print_time(
        effective_volume_cc, material_slug, complexity_features
    )

    return PriceBreakdown(
        model_volume_cc=model_volume_cc,
        support_volume_cc=support_volume_cc,
        effective_volume_cc=effective_volume_cc,
        infill_factor=infill_factor,
        support_factor=support_factor,
        complexity_multiplier=complexity_mult,
        orientation_multiplier=orientation_mult,
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
