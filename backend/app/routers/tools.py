from __future__ import annotations
import tempfile
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..core.deps import CurrentUser
from ..tools.registry import TOOL_REGISTRY
from ..services.job_service import create_job, UPLOAD_DIR
from ..config import settings

router = APIRouter()


@router.get("")
async def list_tools():
    """列出所有可用工具"""
    tools = [t.to_dict() for t in TOOL_REGISTRY.values() if t.enabled]
    return {"tools": tools, "total": len(tools)}


@router.get("/{tool_id}")
async def get_tool(tool_id: str):
    tool = TOOL_REGISTRY.get(tool_id)
    if not tool:
        raise HTTPException(404, f"工具 {tool_id} 不存在")
    return tool.to_dict()


@router.post("/{tool_id}/submit")
async def submit_tool(
    tool_id: str,
    user: CurrentUser,
    files: List[UploadFile] = File(...),
    params: str = Form("{}"),
    db: AsyncSession = Depends(get_db),
):
    """非同步提交作業，回傳 job_id（支援多檔案）"""
    import json
    tool = TOOL_REGISTRY.get(tool_id)
    if not tool:
        raise HTTPException(404, f"工具 {tool_id} 不存在")

    max_size = settings.max_upload_size_mb * 1024 * 1024
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # 儲存所有上傳檔案
    saved_paths: list[Path] = []
    for upload in files:
        content = await upload.read()
        if len(content) > max_size:
            raise HTTPException(413, f"檔案 {upload.filename} 超過 {settings.max_upload_size_mb}MB 限制")
        file_id = str(uuid.uuid4())
        suffix = Path(upload.filename or "file").suffix
        upload_path = UPLOAD_DIR / f"{file_id}{suffix}"
        upload_path.write_bytes(content)
        saved_paths.append(upload_path)

    try:
        params_dict = json.loads(params)
    except Exception:
        params_dict = {}

    # 第一個檔案為主輸入，其餘作為 extra_files 傳入 params
    if len(saved_paths) > 1:
        params_dict["extra_files"] = [str(p) for p in saved_paths[1:]]

    primary = saved_paths[0]
    job = await create_job(
        db=db,
        user=user,
        tool_id=tool_id,
        input_filename=files[0].filename or "file",
        input_path=str(primary),
        params=params_dict,
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "tool_id": tool_id,
        "message": "作業已提交",
    }


@router.post("/{tool_id}/execute")
async def execute_tool_sync(
    tool_id: str,
    user: CurrentUser,
    file: UploadFile = File(...),
    params: str = Form("{}"),
):
    """同步執行（小檔案，直接回傳結果）"""
    import json
    tool = TOOL_REGISTRY.get(tool_id)
    if not tool:
        raise HTTPException(404, f"工具 {tool_id} 不存在")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "同步執行限制 20MB，大檔案請使用 /submit")

    try:
        params_dict = json.loads(params)
    except Exception:
        params_dict = {}

    workdir = Path(tempfile.mkdtemp(prefix="sync_"))
    try:
        suffix = Path(file.filename or "file").suffix
        input_path = workdir / f"input{suffix}"
        input_path.write_bytes(content)

        result = await tool.execute(input_path, params_dict, workdir)
        if not result.success:
            raise HTTPException(422, result.error or "執行失敗")

        return FileResponse(
            path=str(result.output_path),
            filename=result.output_filename or result.output_path.name,
            media_type=result.content_type,
            background=None,  # 直接串流
        )
    finally:
        # FileResponse 需要檔案存在，刪除在回應後進行
        # 暫時不刪除（讓 OS 清理 temp）
        pass
