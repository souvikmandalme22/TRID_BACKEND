import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class PricingSnapshot(Base):
    __tablename__ = "pricing_snapshots"

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id                  = Column(String(64), ForeignKey("uploaded_models.model_id"), nullable=False)
    material_slug             = Column(String(64), nullable=False)

    # Inputs
    final_effective_material  = Column(Float,   nullable=False)   # mm³
    complexity                = Column(String(16), nullable=False)
    machine_tier              = Column(String(16), nullable=False)
    quantity                  = Column(Integer,  nullable=False, default=1)
    delivery_type             = Column(String(16), nullable=False)

    # Internal breakdown (full detail)
    effective_cc              = Column(Float, nullable=False)
    material_rate_per_cc      = Column(Float, nullable=False)
    material_cost             = Column(Float, nullable=False)
    base_cost                 = Column(Float, nullable=False)
    platform_fee              = Column(Float, nullable=False)    # hidden
    subtotal_before_delivery  = Column(Float, nullable=False)
    delivery_charge           = Column(Float, nullable=False)
    subtotal_before_gst       = Column(Float, nullable=False)
    gst_amount                = Column(Float, nullable=False)
    unit_price                = Column(Float, nullable=False)
    total_price               = Column(Float, nullable=False)

    # Customer-visible
    customer_material_cost    = Column(Float, nullable=False)
    customer_base_cost        = Column(Float, nullable=False)
    customer_delivery         = Column(Float, nullable=False)
    customer_gst              = Column(Float, nullable=False)
    customer_total            = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_pricing_snapshots_model_id", "model_id"),
    )
