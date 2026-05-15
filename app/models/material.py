import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer,
    Float, ForeignKey, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class Material(Base):
    __tablename__ = "materials"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id             = Column(UUID(as_uuid=True), ForeignKey("material_families.id"), nullable=False)

    name                  = Column(String(64),  unique=True, nullable=False)
    slug                  = Column(String(64),  unique=True, nullable=False)
    short_description     = Column(String(512), nullable=True)

    # Pricing
    price_per_cc          = Column(Float,  nullable=False)           # ₹ per cm³

    # Physical properties
    strength_category     = Column(String(32), nullable=False)       # low / medium / high / ultra
    flexibility_category  = Column(String(32), nullable=False)       # rigid / semi-flex / flexible
    outdoor_suitable      = Column(Boolean, default=False, nullable=False)
    heat_resistance       = Column(Boolean, default=False, nullable=False)

    # Print logic
    supports_infill       = Column(Boolean, default=True,  nullable=False)  # False for resin
    default_support_density = Column(String(16), default="normal", nullable=False)  # light/normal/dense

    # UI tags (e.g. ["Best", "Budget"])
    tags                  = Column(String(128), nullable=True)       # comma-separated

    # Icon
    icon_ref              = Column(String(128), nullable=True)

    sort_order            = Column(Integer, default=0, nullable=False)
    is_active             = Column(Boolean, default=True, nullable=False)
    created_at            = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_materials_slug",      "slug"),
        Index("ix_materials_family_id", "family_id"),
        Index("ix_materials_is_active", "is_active"),
    )
