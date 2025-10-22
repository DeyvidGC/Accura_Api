"""Routes for managing users."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.application.use_cases.users import (
    create_user as create_user_uc,
    delete_user as delete_user_uc,
    get_user as get_user_uc,
    list_users as list_users_uc,
    update_user as update_user_uc,
)
from app.domain.entities import User
from app.infrastructure.database import get_db
from app.infrastructure.email import send_new_user_credentials_email
from app.interfaces.api.dependencies import get_current_active_user
from app.interfaces.api.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


def _to_read_model(user: User) -> UserRead:
    if hasattr(UserRead, "model_validate"):
        return UserRead.model_validate(user)
    return UserRead.from_orm(user)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a new user that can authenticate with the API."""

    try:
        user = create_user_uc(
            db,
            name=user_in.name,
            email=user_in.email,
            password=user_in.password,
            alias=user_in.alias,
            must_change_password=user_in.must_change_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not send_new_user_credentials_email(user.email, user_in.password):
        logger.warning("No se pudo enviar el correo de credenciales al usuario %s", user.email)

    return _to_read_model(user)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_active_user)):
    """Return the authenticated user."""

    return _to_read_model(current_user)


@router.get("/", response_model=list[UserRead])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Return a paginated list of users."""

    users = list_users_uc(db, skip=skip, limit=limit)
    return [_to_read_model(user) for user in users]


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Return the user identified by ``user_id``."""

    try:
        user = get_user_uc(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_read_model(user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an existing user."""

    try:
        user = update_user_uc(
            db,
            user_id=user_id,
            name=user_in.name,
            email=user_in.email,
            alias=user_in.alias,
            must_change_password=user_in.must_change_password,
            is_active=user_in.is_active,
            password=user_in.password,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        status_code = status.HTTP_400_BAD_REQUEST
        if str(exc) == "Usuario no encontrado":
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return _to_read_model(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Delete the specified user."""

    try:
        delete_user_uc(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
