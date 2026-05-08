from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database import get_db
from ..core.deps import CurrentUser
from ..models.job import Job
from ..services.job_service import get_job, list_jobs

router = APIRouter()


@router.get("")
async def list_my_jobs(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    tool_id: str | None = Query(None),
):
    jobs, total = await list_jobs(db, user.id, page, page_size, status, tool_id)
    return {
        "jobs": [_job_to_dict(j) for j in jobs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{job_id}")
async def get_job_detail(job_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id, user.id)
    if not job:
        raise HTTPException(404, "作業不存在")
    return _job_to_dict(job)


@router.get("/{job_id}/download")
async def download_job_result(job_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id, user.id)
    if not job:
        raise HTTPException(404, "作業不存在")
    if job.status != "done":
        raise HTTPException(400, f"作業尚未完成（當前狀態：{job.status}）")
    if not job.output_path:
        raise HTTPException(404, "找不到輸出檔案")

    output_path = Path(job.output_path)
    if not output_path.exists():
        raise HTTPException(404, "輸出檔案已過期或被刪除")

    return FileResponse(
        path=str(output_path),
        filename=job.output_filename or output_path.name,
        media_type=job.content_type,
    )


@router.delete("/{job_id}")
async def cancel_or_delete_job(job_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id, user.id)
    if not job:
        raise HTTPException(404, "作業不存在")

    if job.status in ("queued", "running"):
        from ..services.job_service import cancel_running_job
        # 強制取消 asyncio Task（若仍在執行）
        cancel_running_job(job_id)
        # 立即更新 DB，不等 Task 內部的 CancelledError handler
        await db.execute(
            update(Job).where(Job.id == job_id).values(
                status="cancelled",
                error_message="由使用者強制取消",
                finished_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        return {"message": "作業已強制取消"}

    elif job.status == "done":
        if job.output_path:
            import shutil
            out = Path(job.output_path).parent
            shutil.rmtree(str(out), ignore_errors=True)
        await db.delete(job)
        await db.commit()
        return {"message": "作業已刪除"}

    else:
        # cancelled / failed → 直接刪除記錄
        await db.delete(job)
        await db.commit()
        return {"message": "作業記錄已刪除"}


def _job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "tool_id": job.tool_id,
        "status": job.status,
        "progress": job.progress,
        "input_filename": job.input_filename,
        "output_filename": job.output_filename,
        "content_type": job.content_type,
        "params": job.params,
        "error_message": job.error_message,
        "metadata": job.metadata_,
        "duration_seconds": job.duration_seconds,
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "expires_at": job.expires_at.isoformat() if job.expires_at else None,
    }
