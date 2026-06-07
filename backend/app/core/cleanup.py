"""定期清理過期作業記錄與對應檔案"""
from __future__ import annotations
import asyncio
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, delete

from ..database import AsyncSessionLocal
from ..config import settings

logger = logging.getLogger(__name__)

STORAGE_DIR   = Path(settings.storage_local_path)
OUTPUT_DIR    = STORAGE_DIR / "output"
UPLOAD_DIR    = STORAGE_DIR / "uploads"
CLEANUP_INTERVAL = 3600  # 每小時執行一次


async def cleanup_expired() -> dict:
    """
    清除 expires_at 已過期的作業：
    - 刪除輸出目錄（output/<job_id>/）
    - 刪除上傳檔案（uploads/<uuid>）
    - 從 DB 刪除 Job 記錄
    回傳 {"deleted_jobs": N, "freed_files": N}
    """
    from ..models.job import Job  # 避免循環匯入

    now   = datetime.now(timezone.utc)
    freed = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job).where(Job.expires_at <= now)
        )
        expired = result.scalars().all()

        for job in expired:
            # 輸出目錄
            out_dir = OUTPUT_DIR / job.id
            if out_dir.exists():
                shutil.rmtree(str(out_dir), ignore_errors=True)
                freed += 1
            # 上傳檔案
            if job.input_path:
                inp = Path(job.input_path)
                if inp.exists():
                    inp.unlink(missing_ok=True)
                    freed += 1

        count = len(expired)
        if count:
            await db.execute(delete(Job).where(Job.expires_at <= now))
            await db.commit()
            logger.info("過期清理完成：%d 筆作業、%d 個檔案已刪除", count, freed)
        else:
            logger.debug("過期清理：無需清理的記錄")

    return {"deleted_jobs": count, "freed_files": freed}


async def run_cleanup_scheduler() -> None:
    """背景排程：啟動後立即執行一次，之後每小時重複。"""
    while True:
        try:
            await cleanup_expired()
        except Exception:
            logger.exception("過期清理排程發生例外")
        await asyncio.sleep(CLEANUP_INTERVAL)
