from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum


# =========================================================
# DELIVERY
# =========================================================

class DeliveryType(str, Enum):
    standard = "standard"
    express = "express"
    urgent = "urgent"
    free = "free"


# =========================================================
# COMPLEXITY FEATURES
# =========================================================

class ComplexityFeatures(BaseModel):
    thin_wall: bool = False
    internal_channels: bool = False
    text_or_logo: bool = False
    high_support: bool = False
    orientation_sensitive: bool = False
    tiny_features: bool = False
    tolerance_critical: bool = False


# =========================================================
# ORIENTATION ANALYSIS
# =========================================================

class OrientationAnalysis(BaseModel):
    stability_score: float = 1.0
    failure_risk: float = 0.0
    tall_geometry: bool = False
    warp_risk: bool = False


# =========================================================
# MAIN PRICING REQUEST
# =========================================================

class PricingRequest(BaseModel):
    material_slug: str

    quantity: int = 1

    # FIXED: unified naming
    delivery_type: DeliveryType = DeliveryType.standard

    # Core Geometry
    model_volume_cc: float
    support_volume_cc: float = 0

    # Printing
    infill_percent: int = 20
    layer_height: float = 0.2
    estimated_print_time_hours: float = 1.0

    # Smart Engines
    complexity_features: ComplexityFeatures = ComplexityFeatures()
    orientation_analysis: OrientationAnalysis = OrientationAnalysis()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError("quantity must be at least 1")
        return v

    @field_validator("model_volume_cc")
    @classmethod
    def validate_volume(cls, v):
        if v <= 0:
            raise ValueError("model_volume_cc must be positive")
        return v

    @field_validator("support_volume_cc")
    @classmethod
    def validate_support(cls, v):
        if v < 0:
            raise ValueError("support_volume_cc cannot be negative")
        return v

    @field_validator("infill_percent")
    @classmethod
    def validate_infill(cls, v):
        if v < 0 or v > 100:
            raise ValueError("infill_percent must be between 0 and 100")
        return v


# =========================================================
# INTERNAL BREAKDOWN RESPONSE
# =========================================================

class PricingBreakdownResponse(BaseModel):
    model_id: str
    material_slug: str
    quantity: int

    # Volumes
    model_volume_cc: float
    support_volume_cc: float
    effective_volume_cc: float

    # Material
    material_rate_per_cc: float

    # Multipliers
    complexity_multiplier: float
    orientation_multiplier: float

    # Costs
    base_manufacturing_cost: float
    adjusted_manufacturing_cost: float

    platform_fee: float
    packaging_fee: float
    delivery_fee: float

    subtotal: float
    gst_amount: float
    final_price: float

    delivery_type: DeliveryType

    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj):
        return cls(**{c: getattr(obj, c) for c in cls.model_fields})


# =========================================================
# PUBLIC RESPONSE
# =========================================================

class PricingPublicResponse(BaseModel):
    model_id: str
    material_slug: str
    quantity: int

    effective_volume_cc: float
    adjusted_manufacturing_cost: float
    delivery_fee: float
    gst_amount: float
    final_price: float

    delivery_type: DeliveryType
    created_at: datetime

    @classmethod
    def from_orm_model(cls, obj):
        return cls(
            model_id=obj.model_id,
            material_slug=obj.material_slug,
            quantity=obj.quantity,
            effective_volume_cc=obj.effective_volume_cc,
            adjusted_manufacturing_cost=obj.adjusted_manufacturing_cost,
            delivery_fee=obj.delivery_fee,
            gst_amount=obj.gst_amount,
            final_price=obj.final_price,
            delivery_type=obj.delivery_type,
            created_at=obj.created_at,
        )
