from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import init_db, AsyncSessionLocal
from .core.init_data import seed_database
from .routers import auth, tools, jobs, admin, search

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("xPDFedit 啟動中...")
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_database(db)
    logger.info("資料庫初始化完成，工具數量: %d", len(tools.TOOL_REGISTRY))
    yield
    logger.info("xPDFedit 關閉")


app = FastAPI(
    title="xPDFedit API",
    description="xCloudinfo 文件智能平台",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未處理例外: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "伺服器內部錯誤"})


# ── API v1 路由 ───────────────────────────────────────────────────────────────
app.include_router(auth.router,   prefix="/api/v1/auth",   tags=["認證"])
app.include_router(tools.router,  prefix="/api/v1/tools",  tags=["工具"])
app.include_router(jobs.router,   prefix="/api/v1/jobs",   tags=["作業"])
app.include_router(admin.router,  prefix="/api/v1/admin",  tags=["管理"])
app.include_router(search.router, prefix="/api/v1/search", tags=["語意搜尋"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/")
async def root():
    return {"message": "xPDFedit API", "docs": "/api/docs"}
