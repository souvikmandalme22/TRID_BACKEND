import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class MaterialFamily(Base):
    __tablename__ = "material_families"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(64),  unique=True, nullable=False)
    slug        = Column(String(64),  unique=True, nullable=False)
    icon_ref    = Column(String(128), nullable=True)
    description = Column(String(512), nullable=True)
    sort_order  = Column(Integer,     nullable=False, default=0)
    is_active   = Column(Boolean,     default=True,  nullable=False)
    created_at  = Column(DateTime,    default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_material_families_slug",      "slug"),
        Index("ix_material_families_is_active", "is_active"),
    )
