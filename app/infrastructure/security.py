"""Security utilities for password hashing and JWT tokens."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

try:  # pragma: no cover - compatibility shim
    import bcrypt  # type: ignore
except ImportError:  # pragma: no cover - dependency missing during static analysis
    bcrypt = None  # type: ignore
else:
    if bcrypt is not None and not hasattr(bcrypt, "__about__"):
        version = getattr(bcrypt, "__version__", "")
        bcrypt.__about__ = SimpleNamespace(__version__=version)  # type: ignore[attr-defined]

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:  # pragma: no cover - passthrough to caller
        raise ValueError("Could not validate credentials") from exc
    return payload
