"""測試過期作業清理邏輯"""
from __future__ import annotations
import pytest
import uuid
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _insert_job(db, expires_delta: timedelta, create_files: bool = False):
    """插入一筆 Job，expires_at 由 expires_delta 決定。"""
    from app.models.job import Job
    from app.models.user import User

    user = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    input_file = output_file = None
    if create_files:
        # 建立暫存檔模擬上傳/輸出
        tf_in = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tf_in.write(b"%PDF fake"); tf_in.close()
        input_file = tf_in.name

    job = Job(
        id=job_id,
        user_id=user.id,
        tool_id="pdf-to-txt",
        status="done",
        input_filename="test.pdf",
        input_path=input_file,
        output_path=output_file,
        queued_at=now,
        expires_at=now + expires_delta,
    )
    db.add(job)
    await db.commit()
    return job


class TestCleanup:

    async def test_expired_job_deleted(self, db):
        """過期作業應被清理，未過期的應保留"""
        from app.core.cleanup import cleanup_expired

        # 建立 1 筆已過期、1 筆未過期
        expired = await _insert_job(db, timedelta(seconds=-1))
        fresh   = await _insert_job(db, timedelta(days=7))

        result = await cleanup_expired()

        assert result["deleted_jobs"] >= 1

        from app.models.job import Job
        remaining = (await db.execute(select(Job))).scalars().all()
        ids = [j.id for j in remaining]
        assert expired.id not in ids
        assert fresh.id in ids

    async def test_expired_input_file_deleted(self, db, tmp_path):
        """過期作業的輸入檔應被刪除"""
        from app.core.cleanup import cleanup_expired
        from app.models.job import Job
        import shutil

        # 建立真實的輸入檔
        fake_input = tmp_path / "upload.pdf"
        fake_input.write_bytes(b"%PDF fake")

        from app.models.user import User
        user = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        job = Job(
            id=job_id,
            user_id=user.id,
            tool_id="pdf-to-txt",
            status="done",
            input_filename="upload.pdf",
            input_path=str(fake_input),
            queued_at=now,
            expires_at=now - timedelta(seconds=1),
        )
        db.add(job)
        await db.commit()

        assert fake_input.exists()
        await cleanup_expired()
        assert not fake_input.exists()

    async def test_not_expired_job_preserved(self, db):
        """未過期的作業不應被清理"""
        from app.core.cleanup import cleanup_expired
        from app.models.job import Job

        fresh = await _insert_job(db, timedelta(days=3))

        await cleanup_expired()

        found = (await db.execute(select(Job).where(Job.id == fresh.id))).scalar_one_or_none()
        assert found is not None

    async def test_cleanup_idempotent(self, db):
        """重複執行清理不應出錯"""
        from app.core.cleanup import cleanup_expired

        await _insert_job(db, timedelta(seconds=-1))
        r1 = await cleanup_expired()
        r2 = await cleanup_expired()  # 第二次應無作業可刪

        assert r1["deleted_jobs"] >= 1
        assert r2["deleted_jobs"] == 0

    async def test_admin_trigger_endpoint(self, client, auth_headers):
        """POST /admin/system/cleanup 應回傳 200"""
        resp = await client.post("/api/v1/admin/system/cleanup", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted_jobs" in data
        assert "freed_files" in data
