from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreatePaymentRequest(BaseModel):
    order_id: str


class CreatePaymentResponse(BaseModel):
    razorpay_order_id: str
    amount_paise:      int
    currency:          str
    order_id:          str
    key_id:            str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str


class PaymentStatusResponse(BaseModel):
    payment_id:          str
    order_id:            str
    razorpay_order_id:   str
    razorpay_payment_id: Optional[str]
    amount:              float
    status:              str
    created_at:          datetime

    class Config:
        from_attributes = True
