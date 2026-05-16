from dataclasses import dataclass
from typing import Dict
import math


# =========================================================
# CONSTANTS
# =========================================================

GST_RATE = 0.18

DELIVERY_PRICING = {
    "standard": 80,
    "express": 180,
    "urgent": 350,
    "free": 0,
}

INFILL_FACTORS = {
    5: 0.22,
    10: 0.28,
    15: 0.35,
    20: 0.42,
    30: 0.52,
    40: 0.62,
    50: 0.72,
    70: 0.86,
    100: 1.0,
}

MATERIAL_RATES = {
    "pla": 4,
    "petg": 6,
    "abs": 8,
    "tpu": 10,
    "nylon": 16,

    "standard-resin": 12,
    "tough-resin": 18,
    "clear-resin": 15,
    "castable-wax-resin": 25,

    "pa12": 22,
}

DEFAULT_RATE = 15


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
    material_rate_per_cc: float

    base_manufacturing_cost: float
    adjusted_manufacturing_cost: float

    platform_fee: float
    packaging_fee: float
    delivery_fee: float

    subtotal: float
    gst_amount: float
    final_price: float

    quantity: int
    delivery_tier: str


# =========================================================
# INFILL ENGINE
# =========================================================

def get_infill_factor(infill_percent: int) -> float:
    nearest = min(INFILL_FACTORS.keys(), key=lambda x: abs(x - infill_percent))
    return INFILL_FACTORS[nearest]


# =========================================================
# SUPPORT ENGINE
# =========================================================

def get_support_factor(material_slug: str, support_volume_cc: float) -> float:
    if "resin" in material_slug:
        return 0.2
    if support_volume_cc > 100:
        return 0.55
    if support_volume_cc > 40:
        return 0.45
    return 0.3


# =========================================================
# COMPLEXITY ENGINE
# =========================================================

def get_complexity_multiplier(complexity_features: Dict) -> float:
    score = 0

    if complexity_features.get("thin_wall"):
        score += 1
    if complexity_features.get("internal_channels"):
        score += 1
    if complexity_features.get("text_or_logo"):
        score += 1
    if complexity_features.get("high_support"):
        score += 1
    if complexity_features.get("orientation_sensitive"):
        score += 1
    if complexity_features.get("tiny_features"):
        score += 1
    if complexity_features.get("tolerance_critical"):
        score += 2

    if score <= 1:
        return 1.0
    if score <= 3:
        return 1.15
    if score <= 5:
        return 1.35
    return 1.6


# =========================================================
# ORIENTATION ENGINE (INDUSTRY GRADE)
# =========================================================

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def get_orientation_multiplier(orientation_analysis: Dict) -> float:
    """
    Stable production-grade orientation risk engine:
    - weighted scoring
    - nonlinear smoothing
    - safe bounded output
    """

    WEIGHTS = {
        "failure_risk": 5,
        "warp_risk": 3,
        "tall_geometry": 2,
        "high_surface_area": 3,
        "overhang_complexity": 5,
        "thin_wall": 2,
        "tolerance_critical": 5,
    }

    score = 0.0

    if orientation_analysis.get("warp_risk"):
        score += WEIGHTS["warp_risk"]
    if orientation_analysis.get("tall_geometry"):
        score += WEIGHTS["tall_geometry"]
    if orientation_analysis.get("thin_wall"):
        score += WEIGHTS["thin_wall"]
    if orientation_analysis.get("high_surface_area"):
        score += WEIGHTS["high_surface_area"]
    if orientation_analysis.get("overhang_complexity"):
        score += WEIGHTS["overhang_complexity"]
    if orientation_analysis.get("tolerance_critical"):
        score += WEIGHTS["tolerance_critical"]

    failure_risk = orientation_analysis.get("failure_risk", 0.0)
    score += failure_risk * WEIGHTS["failure_risk"]

    normalized = score / 18.0

    curve = _sigmoid((normalized - 0.5) * 6)

    multiplier = 1.0 + (curve * 0.70)

    return round(max(1.0, min(multiplier, 1.70)), 3)


# =========================================================
# MATERIAL ENGINE
# =========================================================

def get_material_rate(material_slug: str) -> float:
    return MATERIAL_RATES.get(material_slug, DEFAULT_RATE)


# =========================================================
# PLATFORM FEES
# =========================================================

def get_platform_fee(adjusted_cost: float) -> float:
    if adjusted_cost < 300:
        return 100
    if adjusted_cost < 1000:
        return 250
    return 500


# =========================================================
# PACKAGING ENGINE
# =========================================================

def get_packaging_fee(effective_volume_cc: float, material_slug: str) -> float:
    if "resin" in material_slug:
        return 50
    if effective_volume_cc > 300:
        return 40
    if effective_volume_cc > 100:
        return 25
    return 15


# =========================================================
# DELIVERY ENGINE
# =========================================================

def get_delivery_fee(delivery_tier: str) -> float:
    return DELIVERY_PRICING.get(delivery_tier, 80)


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
) -> PriceBreakdown:

    if model_volume_cc <= 0:
        raise ValueError("model_volume_cc must be positive")

    if quantity < 1:
        raise ValueError("quantity must be at least 1")

    infill_factor = get_infill_factor(infill_percent)
    support_factor = get_support_factor(material_slug, support_volume_cc)
    complexity_multiplier = get_complexity_multiplier(complexity_features)
    orientation_multiplier = get_orientation_multiplier(orientation_analysis)
    material_rate = get_material_rate(material_slug)

    effective_volume_cc = (model_volume_cc * infill_factor) + (support_volume_cc * support_factor)
    effective_volume_cc = round(effective_volume_cc, 2)

    base_manufacturing_cost = round(effective_volume_cc * material_rate, 2)

    adjusted_manufacturing_cost = round(
        base_manufacturing_cost * complexity_multiplier * orientation_multiplier,
        2
    )

    platform_fee = get_platform_fee(adjusted_manufacturing_cost)
    packaging_fee = get_packaging_fee(effective_volume_cc, material_slug)
    delivery_fee = get_delivery_fee(delivery_tier)

    subtotal = round(
        adjusted_manufacturing_cost + platform_fee + packaging_fee + delivery_fee,
        2
    )

    gst_amount = round(subtotal * GST_RATE, 2)

    final_price = round((subtotal + gst_amount) * quantity, 2)

    return PriceBreakdown(
        model_volume_cc=model_volume_cc,
        support_volume_cc=support_volume_cc,
        effective_volume_cc=effective_volume_cc,

        infill_factor=infill_factor,
        support_factor=support_factor,
        complexity_multiplier=complexity_multiplier,
        orientation_multiplier=orientation_multiplier,

        material_slug=material_slug,
        material_rate_per_cc=material_rate,

        base_manufacturing_cost=base_manufacturing_cost,
        adjusted_manufacturing_cost=adjusted_manufacturing_cost,

        platform_fee=platform_fee,
        packaging_fee=packaging_fee,
        delivery_fee=delivery_fee,

        subtotal=subtotal,
        gst_amount=gst_amount,
        final_price=final_price,

        quantity=quantity,
        delivery_tier=delivery_tier,
    )
