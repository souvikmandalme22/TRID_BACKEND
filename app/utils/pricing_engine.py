"""
TRID Pricing Engine
Formula: final_price = (final_effective_material × material_rate) + base_cost + platform_fee + delivery + GST
Material rates sourced from India 3D Printing complexity-based pricing table.
"""
from dataclasses import dataclass
from enum import Enum


class ComplexityTier(str, Enum):
    simple      = "simple"
    mid_complex = "mid_complex"
    complex     = "complex"


class MachineTier(str, Enum):
    desktop    = "desktop"
    mid        = "mid"
    production = "production"


# ₹ per CC — (min, max) — from uploaded pricing table
# structure: PRICING_TABLE[material_slug][complexity][machine_tier] = (min, max)
PRICING_TABLE: dict[str, dict[str, dict[str, tuple[float, float]]]] = {
    "pla": {
        "simple":      {"desktop": (3,6),    "mid": (10,18),  "production": (55,90)},
        "mid_complex": {"desktop": (6,12),   "mid": (18,30),  "production": (90,150)},
        "complex":     {"desktop": (12,22),  "mid": (30,55),  "production": (150,250)},
    },
    "abs": {
        "simple":      {"desktop": (4,8),    "mid": (12,22),  "production": (60,100)},
        "mid_complex": {"desktop": (8,16),   "mid": (22,38),  "production": (100,170)},
        "complex":     {"desktop": (16,28),  "mid": (38,65),  "production": (170,280)},
    },
    "petg": {
        "simple":      {"desktop": (5,9),    "mid": (12,22),  "production": (60,100)},
        "mid_complex": {"desktop": (9,16),   "mid": (22,38),  "production": (100,170)},
        "complex":     {"desktop": (16,28),  "mid": (38,65),  "production": (170,280)},
    },
    "tpu": {
        "simple":      {"desktop": (6,12),   "mid": (15,28),  "production": (70,120)},
        "mid_complex": {"desktop": (12,22),  "mid": (28,48),  "production": (120,200)},
        "complex":     {"desktop": (22,38),  "mid": (48,80),  "production": (200,340)},
    },
    "nylon": {
        "simple":      {"desktop": (8,18),   "mid": (32,45),  "production": (80,140)},
        "mid_complex": {"desktop": (18,30),  "mid": (45,70),  "production": (140,230)},
        "complex":     {"desktop": (30,50),  "mid": (70,110), "production": (230,380)},
    },
    # Resin family
    "standard-resin": {
        "simple":      {"desktop": (25,40),  "mid": (35,60),  "production": (90,160)},
        "mid_complex": {"desktop": (40,70),  "mid": (60,100), "production": (160,270)},
        "complex":     {"desktop": (70,120), "mid": (100,170),"production": (270,450)},
    },
    "tough-resin": {
        "simple":      {"desktop": (40,70),  "mid": (60,95),  "production": (120,210)},
        "mid_complex": {"desktop": (70,120), "mid": (95,160), "production": (210,360)},
        "complex":     {"desktop": (120,200),"mid": (160,280),"production": (360,600)},
    },
    "castable-wax-resin": {
        "simple":      {"desktop": (60,110), "mid": (90,150), "production": (200,380)},
        "mid_complex": {"desktop": (110,180),"mid": (150,260),"production": (380,650)},
        "complex":     {"desktop": (180,300),"mid": (260,440),"production": (650,1100)},
    },
    "high-detail-resin": {
        "simple":      {"desktop": (40,70),  "mid": (60,95),  "production": (120,210)},
        "mid_complex": {"desktop": (70,120), "mid": (95,160), "production": (210,360)},
        "complex":     {"desktop": (120,200),"mid": (160,280),"production": (360,600)},
    },
    "clear-resin": {
        "simple":      {"desktop": (25,40),  "mid": (35,60),  "production": (90,160)},
        "mid_complex": {"desktop": (40,70),  "mid": (60,100), "production": (160,270)},
        "complex":     {"desktop": (70,120), "mid": (100,170),"production": (270,450)},
    },
    "flexible-resin": {
        "simple":      {"desktop": (30,55),  "mid": (45,80),  "production": (100,180)},
        "mid_complex": {"desktop": (55,90),  "mid": (80,130), "production": (180,300)},
        "complex":     {"desktop": (90,150), "mid": (130,220),"production": (300,500)},
    },
}

# Fallback rate if material not in table
DEFAULT_RATE_PER_CC = 15.0

