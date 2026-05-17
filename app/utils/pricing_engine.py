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

FLOW_RATE_CC_PER_HR = {
    "pla": 18,
    "petg": 16,
    "abs": 15,
    "tpu": 10,
    "nylon": 12,
    "standard-resin": 8,
    "tough-resin": 7,
    "clear-resin": 8,
    "castable-wax-resin": 6,
    "pa12": 25,
}

SETUP_OVERHEAD_HRS = 0.5


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

    estimated_print_time_hrs: float


# =========================================================
# INFILL ENGINE
# =========================================================

def get_infill_factor(infill_percent: int) -> float:
    safe_percent = max(0, min(infill_percent, 100))
    return round(0.28 + (0.72 * (safe_percent / 100)), 4)


# =========================================================
# SUPPORT ENGINE
# =========================================================

def get_support_factor(material_slug: str, support_volume_cc: float) -> float:
    return 1.0


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
    if score <= 3
