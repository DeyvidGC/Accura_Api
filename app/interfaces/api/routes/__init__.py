from fastapi import FastAPI

from .assistant import router as assistant_router
from .auth import router as auth_router
from .rules import router as rules_router
from .templates import router as templates_router
from .users import router as users_router


def register_routes(app: FastAPI) -> None:
    """Register all API routes with the FastAPI application."""

    app.include_router(assistant_router)
    app.include_router(auth_router)
    app.include_router(rules_router)
    app.include_router(users_router)
    app.include_router(templates_router)
