from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.interfaces.api.routes import register_routes
from app.infrastructure.database import initialize_database, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 👉 crea tablas si no existen
    initialize_database()
    yield
    # 👉 libera conexiones
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # Configurar CORS para permitir peticiones desde localhost:4200
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],  # Permitir solicitudes desde localhost:4200
        allow_credentials=True,
        allow_methods=["*"],  # Permitir todos los métodos HTTP
        allow_headers=["*"],  # Permitir todos los encabezados
    )

    register_routes(app)
    return app


app = create_app()
