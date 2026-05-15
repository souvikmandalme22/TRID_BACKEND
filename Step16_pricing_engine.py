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
from sqlalchemy import select
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
# COMPLEXITY-BASED PRICING CHART (₹ per CC)
# Source: TRID official pricing document
# Format: material_key → complexity → tier → (min, max)
# ─────────────────────────────────────────────

PRICING_CHART: dict = {
    "PLA": {
        ComplexityLevel.SIMPLE:      {MachineTier.DESKTOP: (3, 6),   MachineTier.MID_INDUSTRY: (10, 18),  MachineTier.INDUSTRY: (55, 90)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.DESKTOP: (6, 12),  MachineTier.MID_INDUSTRY: (18, 30),  MachineTier.INDUSTRY: (90, 150)},
        ComplexityLevel.COMPLEX:     {MachineTier.DESKTOP: (12, 22), MachineTier.MID_INDUSTRY: (30, 55),  MachineTier.INDUSTRY: (150, 250)},
    },
    "ABS": {
        ComplexityLevel.SIMPLE:      {MachineTier.DESKTOP: (4, 8),   MachineTier.MID_INDUSTRY: (12, 22),  MachineTier.INDUSTRY: (60, 100)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.DESKTOP: (8, 16),  MachineTier.MID_INDUSTRY: (22, 38),  MachineTier.INDUSTRY: (100, 170)},
        ComplexityLevel.COMPLEX:     {MachineTier.DESKTOP: (16, 28), MachineTier.MID_INDUSTRY: (38, 65),  MachineTier.INDUSTRY: (170, 280)},
    },
    "PETG": {
        ComplexityLevel.SIMPLE:      {MachineTier.DESKTOP: (5, 9),   MachineTier.MID_INDUSTRY: (12, 22),  MachineTier.INDUSTRY: (60, 100)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.DESKTOP: (9, 16),  MachineTier.MID_INDUSTRY: (22, 38),  MachineTier.INDUSTRY: (100, 170)},
        ComplexityLevel.COMPLEX:     {MachineTier.DESKTOP: (16, 28), MachineTier.MID_INDUSTRY: (38, 65),  MachineTier.INDUSTRY: (170, 280)},
    },
    "TPU": {
        ComplexityLevel.SIMPLE:      {MachineTier.DESKTOP: (6, 12),  MachineTier.MID_INDUSTRY: (15, 28),  MachineTier.INDUSTRY: (70, 120)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.DESKTOP: (12, 22), MachineTier.MID_INDUSTRY: (28, 48),  MachineTier.INDUSTRY: (120, 200)},
        ComplexityLevel.COMPLEX:     {MachineTier.DESKTOP: (22, 38), MachineTier.MID_INDUSTRY: (48, 80),  MachineTier.INDUSTRY: (200, 340)},
    },
    "NYLON_PA12": {
        ComplexityLevel.SIMPLE:      {MachineTier.DESKTOP: (8, 18),  MachineTier.MID_INDUSTRY: (32, 45),  MachineTier.INDUSTRY: (80, 140)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.DESKTOP: (18, 30), MachineTier.MID_INDUSTRY: (45, 70),  MachineTier.INDUSTRY: (140, 230)},
        ComplexityLevel.COMPLEX:     {MachineTier.DESKTOP: (30, 50), MachineTier.MID_INDUSTRY: (70, 110), MachineTier.INDUSTRY: (230, 380)},
    },
    "CARBON_FIBRE": {
        ComplexityLevel.SIMPLE:      {MachineTier.DESKTOP: (20, 50),  MachineTier.MID_INDUSTRY: (60, 110),  MachineTier.INDUSTRY: (150, 280)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.DESKTOP: (50, 90),  MachineTier.MID_INDUSTRY: (110, 180), MachineTier.INDUSTRY: (280, 450)},
        ComplexityLevel.COMPLEX:     {MachineTier.DESKTOP: (90, 160), MachineTier.MID_INDUSTRY: (180, 300), MachineTier.INDUSTRY: (450, 750)},
    },
    "PEEK_PEKK": {
        ComplexityLevel.SIMPLE:      {MachineTier.DESKTOP: (80, 150),  MachineTier.MID_INDUSTRY: (200, 350),  MachineTier.INDUSTRY: (450, 800)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.DESKTOP: (150, 260), MachineTier.MID_INDUSTRY: (350, 600),  MachineTier.INDUSTRY: (800, 1400)},
        ComplexityLevel.COMPLEX:     {MachineTier.DESKTOP: (260, 420), MachineTier.MID_INDUSTRY: (600, 1000), MachineTier.INDUSTRY: (1400, 2500)},
    },
    "ABS_LIKE_RESIN": {
        ComplexityLevel.SIMPLE:      {MachineTier.MID_INDUSTRY: (35, 60),   MachineTier.INDUSTRY: (90, 160)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.MID_INDUSTRY: (60, 100),  MachineTier.INDUSTRY: (160, 270)},
        ComplexityLevel.COMPLEX:     {MachineTier.MID_INDUSTRY: (100, 170), MachineTier.INDUSTRY: (270, 450)},
    },
    "TOUGH_RESIN": {
        ComplexityLevel.SIMPLE:      {MachineTier.MID_INDUSTRY: (60, 95),   MachineTier.INDUSTRY: (120, 210)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.MID_INDUSTRY: (95, 160),  MachineTier.INDUSTRY: (210, 360)},
        ComplexityLevel.COMPLEX:     {MachineTier.MID_INDUSTRY: (160, 280), MachineTier.INDUSTRY: (360, 600)},
    },
    "CASTABLE_RESIN": {
        ComplexityLevel.SIMPLE:      {MachineTier.MID_INDUSTRY: (90, 150),  MachineTier.INDUSTRY: (200, 380)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.MID_INDUSTRY: (150, 260), MachineTier.INDUSTRY: (380, 650)},
        ComplexityLevel.COMPLEX:     {MachineTier.MID_INDUSTRY: (260, 440), MachineTier.INDUSTRY: (650, 1100)},
    },
    "MJF_NYLON_PA12": {
        ComplexityLevel.SIMPLE:      {MachineTier.MID_INDUSTRY: (32, 45),  MachineTier.INDUSTRY: (80, 130)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.MID_INDUSTRY: (45, 72),  MachineTier.INDUSTRY: (130, 210)},
        ComplexityLevel.COMPLEX:     {MachineTier.MID_INDUSTRY: (72, 120), MachineTier.INDUSTRY: (210, 350)},
    },
    "ALUMINIUM": {
        ComplexityLevel.SIMPLE:      {MachineTier.INDUSTRY: (200, 400)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.INDUSTRY: (400, 700)},
        ComplexityLevel.COMPLEX:     {MachineTier.INDUSTRY: (700, 1200)},
    },
    "STAINLESS_STEEL": {
        ComplexityLevel.SIMPLE:      {MachineTier.INDUSTRY: (250, 500)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.INDUSTRY: (500, 850)},
        ComplexityLevel.COMPLEX:     {MachineTier.INDUSTRY: (850, 1500)},
    },
    "TITANIUM": {
        ComplexityLevel.SIMPLE:      {MachineTier.INDUSTRY: (400, 800)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.INDUSTRY: (800, 1400)},
        ComplexityLevel.COMPLEX:     {MachineTier.INDUSTRY: (1400, 2500)},
    },
    "TOOL_STEEL_INCONEL": {
        ComplexityLevel.SIMPLE:      {MachineTier.INDUSTRY: (600, 1200)},
        ComplexityLevel.MID_COMPLEX: {MachineTier.INDUSTRY: (1200, 2000)},
        ComplexityLevel.COMPLEX:     {MachineTier.INDUSTRY: (2000, 3500)},
    },
}


