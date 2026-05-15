import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class SupportAnalysis(Base):
    __tablename__ = "support_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(64), ForeignKey("uploaded_models.model_id"), unique=True, nullable=False)

    raw_support_volume  = Column(Float, nullable=True)   # mm³
    support_area        = Column(Float, nullable=True)   # mm²
    print_height        = Column(Float, nullable=True)   # mm
    overhang_face_count = Column(Float, nullable=True)

    analysis_status = Column(String(32), default="pending", nullable=False)
    error_message   = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_support_analyses_model_id", "model_id"),
    )
