from fastapi import FastAPI

from .auth import router as auth_router
from .users import router as users_router


def register_routes(app: FastAPI) -> None:
    """Register all API routes with the FastAPI application."""

    app.include_router(auth_router)
    app.include_router(users_router)