# ─────────────────────────────────────────────
# PLATFORM FEE CONFIG (hidden from customer)
# ─────────────────────────────────────────────

PLATFORM_FEE_CONFIG = {
    "low":    {"threshold": 500,   "rate": 0.12},  # 12% if base < 500
    "mid":    {"threshold": 2000,  "rate": 0.10},  # 10% if base < 2000
    "high":   {"threshold": 10000, "rate": 0.08},  # 8% if base < 10000
    "ultra":  {"rate": 0.06},                       # 6% for very large orders
}

GST_RATE = Decimal("0.18")  # 18% GST

DELIVERY_CHARGES = {
    DeliveryType.STANDARD: Decimal("0"),    # Free standard
    DeliveryType.EXPRESS:  Decimal("149"),  # ₹149 express
}

BASE_COST = Decimal("50")  # Fixed base handling cost


# ─────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────

class PricingRequest(BaseModel):
    model_id: str
    material_key: str                          # e.g. "PLA", "NYLON_PA12"
    complexity: ComplexityLevel
    machine_tier: MachineTier
    final_effective_material_cc: float         # from effective material engine (CC)
    quantity: int = Field(default=1, ge=1)
    delivery_type: DeliveryType = DeliveryType.STANDARD
    segment: Optional[str] = None
    use_case: Optional[str] = None


