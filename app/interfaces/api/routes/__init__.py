from fastapi import FastAPI

from .assistant import router as assistant_router
from .auth import router as auth_router
from .audit_logs import router as audit_logs_router
from .digital_files import router as digital_files_router
from .loads import router as loads_router
from .kpis import router as kpis_router
from .rules import router as rules_router
from .templates import router as templates_router
from .users import router as users_router
from .notifications import router as notifications_router
from .activity import router as activity_router


def register_routes(app: FastAPI) -> None:
    """Registra todos los routers de la API en la aplicación FastAPI."""

    app.include_router(assistant_router)
    app.include_router(auth_router)
    app.include_router(audit_logs_router)
    app.include_router(digital_files_router)
    app.include_router(loads_router)
    app.include_router(kpis_router)
    app.include_router(rules_router)
    app.include_router(users_router)
    app.include_router(templates_router)
    app.include_router(notifications_router)
    app.include_router(activity_router)
