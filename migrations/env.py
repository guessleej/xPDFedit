"""Alembic 遷移環境設定 — PostgreSQL (asyncpg)"""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 匯入所有 models 讓 Alembic 能偵測變更
from services.auth.app.models import Base as AuthBase         # noqa: F401
from services.document.app.models import Base as DocBase      # noqa: F401
from services.job.app.models import Base as JobBase           # noqa: F401

# 合併所有 metadata
from sqlalchemy import MetaData
target_metadata = MetaData()
for base in [AuthBase, DocBase, JobBase]:
    for table in base.metadata.tables.values():
        table.to_metadata(target_metadata)

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+asyncpg://xcloud:xcloud@localhost:5432/xcloudpdf")
# Alembic 需同步 URL（遷移時用）
SYNC_URL = POSTGRES_URL.replace("+asyncpg", "")


def run_migrations_offline() -> None:
    context.configure(
        url=SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = POSTGRES_URL
    engine = async_engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
