"""作業執行服務 — asyncio + ThreadPoolExecutor 非同步執行"""
from __future__ import annotations
import asyncio
import logging
import shutil
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..models.job import Job
from ..models.user import User
from ..tools.registry import TOOL_REGISTRY
from ..config import settings

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="job-worker")

# 追蹤正在執行的 asyncio Task，供強制取消使用
_running_tasks: dict[str, asyncio.Task] = {}

STORAGE_DIR = Path(settings.storage_local_path)
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "output"


def _ensure_dirs():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def cancel_running_job(job_id: str) -> bool:
    """強制取消正在執行的 asyncio Task。回傳 True 表示有找到並取消。"""
    task = _running_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        logger.info("Job %s: asyncio task cancelled", job_id)
        return True
    return False


async def create_job(
    db: AsyncSession,
    user: User,
    tool_id: str,
    input_filename: str,
    input_path: str,
    params: dict,
    priority: int = 5,
) -> Job:
    _ensure_dirs()
    job_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.file_retention_days)
    job = Job(
        id=job_id,
        user_id=user.id,
        tool_id=tool_id,
        status="queued",
        priority=priority,
        input_filename=input_filename,
        input_path=input_path,
        params=params,
        expires_at=expires_at,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 建立 asyncio Task 並追蹤
    task = asyncio.create_task(_run_job(job_id, tool_id, input_path, params))
    _running_tasks[job_id] = task
    task.add_done_callback(lambda t: _running_tasks.pop(job_id, None))
    return job


async def _run_job(job_id: str, tool_id: str, input_path: str, params: dict):
    """在 ThreadPoolExecutor 中執行工具，支援 asyncio 取消"""
    from ..database import AsyncSessionLocal

    workdir = Path(tempfile.mkdtemp(prefix=f"job_{job_id}_"))
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Job).where(Job.id == job_id).values(
                    status="running",
                    started_at=datetime.now(timezone.utc),
                    progress=10,
                )
            )
            await db.commit()

        tool = TOOL_REGISTRY.get(tool_id)
        if not tool:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Job).where(Job.id == job_id).values(
                        status="failed", error_message=f"工具 {tool_id} 不存在",
                        finished_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
            return

        inp_path = Path(input_path) if input_path else workdir / "dummy"

        # run_in_executor 可被 task.cancel() 中斷（在 await 點拋出 CancelledError）
        result = await asyncio.get_event_loop().run_in_executor(
            _executor,
            lambda: asyncio.run(tool.execute(inp_path, params, workdir))
        )

        async with AsyncSessionLocal() as db:
            # 執行完成前先確認 DB 狀態是否被外部取消
            current = (await db.execute(
                select(Job.status).where(Job.id == job_id)
            )).scalar_one_or_none()

            if current == "cancelled":
                return  # 外部已取消，不更新結果

            if result.success and result.output_path:
                out_dir = OUTPUT_DIR / job_id
                out_dir.mkdir(parents=True, exist_ok=True)
                dest = out_dir / (result.output_filename or result.output_path.name)
                shutil.copy2(str(result.output_path), str(dest))
                await db.execute(
                    update(Job).where(Job.id == job_id).values(
                        status="done",
                        output_path=str(dest),
                        output_filename=dest.name,
                        content_type=result.content_type,
                        progress=100,
                        metadata_=result.metadata,
                        finished_at=datetime.now(timezone.utc),
                        duration_seconds=int(
                            (datetime.now(timezone.utc) -
                             (await db.execute(select(Job.started_at).where(Job.id == job_id))).scalar_one()).total_seconds()
                        ) if False else None,  # 簡化，不重算
                    )
                )
            else:
                await db.execute(
                    update(Job).where(Job.id == job_id).values(
                        status="failed",
                        error_message=result.error or result.message,
                        finished_at=datetime.now(timezone.utc),
                    )
                )
            await db.commit()

    except asyncio.CancelledError:
        # Task 被強制取消 → 更新 DB 狀態
        logger.info("Job %s: cancelled by user", job_id)
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Job).where(Job.id == job_id).values(
                        status="cancelled",
                        error_message="由使用者強制取消",
                        finished_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
        except Exception:
            pass
        # 不重新拋出，讓 finally 清理

    except Exception as e:
        logger.exception("Job %s 執行失敗", job_id)
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Job).where(Job.id == job_id).values(
                        status="failed",
                        error_message=str(e),
                        finished_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
        except Exception:
            pass
    finally:
        shutil.rmtree(str(workdir), ignore_errors=True)
        _running_tasks.pop(job_id, None)


async def get_job(db: AsyncSession, job_id: str, user_id: int) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    tool_filter: str | None = None,
) -> tuple[list[Job], int]:
    from sqlalchemy import func
    query = select(Job).where(Job.user_id == user_id)
    count_query = select(func.count()).where(Job.user_id == user_id)
    if status_filter:
        query = query.where(Job.status == status_filter)
        count_query = count_query.where(Job.status == status_filter)
    if tool_filter:
        query = query.where(Job.tool_id == tool_filter)
        count_query = count_query.where(Job.tool_id == tool_filter)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(Job.queued_at.desc()).offset((page - 1) * page_size).limit(page_size)
    jobs = (await db.execute(query)).scalars().all()
    return list(jobs), total