# Base cost — fixed operational overhead per order (₹)
BASE_COST = 49.0

# Hidden platform fee — % of material cost (not shown to customer line-by-line)
PLATFORM_FEE_RATE = 0.12   # 12%

# GST rate
GST_RATE = 0.18            # 18%

# Delivery charges (₹)
DELIVERY_CHARGES = {
    "standard": 79.0,
    "express":  199.0,
    "free":     0.0,
}

# Free delivery threshold
FREE_DELIVERY_THRESHOLD = 999.0


def get_material_rate(
    material_slug: str,
    complexity: ComplexityTier,
    machine_tier: MachineTier,
) -> float:
    """Return midpoint ₹/CC rate for the given material + complexity + machine tier."""
    table = PRICING_TABLE.get(material_slug)
    if not table:
        return DEFAULT_RATE_PER_CC
    tier_map = table.get(complexity.value, {})
    range_val = tier_map.get(machine_tier.value)
    if not range_val:
        return DEFAULT_RATE_PER_CC
    return (range_val[0] + range_val[1]) / 2.0


@dataclass
class PriceBreakdown:
    # Inputs
    final_effective_material: float   # mm³ (converted to CC internally)
    material_slug:            str
    complexity:               ComplexityTier
    machine_tier:             MachineTier
    quantity:                 int
    delivery_type:            str

    # Computed — per unit
    effective_cc:             float   # mm³ → CC (÷1000)
    material_rate_per_cc:     float
    material_cost:            float   # effective_cc × rate
    base_cost:                float
    platform_fee:             float   # hidden
    subtotal_before_delivery: float
    delivery_charge:          float
    subtotal_before_gst:      float
    gst_amount:               float

    # Final
    unit_price:               float
    total_price:              float   # unit_price × quantity

    # Customer visible (no platform fee line)
    customer_material_cost:   float
    customer_base_cost:       float
    customer_delivery:        float
    customer_gst:             float
    customer_total:           float


def calculate_price(
    final_effective_material: float,   # mm³
    material_slug: str,
    complexity: ComplexityTier = ComplexityTier.mid_complex,
    machine_tier: MachineTier = MachineTier.desktop,
    quantity: int = 1,
    delivery_type: str = "standard",
) -> PriceBreakdown:
    if final_effective_material <= 0:
        raise ValueError("final_effective_material must be positive.")
    if quantity < 1:
        raise ValueError("quantity must be at least 1.")

    effective_cc       = round(final_effective_material / 1000.0, 6)  # mm³ → CC
    rate               = get_material_rate(material_slug, complexity, machine_tier)
    material_cost      = round(effective_cc * rate, 2)

    platform_fee       = round(material_cost * PLATFORM_FEE_RATE, 2)
    subtotal           = round(material_cost + BASE_COST + platform_fee, 2)

    # Delivery
    if subtotal * quantity >= FREE_DELIVERY_THRESHOLD:
        delivery        = DELIVERY_CHARGES["free"]
        delivery_type   = "free"
    else:
        delivery        = DELIVERY_CHARGES.get(delivery_type, DELIVERY_CHARGES["standard"])

    subtotal_with_del  = round(subtotal + delivery, 2)
    gst                = round(subtotal_with_del * GST_RATE, 2)
    unit_price         = round(subtotal_with_del + gst, 2)
    total_price        = round(unit_price * quantity, 2)

    # Customer-visible (platform fee absorbed into material cost display)
    cust_material      = round(material_cost + platform_fee, 2)
    cust_gst           = round((cust_material + BASE_COST + delivery) * GST_RATE, 2)
    cust_total         = round(cust_material + BASE_COST + delivery + cust_gst, 2)

    return PriceBreakdown(
        final_effective_material=final_effective_material,
        material_slug=material_slug,
        complexity=complexity,
        machine_tier=machine_tier,
        quantity=quantity,
        delivery_type=delivery_type,
        effective_cc=effective_cc,
        material_rate_per_cc=round(rate, 4),
        material_cost=material_cost,
        base_cost=BASE_COST,
        platform_fee=platform_fee,
        subtotal_before_delivery=subtotal,
        delivery_charge=delivery,
        subtotal_before_gst=subtotal_with_del,
        gst_amount=gst,
        unit_price=unit_price,
        total_price=total_price,
        customer_material_cost=cust_material,
        customer_base_cost=BASE_COST,
        customer_delivery=delivery,
        customer_gst=cust_gst,
        customer_total=cust_total * quantity,
    )
