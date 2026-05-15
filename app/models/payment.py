import uuid
import enum
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from app.db.session import Base


class PaymentStatus(str, enum.Enum):
    initiated = "initiated"
    success   = "success"
    failed    = "failed"
    refunded  = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id                   = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id             = Column(String, nullable=False, index=True)
    user_id              = Column(String, nullable=False, index=True)
    razorpay_order_id    = Column(String, unique=True, nullable=False, index=True)
    razorpay_payment_id  = Column(String, nullable=True)
    razorpay_signature   = Column(String, nullable=True)
    amount               = Column(Float, nullable=False)
    currency             = Column(String(5), default="INR")
    status               = Column(SAEnum(PaymentStatus), default=PaymentStatus.initiated)
    failure_reason       = Column(String(500), nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())
