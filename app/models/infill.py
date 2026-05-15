import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class InfillSelection(Base):
    __tablename__ = "infill_selections"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id                 = Column(String(64), ForeignKey("uploaded_models.model_id"), nullable=False)
    material_slug            = Column(String(64), nullable=False)

    infill_profile           = Column(String(16), nullable=False)   # "10","20","40","60","100"
    infill_percentage        = Column(Integer,    nullable=False)
    infill_factor            = Column(Float,      nullable=False)
    model_volume             = Column(Float,      nullable=False)    # mm³
    effective_model_material = Column(Float,      nullable=False)    # mm³
    is_resin                 = Column(Boolean,    default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_infill_selections_model_id", "model_id"),
    )
