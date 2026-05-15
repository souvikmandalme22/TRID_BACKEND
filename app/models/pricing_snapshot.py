import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON
from sqlalchemy.sql import func
from app.database.base import Base


class PricingSnapshot(Base):
    __tablename__ = "pricing_snapshots"

    id                  = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id         = Column(String, unique=True, nullable=False, index=True)
    model_id            = Column(String, nullable=False, index=True)
    material_key        = Column(String, nullable=False)
    complexity          = Column(String, nullable=False)
    machine_tier        = Column(String, nullable=False)
    quantity            = Column(Integer, nullable=False)
    delivery_type       = Column(String, nullable=False)

    base_display_price  = Column(Float, nullable=False)
    gst_amount          = Column(Float, nullable=False)
    delivery_charges    = Column(Float, nullable=False)
    final_price         = Column(Float, nullable=False)
    price_range_min     = Column(Float)
    price_range_max     = Column(Float)

    internal_breakdown  = Column(JSON, nullable=False)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
