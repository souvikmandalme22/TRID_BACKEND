import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone       = Column(String(15), unique=True, nullable=False, index=True)
    name        = Column(String(100), nullable=True)
    email       = Column(String(255), nullable=True, unique=True)
    is_active   = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
