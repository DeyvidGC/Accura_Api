# app/infrastructure/security.py

from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.config import get_settings

# 👉 Parchea bcrypt ANTES de importar passlib
try:
    import bcrypt  # type: ignore
except ImportError:
    bcrypt = None  # type: ignore
else:
    # En bcrypt>=4 ya no viene __about__; Passlib viejo lo busca.
    if bcrypt is not None and not hasattr(bcrypt, "__about__"):
        class _About: __version__ = getattr(bcrypt, "__version__", "")
        bcrypt.__about__ = _About()  # type: ignore[attr-defined]

from passlib.context import CryptContext  # <-- ahora sí

# ---- Hashing recomendado ----
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],  # bcrypt_sha256 por defecto
    deprecated="auto",
    bcrypt_sha256__default_rounds=12,
    bcrypt__truncate_error=False,         # evita el error de 72 bytes si algo usa bcrypt “puro”
)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password, scheme="bcrypt_sha256")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

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
