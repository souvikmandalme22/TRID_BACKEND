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
    order = await _get_order(order_id, db)

    if order.user_id != user_id:
        raise PermissionError("Not authorized")

    if order.status.value == "cancelled":
        raise ValueError("Cannot pay for cancelled order")

    existing = await db.execute(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.status   == PaymentStatus.SUCCESS,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Order already paid")

    amount_paise = int(order.final_price * 100)
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
    msg      = f"{rz_order_id}|{rz_payment_id}".encode()
    secret   = RAZORPAY_KEY_SECRET.encode()
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def verify_and_confirm_payment(
    rz_order_id  : str,
    rz_payment_id: str,
    signature    : str,
    db           : AsyncSession,
) -> Payment:
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

    payment.razorpay_payment_id = rz_payment_id
    payment.razorpay_signature  = signature
    payment.status              = PaymentStatus.SUCCESS

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


# FIX: raw_body (bytes) passed from endpoint instead of parsed dict
async def handle_razorpay_webhook(
    payload       : dict,
    raw_body      : bytes,
    webhook_secret: str,
    signature     : str,
    db            : AsyncSession,
):
    expected = hmac.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
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
