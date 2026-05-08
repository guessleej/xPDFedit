"""
Auth & Identity Service — FastAPI 應用入口

端點：
  POST  /login              本機 / LDAP / AD 登入
  POST  /login/ldap         指定 LDAP Realm 登入
  POST  /logout
  POST  /token/refresh
  GET   /me
  POST  /api-keys
  GET   /api-keys
  DELETE /api-keys/{key_id}
  GET   /internal/verify    Nginx auth_request 內部驗證端點
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.auth import router as auth_router
from .routers.api_keys import router as api_keys_router
from .routers.internal import router as internal_router
from .db import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="xCloudPDF Auth Service",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG") == "true" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,      prefix="",           tags=["Auth"])
app.include_router(api_keys_router,  prefix="/api-keys",  tags=["API Keys"])
app.include_router(internal_router,  prefix="/internal",  tags=["Internal"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth"}
