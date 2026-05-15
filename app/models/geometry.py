import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class GeometryAnalysis(Base):
    __tablename__ = "geometry_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(64), ForeignKey("uploaded_models.model_id"), unique=True, nullable=False)

    dim_x = Column(Float, nullable=True)
    dim_y = Column(Float, nullable=True)
    dim_z = Column(Float, nullable=True)

    bbox_min_x = Column(Float, nullable=True)
    bbox_min_y = Column(Float, nullable=True)
    bbox_min_z = Column(Float, nullable=True)
    bbox_max_x = Column(Float, nullable=True)
    bbox_max_y = Column(Float, nullable=True)
    bbox_max_z = Column(Float, nullable=True)

    volume = Column(Float, nullable=True)
    surface_area = Column(Float, nullable=True)
    is_watertight = Column(Boolean, nullable=True)

    analysis_status = Column(String(32), default="pending", nullable=False)
    error_message = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_geometry_analyses_model_id", "model_id"),
    )
