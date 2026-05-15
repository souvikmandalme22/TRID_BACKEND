"""
TRID Order Management System
Complete order lifecycle — production-grade

FILES TO CREATE:
- app/models/order.py
- app/schemas/order.py
- app/services/order_service.py
- app/api/v1/endpoints/orders.py
- alembic/versions/0018_orders.py
"""

# ─────────────────────────────────────────────
# app/models/order.py
# ─────────────────────────────────────────────

ORDER_MODEL = '''
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from app.database.base import Base
import enum

class OrderStatus(str, enum.Enum):
    RECEIVED   = "received"
    PRINTING   = "printing"
    PROCESSING = "processing"
    SHIPPED    = "shipped"
    DELIVERED  = "delivered"
    CANCELLED  = "cancelled"

class Order(Base):
    __tablename__ = "orders"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number    = Column(String(20), unique=True, nullable=False, index=True)

    # Relations (stored as IDs — FK constraints optional for MVP)
    user_id         = Column(String, nullable=False, index=True)
    model_id        = Column(String, nullable=False)
    snapshot_id     = Column(String, nullable=False)   # pricing snapshot

    # Order details
    segment         = Column(String(100), nullable=False)
    material_key    = Column(String(100), nullable=False)
    use_case        = Column(String(100), nullable=False)
    infill_percent  = Column(Integer, nullable=True)    # null for resin
    quantity        = Column(Integer, nullable=False, default=1)
    delivery_type   = Column(String(20), nullable=False)

    # Address
    delivery_name   = Column(String(100), nullable=False)
    delivery_phone  = Column(String(15),  nullable=False)
    delivery_address= Column(String(500), nullable=False)
    delivery_pincode= Column(String(10),  nullable=False)

    # Pricing (denormalized for order record integrity)
    base_price      = Column(Float, nullable=False)
    gst_amount      = Column(Float, nullable=False)
    delivery_charges= Column(Float, nullable=False)
    final_price     = Column(Float, nullable=False)

    # Status
    status          = Column(SAEnum(OrderStatus), default=OrderStatus.RECEIVED, nullable=False)
    status_note     = Column(String(500), nullable=True)

    # Timestamps
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    delivered_at    = Column(DateTime(timezone=True), nullable=True)
'''

# ─────────────────────────────────────────────
# app/models/order_status_log.py
# ─────────────────────────────────────────────

ORDER_STATUS_LOG_MODEL = '''
import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database.base import Base

class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id     = Column(String, nullable=False, index=True)
    old_status   = Column(String(50), nullable=True)
    new_status   = Column(String(50), nullable=False)
    note         = Column(String(500), nullable=True)
    changed_by   = Column(String(100), nullable=True)   # admin user or "system"
    changed_at   = Column(DateTime(timezone=True), server_default=func.now())
'''

# ─────────────────────────────────────────────
# app/schemas/order.py
# ─────────────────────────────────────────────

ORDER_SCHEMAS = '''
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    RECEIVED   = "received"
    PRINTING   = "printing"
    PROCESSING = "processing"
    SHIPPED    = "shipped"
    DELIVERED  = "delivered"
    CANCELLED  = "cancelled"

class DeliveryAddress(BaseModel):
    name    : str = Field(..., min_length=2)
    phone   : str = Field(..., min_length=10, max_length=15)
    address : str = Field(..., min_length=10)
    pincode : str = Field(..., min_length=6, max_length=10)

class CreateOrderRequest(BaseModel):
    model_id        : str
    snapshot_id     : str          # from pricing engine
    segment         : str
    material_key    : str
    use_case        : str
    infill_percent  : Optional[int] = None   # null for resin
    quantity        : int = Field(default=1, ge=1, le=10000)
    delivery_type   : str
    delivery_address: DeliveryAddress

class OrderStatusUpdate(BaseModel):
    status : OrderStatus
    note   : Optional[str] = None

class OrderResponse(BaseModel):
    id              : str
    order_number    : str
    user_id         : str
    model_id        : str
    snapshot_id     : str
    segment         : str
    material_key    : str
    use_case        : str
    infill_percent  : Optional[int]
    quantity        : int
    delivery_type   : str
    delivery_name   : str
    delivery_phone  : str
    delivery_address: str
    delivery_pincode: str
    base_price      : float
    gst_amount      : float
    delivery_charges: float
    final_price     : float
    status          : str
    status_note     : Optional[str]
    created_at      : datetime
    updated_at      : Optional[datetime]

    class Config:
        from_attributes = True

class StatusLogResponse(BaseModel):
    order_id   : str
    old_status : Optional[str]
    new_status : str
    note       : Optional[str]
    changed_by : Optional[str]
    changed_at : datetime

    class Config:
        from_attributes = True
'''

# ─────────────────────────────────────────────
# app/services/order_service.py
# ─────────────────────────────────────────────

