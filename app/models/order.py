import uuid
import enum
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from app.db.session import Base


class OrderStatus(str, enum.Enum):
    received   = "received"
    printing   = "printing"
    processing = "processing"
    shipped    = "shipped"
    delivered  = "delivered"
    cancelled  = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number     = Column(String(20), unique=True, nullable=False, index=True)
    user_id          = Column(String, nullable=False, index=True)
    model_id         = Column(String, nullable=False)
    snapshot_id      = Column(String, nullable=False)
    segment          = Column(String(100), nullable=False)
    material_key     = Column(String(100), nullable=False)
    use_case         = Column(String(100), nullable=False)
    infill_percent   = Column(Integer, nullable=True)
    quantity         = Column(Integer, nullable=False, default=1)
    delivery_type    = Column(String(20), nullable=False)
    delivery_name    = Column(String(100), nullable=False)
    delivery_phone   = Column(String(15), nullable=False)
    delivery_address = Column(String(500), nullable=False)
    delivery_pincode = Column(String(10), nullable=False)
    base_price       = Column(Float, nullable=False)
    gst_amount       = Column(Float, nullable=False)
    delivery_charges = Column(Float, nullable=False)
    final_price      = Column(Float, nullable=False)
    status           = Column(SAEnum(OrderStatus), default=OrderStatus.received, nullable=False)
    status_note      = Column(String(500), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())
    delivered_at     = Column(DateTime(timezone=True), nullable=True)
