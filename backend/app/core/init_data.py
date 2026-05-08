"""初始化資料庫預設資料（Realm, Roles, 預設管理員）"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.user import Realm, Role, User, UserRole
from ..core.security import hash_password


DEFAULT_ROLES = [
    {"name": "superadmin", "display_name": "超級管理員", "level": 50, "builtin": True,
     "permissions": ["*"]},
    {"name": "admin", "display_name": "管理員", "level": 40, "builtin": True,
     "permissions": ["tool:*", "document:*", "job:*", "user:*", "settings:*", "audit:read", "audit:export"]},
    {"name": "manager", "display_name": "管理者", "level": 30, "builtin": True,
     "permissions": ["tool:read", "tool:execute", "document:*", "job:*", "audit:read", "audit:export"]},
    {"name": "operator", "display_name": "操作員", "level": 20, "builtin": True,
     "permissions": ["tool:read", "tool:execute", "document:read", "document:create", "document:delete", "job:*"]},
    {"name": "viewer", "display_name": "檢視者", "level": 10, "builtin": True,
     "permissions": ["tool:read", "document:read", "job:read"]},
    {"name": "guest", "display_name": "訪客", "level": 0, "builtin": True,
     "permissions": ["tool:read"]},
]


async def seed_database(db: AsyncSession) -> None:
    # 建立預設 Realm
    result = await db.execute(select(Realm).where(Realm.name == "local"))
    if not result.scalar_one_or_none():
        local_realm = Realm(name="local", type="local", enabled=True)
        db.add(local_realm)
        await db.flush()
    else:
        result = await db.execute(select(Realm).where(Realm.name == "local"))
        local_realm = result.scalar_one()

    # 建立預設角色
    for role_data in DEFAULT_ROLES:
        result = await db.execute(select(Role).where(Role.name == role_data["name"]))
        if not result.scalar_one_or_none():
            db.add(Role(**role_data))

    await db.flush()

    # 建立預設管理員帳號 admin / admin1234
    result = await db.execute(select(User).where(User.username == "admin"))
    if not result.scalar_one_or_none():
        admin = User(
            username="admin",
            realm_id=local_realm.id,
            password_hash=hash_password("admin1234"),
            display_name="系統管理員",
            email="admin@cloudinfo.com.tw",
            is_superadmin=True,
            enabled=True,
        )
        db.add(admin)
        await db.flush()

        result = await db.execute(select(Role).where(Role.name == "superadmin"))
        superadmin_role = result.scalar_one_or_none()
        if superadmin_role:
            db.add(UserRole(user_id=admin.id, role_id=superadmin_role.id))

    await db.commit()