ORDER_SERVICE = '''
import uuid, random, string, logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.order import Order, OrderStatus
from app.models.order_status_log import OrderStatusLog
from app.models.pricing_snapshot import PricingSnapshot
from app.schemas.order import CreateOrderRequest, OrderStatusUpdate

logger = logging.getLogger(__name__)


def _generate_order_number() -> str:
    """TRID-YYYYMMDD-XXXX format."""
    date_part   = datetime.utcnow().strftime("%Y%m%d")
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TRID-{date_part}-{random_part}"


async def _fetch_pricing_snapshot(snapshot_id: str, db: AsyncSession) -> PricingSnapshot:
    result = await db.execute(
        select(PricingSnapshot).where(PricingSnapshot.snapshot_id == snapshot_id)
    )
    snap = result.scalar_one_or_none()
    if not snap:
        raise ValueError(f"Pricing snapshot '{snapshot_id}' not found.")
    return snap


async def create_order(
    user_id: str,
    request: CreateOrderRequest,
    db: AsyncSession,
) -> Order:
    # Pull pricing data from snapshot — single source of truth
    snap = await _fetch_pricing_snapshot(request.snapshot_id, db)

    order = Order(
        id               = str(uuid.uuid4()),
        order_number     = _generate_order_number(),
        user_id          = user_id,
        model_id         = request.model_id,
        snapshot_id      = request.snapshot_id,
        segment          = request.segment,
        material_key     = request.material_key,
        use_case         = request.use_case,
        infill_percent   = request.infill_percent,
        quantity         = request.quantity,
        delivery_type    = request.delivery_type,
        delivery_name    = request.delivery_address.name,
        delivery_phone   = request.delivery_address.phone,
        delivery_address = request.delivery_address.address,
        delivery_pincode = request.delivery_address.pincode,
        base_price       = snap.base_display_price,
        gst_amount       = snap.gst_amount,
        delivery_charges = snap.delivery_charges,
        final_price      = snap.final_price,
        status           = OrderStatus.RECEIVED,
    )
    db.add(order)

    # Log initial status
    log = OrderStatusLog(
        id         = str(uuid.uuid4()),
        order_id   = order.id,
        old_status = None,
        new_status = OrderStatus.RECEIVED.value,
        note       = "Order placed by customer",
        changed_by = "system",
    )
    db.add(log)
    await db.commit()
    await db.refresh(order)

    logger.info(f"Order created: {order.order_number} | user={user_id}")
    return order


async def get_order_by_id(order_id: str, db: AsyncSession) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order  = result.scalar_one_or_none()
    if not order:
        raise ValueError(f"Order '{order_id}' not found.")
    return order


async def get_orders_by_user(user_id: str, db: AsyncSession) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


async def update_order_status(
    order_id: str,
    update_req: OrderStatusUpdate,
    changed_by: str,
    db: AsyncSession,
) -> Order:
    order = await get_order_by_id(order_id, db)

    # Validate transition
    _validate_status_transition(order.status, update_req.status)

    old_status   = order.status
    order.status = update_req.status
    order.status_note = update_req.note

    if update_req.status.value == "delivered":
        order.delivered_at = datetime.now(timezone.utc)

    # Log the change
    log = OrderStatusLog(
        id         = str(uuid.uuid4()),
        order_id   = order_id,
        old_status = old_status.value,
        new_status = update_req.status.value,
        note       = update_req.note,
        changed_by = changed_by,
    )
    db.add(log)
    await db.commit()
    await db.refresh(order)

    logger.info(f"Order {order.order_number}: {old_status} → {update_req.status}")
    return order


async def get_status_logs(order_id: str, db: AsyncSession) -> list[OrderStatusLog]:
    result = await db.execute(
        select(OrderStatusLog)
        .where(OrderStatusLog.order_id == order_id)
        .order_by(OrderStatusLog.changed_at.asc())
    )
    return result.scalars().all()


async def cancel_order(order_id: str, user_id: str, db: AsyncSession) -> Order:
    order = await get_order_by_id(order_id, db)

    if order.user_id != user_id:
        raise PermissionError("Not authorized to cancel this order.")

    if order.status.value not in ("received",):
        raise ValueError(f"Order cannot be cancelled in status: {order.status.value}")

    old_status   = order.status
    order.status = OrderStatus.CANCELLED

    log = OrderStatusLog(
        id         = str(uuid.uuid4()),
        order_id   = order_id,
        old_status = old_status.value,
        new_status = OrderStatus.CANCELLED.value,
        note       = "Cancelled by customer",
        changed_by = user_id,
    )
    db.add(log)
    await db.commit()
    await db.refresh(order)
    return order


# ── Status transition rules ──────────────────

VALID_TRANSITIONS = {
    "received"   : ["printing",   "cancelled"],
    "printing"   : ["processing", "cancelled"],
    "processing" : ["shipped"],
    "shipped"    : ["delivered"],
    "delivered"  : [],
    "cancelled"  : [],
}

def _validate_status_transition(current, new):
    allowed = VALID_TRANSITIONS.get(current.value, [])
    if new.value not in allowed:
        raise ValueError(
            f"Cannot move from '{current.value}' to '{new.value}'. "
            f"Allowed: {allowed}"
        )
'''

