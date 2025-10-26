"""Authentication related schemas."""

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    must_change_password: bool


class PasswordHashRequest(BaseModel):
    password: str


class PasswordHashResponse(BaseModel):
    hashed_password: str
