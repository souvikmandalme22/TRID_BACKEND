"""
TRID Authentication System
Complete OTP + JWT auth — production-grade

FILES TO CREATE:
- app/models/user.py
- app/models/otp.py
- app/schemas/auth.py
- app/services/auth_service.py
- app/services/otp_service.py
- app/core/security.py
- app/core/dependencies.py
- app/api/v1/endpoints/auth.py
- alembic/versions/0017_auth_tables.py
"""

import uuid, random, hashlib, logging
from datetime import datetime, timedelta
from typing import Optional

# ─────────────────────────────────────────────
# app/models/user.py
# ─────────────────────────────────────────────

USER_MODEL = '''
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.base import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone           = Column(String(15), unique=True, nullable=False, index=True)
    name            = Column(String(100), nullable=True)
    email           = Column(String(255), nullable=True, unique=True)
    is_active       = Column(Boolean, default=True)
    is_verified     = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
'''

# ─────────────────────────────────────────────
# app/models/otp.py
# ─────────────────────────────────────────────

OTP_MODEL = '''
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from app.database.base import Base
import uuid

class OTPRecord(Base):
    __tablename__ = "otp_records"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone       = Column(String(15), nullable=False, index=True)
    otp_hash    = Column(String(64), nullable=False)   # SHA-256 hashed, never plain
    is_used     = Column(Boolean, default=False)
    attempts    = Column(Integer, default=0)
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
'''

# ─────────────────────────────────────────────
# app/models/refresh_token.py
# ─────────────────────────────────────────────

REFRESH_TOKEN_MODEL = '''
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.base import Base
import uuid

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String, nullable=False, index=True)
    token_hash  = Column(String(64), nullable=False, unique=True)
    is_revoked  = Column(Boolean, default=False)
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
'''

# ─────────────────────────────────────────────
# app/schemas/auth.py
# ─────────────────────────────────────────────

AUTH_SCHEMAS = '''
from pydantic import BaseModel, Field
from typing import Optional

class SendOTPRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)

class SendOTPResponse(BaseModel):
    message: str
    expires_in_seconds: int = 300

class VerifyOTPRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    otp: str   = Field(..., min_length=4, max_length=6)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class RefreshRequest(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    id: str
    phone: str
    name: Optional[str]
    email: Optional[str]
    is_verified: bool

    class Config:
        from_attributes = True
'''

# ─────────────────────────────────────────────
# app/core/security.py
# ─────────────────────────────────────────────

SECURITY_CORE = '''
import hashlib, secrets, os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY          = os.getenv("SECRET_KEY", "change-this-in-production")
ALGORITHM           = "HS256"
ACCESS_TOKEN_EXPIRE = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE= int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))


def hash_value(value: str) -> str:
    """SHA-256 hash for OTP and refresh tokens."""
    return hashlib.sha256(value.encode()).hexdigest()


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, hashed_token)."""
    raw = secrets.token_urlsafe(64)
    return raw, hash_value(raw)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        return payload
    except JWTError:
        raise ValueError("Token invalid or expired")
'''

# ─────────────────────────────────────────────
# app/services/otp_service.py
# ─────────────────────────────────────────────

OTP_SERVICE = '''
import random, logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.otp import OTPRecord
from app.core.security import hash_value
import uuid

logger = logging.getLogger(__name__)

OTP_EXPIRE_MINUTES  = 5
MAX_OTP_ATTEMPTS    = 3


async def generate_and_save_otp(phone: str, db: AsyncSession) -> str:
    """Generate 6-digit OTP, hash and save it. Returns plain OTP for SMS."""

    # Invalidate old unused OTPs for this phone
    await db.execute(
        update(OTPRecord)
        .where(OTPRecord.phone == phone, OTPRecord.is_used == False)
        .values(is_used=True)
    )

    otp_plain   = str(random.randint(100000, 999999))
    otp_hash    = hash_value(otp_plain)
    expires_at  = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    record = OTPRecord(
        id=str(uuid.uuid4()),
        phone=phone,
        otp_hash=otp_hash,
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()

    logger.info(f"OTP generated for {phone}")  # Never log plain OTP in production
    return otp_plain  # Send this via SMS


async def verify_otp(phone: str, otp_plain: str, db: AsyncSession) -> bool:
    """Verify OTP. Returns True if valid."""
    otp_hash = hash_value(otp_plain)
    now      = datetime.now(timezone.utc)

    result = await db.execute(
        select(OTPRecord)
        .where(
            OTPRecord.phone    == phone,
            OTPRecord.is_used  == False,
            OTPRecord.expires_at > now,
        )
        .order_by(OTPRecord.created_at.desc())
        .limit(1)
    )
    record: OTPRecord | None = result.scalar_one_or_none()

    if not record:
        raise ValueError("OTP expired or not found. Request a new OTP.")

    # Increment attempt counter
    record.attempts += 1
    if record.attempts > MAX_OTP_ATTEMPTS:
        record.is_used = True
        await db.commit()
        raise ValueError("Too many failed attempts. Request a new OTP.")

    if record.otp_hash != otp_hash:
        await db.commit()
        raise ValueError("Invalid OTP.")

    # Mark used
    record.is_used = True
    await db.commit()
    return True


async def send_otp_sms(phone: str, otp: str):
    """
    Plug in your SMS provider here.
    Options: Twilio, MSG91, Fast2SMS, TextLocal
    Example with MSG91:
        import httpx
        await httpx.AsyncClient().post(
            "https://api.msg91.com/api/v5/otp",
            json={"mobile": phone, "otp": otp, "template_id": "YOUR_TEMPLATE"}
        )
    """
    logger.info(f"[SMS STUB] OTP {otp} → {phone}")  # Replace with real SMS call
'''

