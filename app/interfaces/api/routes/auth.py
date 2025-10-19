"""Authentication endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.application.use_cases.users import authenticate_user, record_login
from app.config import get_settings
from app.infrastructure.database import get_db
from app.infrastructure.security import create_access_token
from app.interfaces.api.schemas import Token

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate the user and return a JWT token."""

    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    record_login(db, user.id)
    return {"access_token": access_token, "token_type": "bearer"}
