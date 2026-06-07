"""測試每日配額強制執行"""
from __future__ import annotations
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _get_admin(db):
    from app.models.user import User
    return (await db.execute(select(User).where(User.username == "admin"))).scalar_one()


async def _create_fake_job(db, user_id: int, queued_at=None):
    """直接插入一筆 Job 記錄（不真的執行工具）"""
    import uuid
    from app.models.job import Job
    now = queued_at or datetime.now(timezone.utc)
    job = Job(
        id=str(uuid.uuid4()),
        user_id=user_id,
        tool_id="pdf-compress",
        status="done",
        input_filename="test.pdf",
        queued_at=now,
        expires_at=now + timedelta(days=7),
    )
    db.add(job)
    await db.commit()
    return job


class TestDailyQuota:

    async def test_no_limit_by_default(self, db):
        """daily_limit 預設為 None，不應限制作業數量"""
        user = await _get_admin(db)
        assert user.daily_limit is None

    async def test_quota_not_triggered_when_none(self, db):
        """daily_limit=None 時，create_job 不應拋出 429"""
        from app.services.job_service import create_job
        import tempfile, pathlib
        user = await _get_admin(db)

        # 建一個假的輸入檔
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp = f.name

        # 不應拋出異常
        job = await create_job(db, user, "pdf-to-txt", "test.pdf", tmp, {})
        assert job.id is not None

    async def test_quota_enforced_when_exceeded(self, db):
        """daily_limit=2 時，第3筆應拋出 HTTP 429"""
        from fastapi import HTTPException
        from sqlalchemy import update
        from app.models.user import User
        from app.services.job_service import create_job
        import tempfile

        user = await _get_admin(db)

        # 設定 daily_limit = 2
        await db.execute(update(User).where(User.id == user.id).values(daily_limit=2))
        await db.commit()
        await db.refresh(user)

        # 插入今日 2 筆已存在的作業
        await _create_fake_job(db, user.id)
        await _create_fake_job(db, user.id)

        # 第 3 筆應被擋下
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp = f.name

        with pytest.raises(HTTPException) as exc_info:
            await create_job(db, user, "pdf-to-txt", "test.pdf", tmp, {})

        assert exc_info.value.status_code == 429
        assert "每日限制" in exc_info.value.detail

    async def test_yesterday_jobs_not_counted(self, db):
        """昨天的作業不應計入今日配額"""
        from sqlalchemy import update
        from app.models.user import User
        from app.services.job_service import create_job
        import tempfile

        user = await _get_admin(db)
        await db.execute(update(User).where(User.id == user.id).values(daily_limit=1))
        await db.commit()
        await db.refresh(user)

        # 插入昨天的作業
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        await _create_fake_job(db, user.id, queued_at=yesterday)

        # 今天的第一筆應成功（昨天的不算）
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp = f.name

        job = await create_job(db, user, "pdf-to-txt", "test.pdf", tmp, {})
        assert job.id is not None

    async def test_update_daily_limit_via_admin(self, client, auth_headers):
        """透過 PUT /admin/users/{id} 設定 daily_limit"""
        # 取得 admin user id
        resp = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 200
        users = resp.json()["users"]
        admin_id = next(u["id"] for u in users if u["username"] == "admin")

        # 設定 daily_limit = 5
        resp = await client.put(
            f"/api/v1/admin/users/{admin_id}",
            json={"daily_limit": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # 確認回傳值
        resp2 = await client.get("/api/v1/admin/users", headers=auth_headers)
        admin = next(u for u in resp2.json()["users"] if u["id"] == admin_id)
        assert admin["daily_limit"] == 5

    async def test_clear_daily_limit(self, client, auth_headers):
        """daily_limit = -1 應清除限制（設為 NULL）"""
        resp = await client.get("/api/v1/admin/users", headers=auth_headers)
        admin_id = next(u["id"] for u in resp.json()["users"] if u["username"] == "admin")

        await client.put(f"/api/v1/admin/users/{admin_id}", json={"daily_limit": 3}, headers=auth_headers)
        await client.put(f"/api/v1/admin/users/{admin_id}", json={"daily_limit": -1}, headers=auth_headers)

        resp2 = await client.get("/api/v1/admin/users", headers=auth_headers)
        admin = next(u for u in resp2.json()["users"] if u["id"] == admin_id)
        assert admin["daily_limit"] is None
