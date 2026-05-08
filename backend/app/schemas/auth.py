from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str
    realm: str = "local"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    username: str
    realm: str
    display_name: str
    email: str | None
    roles: list[str]
    is_superadmin: bool
    enabled: bool
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    password: str
    realm: str = "local"
    display_name: str = ""
    email: str | None = None
    roles: list[str] = ["operator"]


class UserUpdate(BaseModel):
    display_name: str | None = None
    email: str | None = None
    password: str | None = None
    enabled: bool | None = None
    roles: list[str] | None = None


class APITokenCreate(BaseModel):
    name: str
    scopes: list[str] = []
    expires_days: int | None = None


class APITokenOut(BaseModel):
    id: int
    name: str
    token_prefix: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked: bool

    model_config = {"from_attributes": True}


class APITokenCreated(APITokenOut):
    token: str  # 只在建立時回傳一次
