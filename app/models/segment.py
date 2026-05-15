import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class Segment(Base):
    __tablename__ = "segments"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(64),  unique=True, nullable=False)
    slug        = Column(String(64),  unique=True, nullable=False)   # e.g. "engineering"
    icon_ref    = Column(String(128), nullable=True)                 # icon name / URL
    description = Column(String(512), nullable=True)
    sort_order  = Column(Integer,     nullable=False, default=0)
    is_active   = Column(Boolean,     default=True,  nullable=False)
    created_at  = Column(DateTime,    default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_segments_slug",      "slug"),
        Index("ix_segments_is_active", "is_active"),
    )
