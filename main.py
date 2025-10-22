from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.interfaces.api.routes import register_routes
from app.infrastructure.database import initialize_database, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 👉 crea tablas si no existen
    #initialize_database()
    yield
    # 👉 libera conexiones
    engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    register_routes(app)
    return app

app = create_app()
