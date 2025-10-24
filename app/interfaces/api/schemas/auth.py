"""Authentication related schemas."""

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str


class PasswordHashRequest(BaseModel):
    password: str


class PasswordHashResponse(BaseModel):
    hashed_password: str
