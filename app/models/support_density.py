import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class SupportDensityResult(Base):
    __tablename__ = "support_density_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(64), ForeignKey("uploaded_models.model_id"), nullable=False)

    raw_support_volume          = Column(Float, nullable=False)
    density_profile             = Column(String(16), nullable=False)   # light/normal/dense
    material_category           = Column(String(16), nullable=False)   # filament/resin
    density_factor              = Column(Float, nullable=False)
    effective_support_material  = Column(Float, nullable=False)        # mm³

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_support_density_model_id", "model_id"),
    )
