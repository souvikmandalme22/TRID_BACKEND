import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class EffectiveMaterial(Base):
    __tablename__ = "effective_materials"

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id                  = Column(String(64), ForeignKey("uploaded_models.model_id"), nullable=False)
    material_slug             = Column(String(64), nullable=False)

    model_volume              = Column(Float, nullable=False)   # mm³
    infill_factor             = Column(Float, nullable=False)
    effective_model_material  = Column(Float, nullable=False)   # model_volume × infill_factor

    raw_support_volume        = Column(Float, nullable=False)   # mm³
    support_density_factor    = Column(Float, nullable=False)
    effective_support_material= Column(Float, nullable=False)   # raw_support_volume × support_density_factor

    final_effective_material  = Column(Float, nullable=False)   # sum of both

    is_resin                  = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_effective_materials_model_id", "model_id"),
    )
