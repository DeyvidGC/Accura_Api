"""Endpoints relacionados con autenticación y gestión de contraseñas."""

import logging
from datetime import timedelta
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.application.use_cases.users import (
    AuthenticationStatus,
    authenticate_user,
    record_login,
    reset_password_by_email,
)
from app.config import get_settings
from app.domain.entities import User
from app.infrastructure.database import get_db
from app.infrastructure.email import send_user_password_reset_email
from app.infrastructure.security import create_access_token, get_password_hash
from app.interfaces.api.dependencies import get_current_user, oauth2_scheme, require_admin
from app.interfaces.api.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    PasswordHashRequest,
    PasswordHashResponse,
    Token,
    TokenValidationResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)

_PASSWORD_RESET_MESSAGE = (
    "Si el correo está registrado, recibirás un mensaje con una contraseña temporal."
)


# Nota: se conserva la firma esperada por OAuth2PasswordRequestForm.
@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Autentica al usuario por correo electrónico y devuelve un token JWT."""

    user, auth_status = authenticate_user(db, form_data.username, form_data.password)

    if auth_status is AuthenticationStatus.INVALID_CREDENTIALS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if auth_status is AuthenticationStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    must_change_password = (
        auth_status is AuthenticationStatus.MUST_CHANGE_PASSWORD or user.must_change_password
    )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    password_signature = sha256(
        f"{user.password}:{int(user.is_active)}".encode()
    ).hexdigest()
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.alias,
            "pwd_sig": password_signature,
        },
        expires_delta=access_token_expires,
    )
    record_login(db, user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.alias,
        "must_change_password": must_change_password,
    }


@router.post("/hash-password", response_model=PasswordHashResponse)
def generate_password_hash(
    payload: PasswordHashRequest,
    _: User = Depends(require_admin),
) -> PasswordHashResponse:
    """Devuelve el hash de la contraseña indicada para uso administrativo."""

    hashed_password = get_password_hash(payload.password)
    return PasswordHashResponse(hashed_password=hashed_password)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """Genera una contraseña temporal y la envía al correo del usuario."""

    try:
        user, temporary_password = reset_password_by_email(
            db,
            email=payload.email,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "El correo electrónico debe ser una cuenta de Gmail válida":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        logger.info(
            "Solicitud de restablecimiento ignorada para %s: %s",
            payload.email,
            detail,
        )
        return ForgotPasswordResponse(message=_PASSWORD_RESET_MESSAGE)

    if not send_user_password_reset_email(user.email, temporary_password):
        logger.warning(
            "No se pudo enviar el correo de restablecimiento de contraseña al usuario %s",
            user.email,
        )

    return ForgotPasswordResponse(message=_PASSWORD_RESET_MESSAGE)


@router.get("/validate-token", response_model=TokenValidationResponse)
def validate_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> TokenValidationResponse:
    """Valida el token proporcionado y devuelve un indicador booleano."""

    try:
        get_current_user(token=token, db=db)
    except HTTPException:
        return TokenValidationResponse(is_valid=False)

    return TokenValidationResponse(is_valid=True)
