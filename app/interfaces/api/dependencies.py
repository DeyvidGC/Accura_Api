"""FastAPI dependency utilities."""

from hashlib import sha256

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.database import get_db
from app.infrastructure.repositories import UserRepository
from app.infrastructure.security import decode_access_token, refresh_access_token
from app.infrastructure.openai_client import (
    OpenAIConfigurationError,
    StructuredChatService,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def resolve_current_user(token: str, db: Session) -> User:
    """Resolve the authenticated user for the provided token."""

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email: str | None = payload.get("sub")
    password_signature_claim = payload.get("pwd_sig")
    if email is None or password_signature_claim is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not isinstance(password_signature_claim, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserRepository(db).get_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_signature = sha256(
        f"{user.password}:{int(user.is_active)}".encode()
    ).hexdigest()
    if password_signature_claim != expected_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user(
    request: Request,
    response: Response,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated user from the provided token."""

    user = resolve_current_user(token, db)

    try:
        refreshed_token = refresh_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    response.headers["X-Refreshed-Token"] = refreshed_token
    request.state.refreshed_token = refreshed_token

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the authenticated user is active."""

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Ensure the authenticated user has administrator privileges."""

    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        )
    return current_user


def get_structured_chat_service() -> StructuredChatService:
    """Return a configured instance of :class:`StructuredChatService`."""

    try:
        return StructuredChatService()
    except OpenAIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
