# app/infrastructure/security.py

from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import get_settings

# ---- Hashing con UNA SOLA LIBRERÍA (passlib) ----
# Ajusta "rounds" según tu presupuesto de CPU. 310000 es una buena base hoy.
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__rounds=310_000,
)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)  # usa pbkdf2_sha256

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def needs_rehash(hashed_password: str) -> bool:
    return pwd_context.needs_update(hashed_password)
# ---- JWT ----
settings = get_settings()

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    return jwt.encode({**data, "exp": expire}, settings.secret_key, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Could not validate credentials") from exc