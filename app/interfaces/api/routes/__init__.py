from fastapi import FastAPI

from .hello import router as hello_router


def register_routes(app: FastAPI) -> None:
    """Register all API routes with the FastAPI application."""

    app.include_router(hello_router)
