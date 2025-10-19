from fastapi import FastAPI

from app.interfaces.api.routes import register_routes


def create_app() -> FastAPI:
    app = FastAPI()
    register_routes(app)
    return app


app = create_app()
