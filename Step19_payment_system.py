"""
TRID Payment System — Razorpay Integration
Step 19: Production-safe payment flow

FILES TO CREATE:
- app/models/payment.py
- app/schemas/payment.py
- app/services/payment_service.py
- app/api/v1/endpoints/payments.py
- alembic/versions/0019_payments.py
"""

# ─────────────────────────────────────────────
# app/models/payment.py
# ─────────────────────────────────────────────

PAYMENT_MODEL = '''
import uuid, enum
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from app.database.base import Base

class PaymentStatus(str, enum.Enum):
    INITIATED = "initiated"
    SUCCESS   = "success"
    FAILED    = "failed"
    REFUNDED  = "refunded"

class Payment(Base):
    __tablename__ = "payments"

    id                   = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id             = Column(String, nullable=False, index=True)
    user_id              = Column(String, nullable=False, index=True)

    # Razorpay fields
    razorpay_order_id    = Column(String, unique=True, nullable=False, index=True)
    razorpay_payment_id  = Column(String, nullable=True)
    razorpay_signature   = Column(String, nullable=True)

    amount               = Column(Float, nullable=False)   # in INR
    currency             = Column(String(5), default="INR")
    status               = Column(SAEnum(PaymentStatus), default=PaymentStatus.INITIATED)
    failure_reason       = Column(String(500), nullable=True)

    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())
'''

# ─────────────────────────────────────────────
# app/schemas/payment.py
# ─────────────────────────────────────────────

PAYMENT_SCHEMAS = '''
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CreatePaymentRequest(BaseModel):
    order_id: str

class CreatePaymentResponse(BaseModel):
    razorpay_order_id : str
    amount_paise      : int       # Razorpay uses paise (INR × 100)
    currency          : str
    order_id          : str
    key_id            : str       # Razorpay public key for frontend

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id   : str
    razorpay_payment_id : str
    razorpay_signature  : str

class PaymentStatusResponse(BaseModel):
    payment_id          : str
    order_id            : str
    razorpay_order_id   : str
    razorpay_payment_id : Optional[str]
    amount              : float
    status              : str
    created_at          : datetime

    class Config:
        from_attributes = True
'''

# ─────────────────────────────────────────────
# app/services/payment_service.py
# ─────────────────────────────────────────────

PAYMENT_SERVICE = '''
import uuid, hmac, hashlib, logging, os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.payment import Payment, PaymentStatus
from app.models.order import Order, OrderStatus
from app.models.order_status_log import OrderStatusLog
import razorpay

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")


def _razorpay_client():
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


async def _get_order(order_id: str, db: AsyncSession) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order  = result.scalar_one_or_none()
    if not order:
        raise ValueError(f"Order {order_id} not found")
    return order


async def create_razorpay_order(
    order_id: str,
    user_id : str,
    db      : AsyncSession,
) -> dict:
    """Create Razorpay order and save payment record."""
    order = await _get_order(order_id, db)

    if order.user_id != user_id:
        raise PermissionError("Not authorized")

    if order.status.value == "cancelled":
        raise ValueError("Cannot pay for cancelled order")

    # Check duplicate payment
    existing = await db.execute(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.status   == PaymentStatus.SUCCESS,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Order already paid")

    # Create Razorpay order
    amount_paise = int(order.final_price * 100)  # INR → paise
    client = _razorpay_client()

    rz_order = client.order.create({
        "amount"  : amount_paise,
        "currency": "INR",
        "receipt" : order.order_number,
        "notes"   : {
            "trid_order_id": order.id,
            "user_id"      : user_id,
        }
    })

    # Save payment record
    payment = Payment(
        id                = str(uuid.uuid4()),
        order_id          = order.id,
        user_id           = user_id,
        razorpay_order_id = rz_order["id"],
        amount            = order.final_price,
        status            = PaymentStatus.INITIATED,
    )
    db.add(payment)
    await db.commit()

    logger.info(f"Razorpay order created: {rz_order['id']} for TRID order: {order.order_number}")

    return {
        "razorpay_order_id": rz_order["id"],
        "amount_paise"     : amount_paise,
        "currency"         : "INR",
        "order_id"         : order.id,
        "key_id"           : RAZORPAY_KEY_ID,
    }


def _verify_signature(rz_order_id: str, rz_payment_id: str, signature: str) -> bool:
    """HMAC-SHA256 signature verification."""
    msg       = f"{rz_order_id}|{rz_payment_id}".encode()
    secret    = RAZORPAY_KEY_SECRET.encode()
    expected  = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def verify_and_confirm_payment(
    rz_order_id  : str,
    rz_payment_id: str,
    signature    : str,
    db           : AsyncSession,
) -> Payment:
    """Verify Razorpay signature and confirm payment."""

    # Fetch payment record
    result  = await db.execute(
        select(Payment).where(Payment.razorpay_order_id == rz_order_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise ValueError("Payment record not found")

    if not _verify_signature(rz_order_id, rz_payment_id, signature):
        payment.status         = PaymentStatus.FAILED
        payment.failure_reason = "Signature verification failed"
        await db.commit()
        raise ValueError("Payment signature invalid — possible tampering")

    # Mark payment success
    payment.razorpay_payment_id = rz_payment_id
    payment.razorpay_signature  = signature
    payment.status              = PaymentStatus.SUCCESS

    # Update order status → printing
    order_result = await db.execute(
        select(Order).where(Order.id == payment.order_id)
    )
    order = order_result.scalar_one_or_none()
    if order:
        old_status   = order.status
        order.status = OrderStatus.PRINTING

        log = OrderStatusLog(
            id         = str(uuid.uuid4()),
            order_id   = order.id,
            old_status = old_status.value,
            new_status = OrderStatus.PRINTING.value,
            note       = f"Payment confirmed: {rz_payment_id}",
            changed_by = "system",
        )
        db.add(log)

    await db.commit()
    await db.refresh(payment)

    logger.info(f"Payment SUCCESS: {rz_payment_id} | Order: {order.order_number if order else payment.order_id}")
    return payment


async def handle_razorpay_webhook(payload: dict, webhook_secret: str, signature: str, db: AsyncSession):
    """
    Handle Razorpay webhook events.
    Verify webhook signature then process event.
    """
    # Verify webhook signature
    body_str = str(payload).encode()
    expected = hmac.new(webhook_secret.encode(), body_str, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Webhook signature invalid")

    event = payload.get("event", "")
    data  = payload.get("payload", {}).get("payment", {}).get("entity", {})

    if event == "payment.captured":
        rz_order_id   = data.get("order_id")
        rz_payment_id = data.get("id")

        result  = await db.execute(
            select(Payment).where(Payment.razorpay_order_id == rz_order_id)
        )
        payment = result.scalar_one_or_none()
        if payment and payment.status != PaymentStatus.SUCCESS:
            payment.razorpay_payment_id = rz_payment_id
            payment.status              = PaymentStatus.SUCCESS
            await db.commit()
            logger.info(f"Webhook: payment captured {rz_payment_id}")

    elif event == "payment.failed":
        rz_order_id = data.get("order_id")
        result  = await db.execute(
            select(Payment).where(Payment.razorpay_order_id == rz_order_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status         = PaymentStatus.FAILED
            payment.failure_reason = data.get("error_description", "Payment failed")
            await db.commit()
            logger.warning(f"Webhook: payment failed for order {rz_order_id}")

    return {"status": "processed", "event": event}


async def get_payment_status(order_id: str, user_id: str, db: AsyncSession) -> Payment:
    result = await db.execute(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.user_id  == user_id,
        ).order_by(Payment.created_at.desc()).limit(1)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise ValueError("No payment found for this order")
    return payment
'''

