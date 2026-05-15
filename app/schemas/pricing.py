from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
from app.utils.pricing_engine import DeliveryTier


class PricingRequest(BaseModel):
    material_slug:  str
    quantity:       int = 1
    delivery_tier:  DeliveryTier = DeliveryTier.standard

    @field_validator("quantity")
    @classmethod
    def qty_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be at least 1.")
        return v


# Internal breakdown — full detail (admin/internal use)
class PricingBreakdownResponse(BaseModel):
    model_id:                     str
    material_slug:                str
    final_effective_material_mm3: float
    final_effective_material_cm3: float
    price_per_cc:                 float
    quantity:                     int
    material_cost:                float
    material_cost_total:          float
    base_cost:                    float
    platform_fee_rate:            float
    platform_fee:                 float
    delivery_tier:                str
    delivery_charge:              float
    subtotal_before_tax:          float
    gst_rate:                     float
    gst_amount:                   float
    final_price:                  float
    created_at:                   datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj) -> "PricingBreakdownResponse":
        return cls(**{
            c: getattr(obj, c) for c in cls.model_fields
        })


# Customer-visible — hides platform fee internals
class PricingPublicResponse(BaseModel):
    model_id:          str
    material_slug:     str
    quantity:          int
    material_cost:     float
    base_cost:         float
    delivery_charge:   float
    gst_amount:        float
    final_price:       float
    delivery_tier:     str
    created_at:        datetime

    @classmethod
    def from_orm_model(cls, obj) -> "PricingPublicResponse":
        return cls(
            model_id=obj.model_id,
            material_slug=obj.material_slug,
            quantity=obj.quantity,
            material_cost=obj.material_cost_total,
            base_cost=obj.base_cost,
            delivery_charge=obj.delivery_charge,
            gst_amount=obj.gst_amount,
            final_price=obj.final_price,
            delivery_tier=obj.delivery_tier,
            created_at=obj.created_at,
        )
