import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Enum as SAEnum, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class UploadStatus(str, enum.Enum):
    pending = "pending"
    validated = "validated"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class FileType(str, enum.Enum):
    stl = "stl"
    obj = "obj"
    step = "step"
    stp = "stp"


class UploadedModel(Base):
    __tablename__ = "uploaded_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(64), unique=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(SAEnum(FileType), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    upload_status = Column(SAEnum(UploadStatus), default=UploadStatus.pending, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_uploaded_models_model_id", "model_id"),
        Index("ix_uploaded_models_upload_status", "upload_status"),
        Index("ix_uploaded_models_created_at", "created_at"),
    )
