"""Routes for managing users."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.use_cases.users import (
    create_user as create_user_uc,
    deactivate_user,
    get_user as get_user_uc,
    list_users as list_users_uc,
    update_user as update_user_uc,
)
from app.domain.entities import User
from app.infrastructure.database import get_db
from app.infrastructure.email import send_user_created_email
from app.interfaces.api.dependencies import get_current_active_user
from app.interfaces.api.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _to_read_model(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        alias=user.alias,
        email=user.email,
        must_change_password=user.must_change_password,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        is_active=user.is_active,
    )


@router.get("/", response_model=list[UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Return a list of users."""

    users = list_users_uc(db, skip=skip, limit=limit)
    return [_to_read_model(user) for user in users]


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Return a single user by id."""

    user = get_user_uc(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return _to_read_model(user)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new user and send a notification email."""

    try:
        user = create_user_uc(
            db,
            name=user_in.name,
            email=user_in.email,
            password=user_in.password,
            alias=user_in.alias,
            created_by=current_user.id,
            must_change_password=user_in.must_change_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    background_tasks.add_task(send_user_created_email, user.email, user.name)
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
            user_id,
            name=user_in.name,
            alias=user_in.alias,
            email=user_in.email,
            password=user_in.password,
            must_change_password=user_in.must_change_password,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _to_read_model(user)


@router.delete("/{user_id}", response_model=UserRead)
def deactivate_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Deactivate a user instead of deleting it permanently."""

    try:
        user = deactivate_user(db, user_id, updated_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _to_read_model(user)
