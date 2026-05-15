import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class UseCase(Base):
    __tablename__ = "use_cases"

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                      = Column(String(64),  unique=True, nullable=False)
    slug                      = Column(String(64),  unique=True, nullable=False)
    description               = Column(String(512), nullable=True)
    durability_level          = Column(String(32),  nullable=False)   # low / medium / high / extreme
    recommended_strength      = Column(String(32),  nullable=False)   # low / medium / high / ultra
    sort_order                = Column(Integer,     default=0, nullable=False)
    is_active                 = Column(Boolean,     default=True, nullable=False)
    created_at                = Column(DateTime,    default=datetime.utcnow, nullable=False)
    updated_at                = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_use_cases_slug",      "slug"),
        Index("ix_use_cases_is_active", "is_active"),
    )
