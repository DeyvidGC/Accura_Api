from fastapi import APIRouter

from app.application.use_cases.create_greeting import create_greeting

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    greeting = create_greeting()
    return {"message": greeting.message}


@router.get("/hello/{name}")
async def say_hello(name: str) -> dict[str, str]:
    greeting = create_greeting(name)
    return {"message": greeting.message}