class PricingBreakdown(BaseModel):
    """Internal breakdown — never expose fully to customer"""
    material_rate_min: float
    material_rate_max: float
    material_rate_used: float
    raw_material_cost: float
    base_cost: float
    platform_fee: float                        # hidden
    platform_fee_rate: float                   # hidden
    delivery_charges: float
    subtotal_before_gst: float
    gst_amount: float
    gst_rate: float


class PricingResult(BaseModel):
    """Customer-visible pricing result"""
    snapshot_id: str
    model_id: str
    material_key: str
    complexity: str
    machine_tier: str
    quantity: int
    delivery_type: str

    # Customer sees only these
    base_display_price: float                  # before GST
    gst_amount: float
    delivery_charges: float
    final_price: float                         # total including everything

    # Internal (stored in DB, not sent to frontend)
    internal_breakdown: PricingBreakdown

    # Price range transparency (optional display)
    price_range_min: float
    price_range_max: float

    created_at: datetime


# ─────────────────────────────────────────────
# PRICING ENGINE SERVICE
# ─────────────────────────────────────────────

class PricingEngine:

    def get_material_rate(
        self,
        material_key: str,
        complexity: ComplexityLevel,
        machine_tier: MachineTier,
    ) -> tuple[float, float]:
        """Returns (min_rate, max_rate) per CC for given material/complexity/tier."""
        material_key = material_key.upper()

        if material_key not in PRICING_CHART:
            raise ValueError(f"Material '{material_key}' not found in pricing chart.")

        complexity_map = PRICING_CHART[material_key]
        if complexity not in complexity_map:
            raise ValueError(f"Complexity '{complexity}' not supported for '{material_key}'.")

        tier_map = complexity_map[complexity]
        if machine_tier not in tier_map:
            raise ValueError(
                f"Machine tier '{machine_tier}' not available for '{material_key}' + '{complexity}'. "
                f"Available tiers: {list(tier_map.keys())}"
            )

        return tier_map[machine_tier]

    def _mid_rate(self, min_rate: float, max_rate: float) -> float:
        """Use midpoint of range as the actual rate."""
        return round((min_rate + max_rate) / 2, 4)

    def _calculate_platform_fee(self, raw_material_cost: Decimal) -> tuple[Decimal, float]:
        """Returns (platform_fee_amount, rate_used)."""
        cost = float(raw_material_cost)

        if cost < PLATFORM_FEE_CONFIG["low"]["threshold"]:
            rate = PLATFORM_FEE_CONFIG["low"]["rate"]
        elif cost < PLATFORM_FEE_CONFIG["mid"]["threshold"]:
            rate = PLATFORM_FEE_CONFIG["mid"]["rate"]
        elif cost < PLATFORM_FEE_CONFIG["high"]["threshold"]:
            rate = PLATFORM_FEE_CONFIG["high"]["rate"]
        else:
            rate = PLATFORM_FEE_CONFIG["ultra"]["rate"]

        fee = Decimal(str(cost * rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return fee, rate

    def calculate_price(self, request: PricingRequest) -> PricingResult:
        """
        Core pricing calculation.
        Formula:
        final_price = (effective_material × rate) + base_cost + platform_fee + delivery + GST
        """
        # 1. Get rate from chart
        min_rate, max_rate = self.get_material_rate(
            request.material_key,
            request.complexity,
            request.machine_tier,
        )
        rate_used = self._mid_rate(min_rate, max_rate)

        # 2. Raw material cost
        effective_cc = Decimal(str(request.final_effective_material_cc))
        rate_decimal = Decimal(str(rate_used))
        raw_material_cost = (effective_cc * rate_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 3. Base cost
        base = BASE_COST

        # 4. Hidden platform fee
        platform_fee, platform_rate = self._calculate_platform_fee(raw_material_cost)

        # 5. Delivery
        delivery = DELIVERY_CHARGES[request.delivery_type]

        # 6. Subtotal before GST
        subtotal = raw_material_cost + base + platform_fee + delivery

        # 7. GST
        gst_amount = (subtotal * GST_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 8. Final price
        final = subtotal + gst_amount

        # 9. Quantity multiplier
        qty = Decimal(str(request.quantity))
        final_total = (final * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        gst_total   = (gst_amount * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        delivery_total = delivery  # delivery is per order, not per unit

        # Price range for transparency
        range_min = float(
            (effective_cc * Decimal(str(min_rate)) + base + platform_fee + delivery)
            * (Decimal("1") + GST_RATE) * qty
        )
        range_max = float(
            (effective_cc * Decimal(str(max_rate)) + base + platform_fee + delivery)
            * (Decimal("1") + GST_RATE) * qty
        )

        breakdown = PricingBreakdown(
            material_rate_min=min_rate,
            material_rate_max=max_rate,
            material_rate_used=rate_used,
            raw_material_cost=float(raw_material_cost * qty),
            base_cost=float(base * qty),
            platform_fee=float(platform_fee * qty),
            platform_fee_rate=platform_rate,
            delivery_charges=float(delivery_total),
            subtotal_before_gst=float(subtotal * qty),
            gst_amount=float(gst_total),
            gst_rate=float(GST_RATE),
        )

        return PricingResult(
            snapshot_id=str(uuid.uuid4()),
            model_id=request.model_id,
            material_key=request.material_key,
            complexity=request.complexity.value,
            machine_tier=request.machine_tier.value,
            quantity=request.quantity,
            delivery_type=request.delivery_type.value,
            base_display_price=float((subtotal * qty).quantize(Decimal("0.01"))),
            gst_amount=float(gst_total),
            delivery_charges=float(delivery_total),
            final_price=float(final_total),
            internal_breakdown=breakdown,
            price_range_min=round(range_min, 2),
            price_range_max=round(range_max, 2),
            created_at=datetime.utcnow(),
        )


# ─────────────────────────────────────────────
# DATABASE MODEL
# app/models/pricing_snapshot.py — add to your models
# ─────────────────────────────────────────────

PRICING_SNAPSHOT_MODEL = '''
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON
from sqlalchemy.sql import func
from app.database.base import Base

class PricingSnapshot(Base):
    __tablename__ = "pricing_snapshots"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id     = Column(String, unique=True, nullable=False, index=True)
    model_id        = Column(String, nullable=False, index=True)
    material_key    = Column(String, nullable=False)
    complexity      = Column(String, nullable=False)
    machine_tier    = Column(String, nullable=False)
    quantity        = Column(Integer, nullable=False)
    delivery_type   = Column(String, nullable=False)

    # Customer visible
    base_display_price  = Column(Float, nullable=False)
    gst_amount          = Column(Float, nullable=False)
    delivery_charges    = Column(Float, nullable=False)
    final_price         = Column(Float, nullable=False)
    price_range_min     = Column(Float)
    price_range_max     = Column(Float)

    # Internal (hidden)
    internal_breakdown  = Column(JSON, nullable=False)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
'''


# ─────────────────────────────────────────────
# ALEMBIC MIGRATION
# alembic/versions/0016_pricing_snapshots.py
# ─────────────────────────────────────────────

ALEMBIC_MIGRATION = '''
"""pricing snapshots table

Revision ID: 0016
Revises: 0015
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "0016"
down_revision = "0015"

def upgrade():
    op.create_table(
        "pricing_snapshots",
        sa.Column("id",                 sa.String(),  primary_key=True),
        sa.Column("snapshot_id",        sa.String(),  nullable=False, unique=True),
        sa.Column("model_id",           sa.String(),  nullable=False),
        sa.Column("material_key",       sa.String(),  nullable=False),
        sa.Column("complexity",         sa.String(),  nullable=False),
        sa.Column("machine_tier",       sa.String(),  nullable=False),
        sa.Column("quantity",           sa.Integer(), nullable=False),
        sa.Column("delivery_type",      sa.String(),  nullable=False),
        sa.Column("base_display_price", sa.Float(),   nullable=False),
        sa.Column("gst_amount",         sa.Float(),   nullable=False),
        sa.Column("delivery_charges",   sa.Float(),   nullable=False),
        sa.Column("final_price",        sa.Float(),   nullable=False),
        sa.Column("price_range_min",    sa.Float()),
        sa.Column("price_range_max",    sa.Float()),
        sa.Column("internal_breakdown", JSON,         nullable=False),
        sa.Column("created_at",         sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pricing_snapshots_model_id",   "pricing_snapshots", ["model_id"])
    op.create_index("ix_pricing_snapshots_snapshot_id","pricing_snapshots", ["snapshot_id"])

def downgrade():
    op.drop_table("pricing_snapshots")
'''


# ─────────────────────────────────────────────
# FASTAPI ENDPOINT
# app/api/v1/endpoints/pricing.py
# ─────────────────────────────────────────────

ENDPOINT_CODE = '''
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.pricing_engine import PricingEngine, PricingRequest, PricingResult
import logging, uuid, json
from datetime import datetime

router = APIRouter(prefix="/pricing", tags=["Pricing"])
engine = PricingEngine()

@router.post("/calculate", response_model=PricingResult)
async def calculate_price(request: PricingRequest, db: AsyncSession = Depends(get_db)):
    """Calculate final price for a 3D print job."""
    try:
        result = engine.calculate_price(request)

        # Save snapshot to DB
        from app.models.pricing_snapshot import PricingSnapshot
        snapshot = PricingSnapshot(
            id=str(uuid.uuid4()),
            snapshot_id=result.snapshot_id,
            model_id=result.model_id,
            material_key=result.material_key,
            complexity=result.complexity,
            machine_tier=result.machine_tier,
            quantity=result.quantity,
            delivery_type=result.delivery_type,
            base_display_price=result.base_display_price,
            gst_amount=result.gst_amount,
            delivery_charges=result.delivery_charges,
            final_price=result.final_price,
            price_range_min=result.price_range_min,
            price_range_max=result.price_range_max,
            internal_breakdown=result.internal_breakdown.dict(),
            created_at=datetime.utcnow(),
        )
        db.add(snapshot)
        await db.commit()

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Pricing error: {e}")
        raise HTTPException(status_code=500, detail="Pricing calculation failed")


@router.get("/snapshot/{snapshot_id}")
async def get_snapshot(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a saved pricing snapshot."""
    from app.models.pricing_snapshot import PricingSnapshot
    from sqlalchemy import select
    result = await db.execute(
        select(PricingSnapshot).where(PricingSnapshot.snapshot_id == snapshot_id)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.get("/rates/{material_key}")
async def get_material_rates(
    material_key: str,
    complexity: str,
    machine_tier: str,
):
    """Get raw rate range for a material/complexity/tier combo."""
    try:
        from app.services.pricing_engine import ComplexityLevel, MachineTier
        min_r, max_r = engine.get_material_rate(
            material_key,
            ComplexityLevel(complexity),
            MachineTier(machine_tier),
        )
        return {"material": material_key, "complexity": complexity,
                "machine_tier": machine_tier, "min_rate": min_r, "max_rate": max_r}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
'''
