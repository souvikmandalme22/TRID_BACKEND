import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id   = Column(String, nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    note       = Column(String(500), nullable=True)
    changed_by = Column(String(100), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
