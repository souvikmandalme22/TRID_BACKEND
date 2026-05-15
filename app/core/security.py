import hashlib, secrets, os
from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY           = os.getenv("SECRET_KEY", "change-this-in-production")
ALGORITHM            = "HS256"
ACCESS_TOKEN_EXPIRE  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
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
