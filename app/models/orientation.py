import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class OrientationResult(Base):
    __tablename__ = "orientation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(64), ForeignKey("uploaded_models.model_id"), unique=True, nullable=False)

    best_direction_x = Column(Float, nullable=False)
    best_direction_y = Column(Float, nullable=False)
    best_direction_z = Column(Float, nullable=False)

    support_area     = Column(Float, nullable=False)
    print_height     = Column(Float, nullable=False)
    bed_stability    = Column(Float, nullable=False)
    overhang_risk    = Column(Float, nullable=False)
    orientation_score = Column(Float, nullable=False)

    n_samples_evaluated = Column(Integer, nullable=False, default=100)
    analysis_status  = Column(String(32), default="pending", nullable=False)
    error_message    = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_orientation_results_model_id", "model_id"),
    )
