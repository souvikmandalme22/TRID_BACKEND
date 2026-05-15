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
    """Razorpay webhook — no JWT auth, uses HMAC signature on raw body."""
    signature = req.headers.get("X-Razorpay-Signature", "")
    try:
        raw_body = await req.body()          # FIX: raw bytes, not parsed JSON
        payload  = await req.json()
        result   = await handle_razorpay_webhook(payload, raw_body, WEBHOOK_SECRET, signature, db)
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
