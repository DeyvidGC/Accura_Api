"""Routes for managing users."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.use_cases.users import create_user as create_user_uc
from app.domain.entities import User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import get_current_active_user
from app.interfaces.api.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


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

    return _to_read_model(user)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_active_user)):
    """Return the authenticated user."""

    return _to_read_model(current_user)