# ─────────────────────────────────────────────
# app/api/v1/endpoints/payments.py
# ─────────────────────────────────────────────

PAYMENT_ENDPOINT = '''
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.payment import (
    CreatePaymentRequest, CreatePaymentResponse,
    VerifyPaymentRequest, PaymentStatusResponse,
)
from app.services.payment_service import (
    create_razorpay_order, verify_and_confirm_payment,
    handle_razorpay_webhook, get_payment_status,
)

router = APIRouter(prefix="/payments", tags=["Payments"])

WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")


@router.post("/create", response_model=CreatePaymentResponse)
async def create_payment(
    request : CreatePaymentRequest,
    user    : User = Depends(get_current_user),
    db      : AsyncSession = Depends(get_db),
):
    """Create Razorpay payment order."""
    try:
        data = await create_razorpay_order(request.order_id, user.id, db)
        return CreatePaymentResponse(**data)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment gateway error")


@router.post("/verify")
async def verify_payment(
    request : VerifyPaymentRequest,
    user    : User = Depends(get_current_user),
    db      : AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment signature and confirm order."""
    try:
        payment = await verify_and_confirm_payment(
            request.razorpay_order_id,
            request.razorpay_payment_id,
            request.razorpay_signature,
            db,
        )
        return {"message": "Payment verified successfully", "status": payment.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def razorpay_webhook(
    req : Request,
    db  : AsyncSession = Depends(get_db),
):
    """Razorpay webhook endpoint — no JWT auth, uses webhook signature."""
    signature = req.headers.get("X-Razorpay-Signature", "")
    try:
        payload = await req.json()
        result  = await handle_razorpay_webhook(payload, WEBHOOK_SECRET, signature, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/{order_id}/status", response_model=PaymentStatusResponse)
async def payment_status(
    order_id : str,
    user     : User = Depends(get_current_user),
    db       : AsyncSession = Depends(get_db),
):
    """Get payment status for an order."""
    try:
        payment = await get_payment_status(order_id, user.id, db)
        return PaymentStatusResponse(
            payment_id          = payment.id,
            order_id            = payment.order_id,
            razorpay_order_id   = payment.razorpay_order_id,
            razorpay_payment_id = payment.razorpay_payment_id,
            amount              = payment.amount,
            status              = payment.status.value,
            created_at          = payment.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
'''

# ─────────────────────────────────────────────
# alembic/versions/0019_payments.py
# ─────────────────────────────────────────────

ALEMBIC_MIGRATION = '''
"""payments table

Revision ID: 0019
Revises: 0018
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision      = "0019"
down_revision = "0018"

def upgrade():
    op.create_table("payments",
        sa.Column("id",                   sa.String(), primary_key=True),
        sa.Column("order_id",             sa.String(), nullable=False),
        sa.Column("user_id",              sa.String(), nullable=False),
        sa.Column("razorpay_order_id",    sa.String(), nullable=False, unique=True),
        sa.Column("razorpay_payment_id",  sa.String(), nullable=True),
        sa.Column("razorpay_signature",   sa.String(), nullable=True),
        sa.Column("amount",               sa.Float(),  nullable=False),
        sa.Column("currency",             sa.String(5), default="INR"),
        sa.Column("status",               sa.String(20), default="initiated"),
        sa.Column("failure_reason",       sa.String(500), nullable=True),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_payments_order_id",          "payments", ["order_id"])
    op.create_index("ix_payments_user_id",           "payments", ["user_id"])
    op.create_index("ix_payments_razorpay_order_id", "payments", ["razorpay_order_id"])

def downgrade():
    op.drop_table("payments")
'''

# requirements.txt mein add karo:
NEW_REQUIREMENTS = "razorpay==1.4.2"
