"""Security helpers for hashing and token generation."""

from datetime import datetime, timedelta
import secrets
import string

from jose import JWTError, jwt
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
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    return jwt.encode({**data, "exp": expire}, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Could not validate credentials") from exc


def generate_secure_password() -> str:
    """Generate a random password between 8 and 12 characters."""

    alphabet = string.ascii_letters + string.digits + string.punctuation
    length = secrets.choice(range(8, 13))

    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
            and any(char in string.punctuation for char in password)
        ):
            return password


