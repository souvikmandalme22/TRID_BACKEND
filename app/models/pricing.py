import uuid

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Index,
)

from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class PricingSnapshot(Base):
    __tablename__ = "pricing_snapshots"

    # =========================================================
    # PRIMARY
    # =========================================================

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    model_id = Column(
        String(64),
        ForeignKey("uploaded_models.model_id"),
        nullable=False,
        index=True,
    )

    material_slug = Column(
        String(64),
        nullable=False,
    )

    # =========================================================
    # BASIC INPUTS
    # =========================================================

    quantity = Column(
        Integer,
        nullable=False,
        default=1,
    )

    delivery_tier = Column(
        String(32),
        nullable=False,
        default="standard",
    )

    # =========================================================
    # GEOMETRY
    # =========================================================

    model_volume_cc = Column(
        Float,
        nullable=False,
    )

    support_volume_cc = Column(
        Float,
        nullable=False,
        default=0,
    )

    effective_volume_cc = Column(
        Float,
        nullable=False,
    )

    infill_percent = Column(
        Integer,
        nullable=False,
        default=20,
    )

    layer_height = Column(
        Float,
        nullable=False,
        default=0.2,
    )

    estimated_print_time_hours = Column(
        Float,
        nullable=False,
        default=1.0,
    )

    # =========================================================
    # COMPLEXITY FLAGS
    # =========================================================

    thin_wall = Column(
        Integer,
        nullable=False,
        default=0,
    )

    internal_channels = Column(
        Integer,
        nullable=False,
        default=0,
    )

    text_or_logo = Column(
        Integer,
        nullable=False,
        default=0,
    )

    high_support = Column(
        Integer,
        nullable=False,
        default=0,
    )

    orientation_sensitive = Column(
        Integer,
        nullable=False,
        default=0,
    )

    tiny_features = Column(
        Integer,
        nullable=False,
        default=0,
    )

    tolerance_critical = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # =========================================================
    # ORIENTATION ANALYSIS
    # =========================================================

    stability_score = Column(
        Float,
        nullable=False,
        default=1.0,
    )

    failure_risk = Column(
        Float,
        nullable=False,
        default=0,
    )

    tall_geometry = Column(
        Integer,
        nullable=False,
        default=0,
    )

    warp_risk = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # =========================================================
    # MULTIPLIERS
    # =========================================================

    material_rate_per_cc = Column(
        Float,
        nullable=False,
    )

    complexity_multiplier = Column(
        Float,
        nullable=False,
    )

    orientation_multiplier = Column(
        Float,
        nullable=False,
    )

    support_factor = Column(
        Float,
        nullable=False,
    )

    infill_factor = Column(
        Float,
        nullable=False,
    )

    # =========================================================
    # COSTS
    # =========================================================

    base_manufacturing_cost = Column(
        Float,
        nullable=False,
    )

    adjusted_manufacturing_cost = Column(
        Float,
        nullable=False,
    )

    platform_fee = Column(
        Float,
        nullable=False,
    )

    packaging_fee = Column(
        Float,
        nullable=False,
    )

    delivery_fee = Column(
        Float,
        nullable=False,
    )

    subtotal = Column(
        Float,
        nullable=False,
    )

    gst_amount = Column(
        Float,
        nullable=False,
    )

    final_price = Column(
        Float,
        nullable=False,
    )

    # =========================================================
    # METADATA
    # =========================================================

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # INDEXES
    # =========================================================

    __table_args__ = (
        Index(
            "ix_pricing_snapshots_model_material",
            "model_id",
            "material_slug",
        ),
    )
