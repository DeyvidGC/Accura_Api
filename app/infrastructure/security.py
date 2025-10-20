"""Security utilities for password hashing and JWT tokens."""

from datetime import datetime, timedelta
from hashlib import sha256
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


def _normalize_password(password: str) -> str:
    """Return a deterministic short representation of ``password``."""

    digest = sha256(password.encode("utf-8")).hexdigest()
    return digest


pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
    # opcional: rounds por defecto (coste)
    bcrypt_sha256__default_rounds=12,
    bcrypt__default_rounds=12,
)
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    scheme = pwd_context.identify(hashed_password) or "bcrypt_sha256"
    if scheme == "bcrypt":
        normalized_password = _normalize_password(plain_password)
        return pwd_context.verify(normalized_password, hashed_password)
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except ValueError as exc:
        message = str(exc)
        if "password cannot be longer than 72 bytes" not in message:
            raise
        normalized_password = _normalize_password(password)
        return pwd_context.hash(normalized_password, scheme="bcrypt")


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