# ─────────────────────────────────────────────
# app/services/auth_service.py
# ─────────────────────────────────────────────

AUTH_SERVICE = '''
import uuid, logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_value, decode_access_token,
    ACCESS_TOKEN_EXPIRE, REFRESH_TOKEN_EXPIRE
)

logger = logging.getLogger(__name__)


async def get_or_create_user(phone: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.phone == phone))
    user   = result.scalar_one_or_none()

    if not user:
        user = User(id=str(uuid.uuid4()), phone=phone, is_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user created: {phone}")
    else:
        user.is_verified = True
        await db.commit()

    return user


async def issue_tokens(user: User, db: AsyncSession) -> dict:
    access_token             = create_access_token(user.id)
    raw_refresh, hash_refresh = create_refresh_token()
    expires_at               = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE)

    rt = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=hash_refresh,
        expires_at=expires_at,
    )
    db.add(rt)
    await db.commit()

    return {
        "access_token":  access_token,
        "refresh_token": raw_refresh,
        "token_type":    "bearer",
        "expires_in":    ACCESS_TOKEN_EXPIRE * 60,
    }


async def refresh_access_token(raw_refresh: str, db: AsyncSession) -> dict:
    token_hash = hash_value(raw_refresh)
    now        = datetime.now(timezone.utc)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise ValueError("Refresh token invalid or expired.")

    # Revoke old token (rotation)
    rt.is_revoked = True
    await db.commit()

    # Get user
    user_result = await db.execute(select(User).where(User.id == rt.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise ValueError("User not found or inactive.")

    return await issue_tokens(user, db)


async def revoke_refresh_token(raw_refresh: str, db: AsyncSession):
    token_hash = hash_value(raw_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.is_revoked = True
        await db.commit()
'''

# ─────────────────────────────────────────────
# app/core/dependencies.py
# ─────────────────────────────────────────────

DEPENDENCIES = '''
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT-protected route dependency."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user
'''

# ─────────────────────────────────────────────
# app/api/v1/endpoints/auth.py
# ─────────────────────────────────────────────

AUTH_ENDPOINT = '''
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.auth import (
    SendOTPRequest, SendOTPResponse,
    VerifyOTPRequest, TokenResponse,
    RefreshRequest, UserProfile,
)
from app.services.otp_service import generate_and_save_otp, verify_otp, send_otp_sms
from app.services.auth_service import get_or_create_user, issue_tokens, refresh_access_token, revoke_refresh_token
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(request: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    """Send OTP to phone number."""
    otp = await generate_and_save_otp(request.phone, db)
    await send_otp_sms(request.phone, otp)
    return SendOTPResponse(message="OTP sent successfully", expires_in_seconds=300)


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_and_login(request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP and return JWT tokens."""
    try:
        await verify_otp(request.phone, request.otp, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user   = await get_or_create_user(request.phone, db)
    tokens = await issue_tokens(user, db)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Get new access token using refresh token."""
    try:
        tokens = await refresh_access_token(request.refresh_token, db)
        return TokenResponse(**tokens)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Revoke refresh token (logout)."""
    await revoke_refresh_token(request.refresh_token, db)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current logged-in user profile. Protected route."""
    return current_user
'''

# ─────────────────────────────────────────────
# alembic/versions/0017_auth_tables.py
# ─────────────────────────────────────────────

ALEMBIC_MIGRATION = '''
"""auth tables - users, otp_records, refresh_tokens

Revision ID: 0017
Revises: 0016
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision    = "0017"
down_revision = "0016"

def upgrade():
    op.create_table("users",
        sa.Column("id",          sa.String(), primary_key=True),
        sa.Column("phone",       sa.String(15), nullable=False, unique=True),
        sa.Column("name",        sa.String(100), nullable=True),
        sa.Column("email",       sa.String(255), nullable=True, unique=True),
        sa.Column("is_active",   sa.Boolean(), default=True),
        sa.Column("is_verified", sa.Boolean(), default=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_phone", "users", ["phone"])

    op.create_table("otp_records",
        sa.Column("id",         sa.String(), primary_key=True),
        sa.Column("phone",      sa.String(15), nullable=False),
        sa.Column("otp_hash",   sa.String(64), nullable=False),
        sa.Column("is_used",    sa.Boolean(), default=False),
        sa.Column("attempts",   sa.Integer(), default=0),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_otp_records_phone", "otp_records", ["phone"])

    op.create_table("refresh_tokens",
        sa.Column("id",         sa.String(), primary_key=True),
        sa.Column("user_id",    sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("is_revoked", sa.Boolean(), default=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

def downgrade():
    op.drop_table("refresh_tokens")
    op.drop_table("otp_records")
    op.drop_table("users")
'''

# ─────────────────────────────────────────────
# requirements to add
# ─────────────────────────────────────────────

NEW_REQUIREMENTS = """
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
"""