# ─────────────────────────────────────────────
# app/api/v1/endpoints/orders.py
# ─────────────────────────────────────────────

ORDER_ENDPOINT = '''
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.order import (
    CreateOrderRequest, OrderResponse,
    OrderStatusUpdate, StatusLogResponse,
)
from app.services.order_service import (
    create_order, get_order_by_id,
    get_orders_by_user, update_order_status,
    get_status_logs, cancel_order,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse)
async def place_order(
    request : CreateOrderRequest,
    user    : User = Depends(get_current_user),
    db      : AsyncSession = Depends(get_db),
):
    """Place a new order. Requires JWT auth."""
    try:
        order = await create_order(user.id, request, db)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my", response_model=list[OrderResponse])
async def my_orders(
    user : User = Depends(get_current_user),
    db   : AsyncSession = Depends(get_db),
):
    """Get all orders for logged-in user."""
    return await get_orders_by_user(user.id, db)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id : str,
    user     : User = Depends(get_current_user),
    db       : AsyncSession = Depends(get_db),
):
    """Get order by ID. User can only see their own orders."""
    try:
        order = await get_order_by_id(order_id, db)
        if order.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        return order
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{order_id}/timeline", response_model=list[StatusLogResponse])
async def order_timeline(
    order_id : str,
    user     : User = Depends(get_current_user),
    db       : AsyncSession = Depends(get_db),
):
    """Get full status timeline of an order."""
    order = await get_order_by_id(order_id, db)
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await get_status_logs(order_id, db)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel(
    order_id : str,
    user     : User = Depends(get_current_user),
    db       : AsyncSession = Depends(get_db),
):
    """Cancel order (only in received status)."""
    try:
        return await cancel_order(order_id, user.id, db)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Admin-only status update ─────────────────
# Add admin auth dependency when admin system is built

@router.patch("/{order_id}/status", response_model=OrderResponse)
async def admin_update_status(
    order_id   : str,
    update_req : OrderStatusUpdate,
    user       : User = Depends(get_current_user),   # replace with admin dep later
    db         : AsyncSession = Depends(get_db),
):
    """Update order status (admin only)."""
    try:
        return await update_order_status(order_id, update_req, user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
'''

# ─────────────────────────────────────────────
# alembic/versions/0018_orders.py
# ─────────────────────────────────────────────

ALEMBIC_MIGRATION = '''
"""orders and order_status_logs tables

Revision ID: 0018
Revises: 0017
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision      = "0018"
down_revision = "0017"

def upgrade():
    op.create_table("orders",
        sa.Column("id",               sa.String(),  primary_key=True),
        sa.Column("order_number",     sa.String(20), nullable=False, unique=True),
        sa.Column("user_id",          sa.String(),  nullable=False),
        sa.Column("model_id",         sa.String(),  nullable=False),
        sa.Column("snapshot_id",      sa.String(),  nullable=False),
        sa.Column("segment",          sa.String(100), nullable=False),
        sa.Column("material_key",     sa.String(100), nullable=False),
        sa.Column("use_case",         sa.String(100), nullable=False),
        sa.Column("infill_percent",   sa.Integer(), nullable=True),
        sa.Column("quantity",         sa.Integer(), nullable=False),
        sa.Column("delivery_type",    sa.String(20), nullable=False),
        sa.Column("delivery_name",    sa.String(100), nullable=False),
        sa.Column("delivery_phone",   sa.String(15),  nullable=False),
        sa.Column("delivery_address", sa.String(500), nullable=False),
        sa.Column("delivery_pincode", sa.String(10),  nullable=False),
        sa.Column("base_price",       sa.Float(), nullable=False),
        sa.Column("gst_amount",       sa.Float(), nullable=False),
        sa.Column("delivery_charges", sa.Float(), nullable=False),
        sa.Column("final_price",      sa.Float(), nullable=False),
        sa.Column("status",           sa.String(20), nullable=False, default="received"),
        sa.Column("status_note",      sa.String(500), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column("delivered_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_orders_user_id",      "orders", ["user_id"])
    op.create_index("ix_orders_order_number", "orders", ["order_number"])

    op.create_table("order_status_logs",
        sa.Column("id",         sa.String(), primary_key=True),
        sa.Column("order_id",   sa.String(), nullable=False),
        sa.Column("old_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("note",       sa.String(500), nullable=True),
        sa.Column("changed_by", sa.String(100), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_order_status_logs_order_id", "order_status_logs", ["order_id"])

def downgrade():
    op.drop_table("order_status_logs")
    op.drop_table("orders")
'''
