from __future__ import annotations
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..core.deps import CurrentUser
from ..core.security import hash_password
from ..models.user import User, Role, UserRole, Realm, Session, APIToken
from ..models.job import Job
from ..schemas.auth import UserCreate, UserUpdate, UserOut
from ..tools.registry import TOOL_REGISTRY

router = APIRouter()


def _require_admin(user: CurrentUser):
    if not user.is_superadmin:
        raise HTTPException(403, "需要管理員權限")
    return user


# ─── 統計 ────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_jobs = (await db.execute(select(func.count()).select_from(Job))).scalar_one()
    done_jobs = (await db.execute(select(func.count()).select_from(Job).where(Job.status == "done"))).scalar_one()
    failed_jobs = (await db.execute(select(func.count()).select_from(Job).where(Job.status == "failed"))).scalar_one()
    running_jobs = (await db.execute(select(func.count()).select_from(Job).where(Job.status == "running"))).scalar_one()
    total_tools = len([t for t in TOOL_REGISTRY.values() if t.enabled])

    from sqlalchemy import cast, Date
    result = await db.execute(
        select(
            cast(Job.queued_at, Date).label("date"),
            func.count().label("count")
        ).group_by(cast(Job.queued_at, Date)).order_by(cast(Job.queued_at, Date).desc()).limit(7)
    )
    trend = [{"date": str(row.date), "count": row.count} for row in result.all()]

    # 依網域類型統計使用者
    realm_result = await db.execute(
        select(Realm.type, func.count(User.id).label("count"))
        .join(User, User.realm_id == Realm.id)
        .group_by(Realm.type)
    )
    users_by_realm = {row.type: row.count for row in realm_result.all()}

    return {
        "users": total_users,
        "users_by_realm": users_by_realm,
        "jobs": {"total": total_jobs, "done": done_jobs, "failed": failed_jobs, "running": running_jobs},
        "tools": total_tools,
        "job_trend": trend[::-1],
    }


# ─── 使用者管理 ──────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    user: CurrentUser, db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
):
    _require_admin(user)
    query = select(User).options(selectinload(User.realm), selectinload(User.user_roles).selectinload(UserRole.role))
    if q:
        query = query.where(User.username.contains(q) | User.display_name.contains(q))
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    users = (await db.execute(query.offset((page-1)*page_size).limit(page_size))).scalars().all()

    def _u(u: User):
        roles = [ur.role.name for ur in u.user_roles if ur.role]
        return {
            "id": u.id, "username": u.username,
            "realm": u.realm.name if u.realm else "local",
            "realm_type": u.realm.type if u.realm else "local",
            "display_name": u.display_name, "email": u.email,
            "roles": roles, "is_superadmin": u.is_superadmin,
            "enabled": u.enabled,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat(),
        }

    return {"users": [_u(u) for u in users], "total": total, "page": page, "page_size": page_size}


@router.post("/users")
async def create_user(req: UserCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    result = await db.execute(select(Realm).where(Realm.name == req.realm))
    realm = result.scalar_one_or_none()
    if not realm:
        raise HTTPException(400, f"Realm {req.realm} 不存在")

    existing = (await db.execute(
        select(User).where(User.username == req.username, User.realm_id == realm.id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "使用者名稱已存在")

    new_user = User(
        username=req.username,
        realm_id=realm.id,
        password_hash=hash_password(req.password) if req.password else None,
        display_name=req.display_name or req.username,
        email=req.email,
        enabled=True,
    )
    db.add(new_user)
    await db.flush()

    for role_name in req.roles:
        role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
        if role:
            db.add(UserRole(user_id=new_user.id, role_id=role.id))

    await db.commit()
    return {"message": "使用者已建立", "id": new_user.id}


@router.put("/users/{user_id}")
async def update_user(user_id: int, req: UserUpdate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "使用者不存在")

    updates = {}
    if req.display_name is not None:
        updates["display_name"] = req.display_name
    if req.email is not None:
        updates["email"] = req.email
    if req.password is not None:
        updates["password_hash"] = hash_password(req.password)
    if req.enabled is not None:
        updates["enabled"] = req.enabled

    if updates:
        await db.execute(update(User).where(User.id == user_id).values(**updates))

    if req.roles is not None:
        for ur in (await db.execute(select(UserRole).where(UserRole.user_id == user_id))).scalars().all():
            await db.delete(ur)
        await db.flush()
        for role_name in req.roles:
            role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
            if role:
                db.add(UserRole(user_id=user_id, role_id=role.id))

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    if user_id == user.id:
        raise HTTPException(400, "不能刪除自己的帳號")
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "使用者不存在")
    await db.delete(target)
    await db.commit()
    return {"message": "使用者已刪除"}


# ─── 角色管理 ────────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    roles = (await db.execute(select(Role).order_by(Role.level.desc()))).scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "display_name": r.display_name,
            "level": r.level,
            "builtin": r.builtin,
            "permissions": r.permissions or [],
        }
        for r in roles
    ]


# ─── Realm（認證網域）管理 ────────────────────────────────────────────────────

class RealmCreate(BaseModel):
    name: str
    type: str = "ldap"  # local | ldap | ad
    display_name: str = ""
    config: dict = {}
    enabled: bool = True


class RealmUpdate(BaseModel):
    display_name: str | None = None
    config: dict | None = None
    enabled: bool | None = None


def _realm_to_dict(r: Realm, user_count: int = 0) -> dict:
    safe_config = {k: v for k, v in (r.config or {}).items() if k != "bind_password"}
    return {
        "id": r.id,
        "name": r.name,
        "type": r.type,
        "display_name": (r.config or {}).get("display_name", ""),
        "config": safe_config,
        "enabled": r.enabled,
        "user_count": user_count,
        "created_at": r.created_at.isoformat(),
    }


@router.get("/realms")
async def list_realms(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    realms = (await db.execute(select(Realm).order_by(Realm.id))).scalars().all()
    counts_result = await db.execute(
        select(User.realm_id, func.count(User.id)).group_by(User.realm_id)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}
    return [_realm_to_dict(r, counts.get(r.id, 0)) for r in realms]


@router.post("/realms")
async def create_realm(req: RealmCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    if req.type == "local":
        raise HTTPException(400, "不可新增本機 Realm，系統已內建")
    existing = (await db.execute(select(Realm).where(Realm.name == req.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Realm 名稱已存在")

    config = dict(req.config)
    if req.display_name:
        config["display_name"] = req.display_name

    realm = Realm(name=req.name, type=req.type, config=config, enabled=req.enabled)
    db.add(realm)
    await db.commit()
    await db.refresh(realm)
    return {"message": "認證網域已建立", "id": realm.id}


@router.put("/realms/{realm_id}")
async def update_realm(realm_id: int, req: RealmUpdate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    realm = (await db.execute(select(Realm).where(Realm.id == realm_id))).scalar_one_or_none()
    if not realm:
        raise HTTPException(404, "Realm 不存在")
    if realm.type == "local" and req.config is not None:
        raise HTTPException(400, "本機 Realm 不可修改設定")

    updates: dict = {}
    if req.enabled is not None:
        if realm.type == "local" and not req.enabled:
            raise HTTPException(400, "不可停用本機 Realm")
        updates["enabled"] = req.enabled

    if req.config is not None or req.display_name is not None:
        new_config = dict(realm.config or {})
        if req.config is not None:
            new_config.update(req.config)
        if req.display_name is not None:
            new_config["display_name"] = req.display_name
        updates["config"] = new_config

    if updates:
        await db.execute(update(Realm).where(Realm.id == realm_id).values(**updates))
        await db.commit()

    updated = (await db.execute(select(Realm).where(Realm.id == realm_id))).scalar_one()
    return _realm_to_dict(updated)


@router.delete("/realms/{realm_id}")
async def delete_realm(realm_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _require_admin(user)
    realm = (await db.execute(select(Realm).where(Realm.id == realm_id))).scalar_one_or_none()
    if not realm:
        raise HTTPException(404, "Realm 不存在")
    if realm.type == "local":
        raise HTTPException(400, "不可刪除本機 Realm")

    user_count = (await db.execute(
        select(func.count()).select_from(User).where(User.realm_id == realm_id)
    )).scalar_one()
    if user_count > 0:
        raise HTTPException(400, f"此 Realm 尚有 {user_count} 個使用者，請先移除使用者再刪除")

    await db.delete(realm)
    await db.commit()
    return {"message": "認證網域已刪除"}


@router.post("/realms/{realm_id}/test")
async def test_realm_connection(realm_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """測試 LDAP/AD 連線是否正常。"""
    _require_admin(user)
    realm = (await db.execute(select(Realm).where(Realm.id == realm_id))).scalar_one_or_none()
    if not realm:
        raise HTTPException(404, "Realm 不存在")
    if realm.type == "local":
        return {"success": True, "message": "本機 Realm 無需測試連線"}

    def _test_sync(realm_type: str, config: dict):
        try:
            from ldap3 import Server, Connection, ALL
            url = config.get("url", "")
            bind_dn = config.get("bind_dn", "")
            bind_password = config.get("bind_password", "")
            if not url:
                return False, "未設定伺服器 URL"
            server = Server(url, get_info=ALL, connect_timeout=5)
            if bind_dn and bind_password:
                conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
            else:
                conn = Connection(server, auto_bind=True)
            info = f"已連線至 {url}（伺服器版本：{server.info.vendor_version if server.info else '未知'}）"
            conn.unbind()
            return True, info
        except Exception as e:
            return False, str(e)

    loop = asyncio.get_event_loop()
    ok, msg = await loop.run_in_executor(None, _test_sync, realm.type, realm.config or {})
    return {"success": ok, "message": msg}


# ─── Realm 目錄瀏覽與同步 ─────────────────────────────────────────────────────

@router.get("/realms/{realm_id}/users")
async def list_realm_directory_users(realm_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """從 LDAP/AD 目錄撈出所有使用者，並標記是否已匯入。"""
    _require_admin(user)
    realm = (await db.execute(select(Realm).where(Realm.id == realm_id))).scalar_one_or_none()
    if not realm:
        raise HTTPException(404, "Realm 不存在")
    if realm.type == "local":
        raise HTTPException(400, "本機 Realm 不支援目錄查詢")

    def _search_sync(realm_type: str, config: dict):
        from ldap3 import Server, Connection, ALL, SUBTREE
        url         = config.get("url", "")
        bind_dn     = config.get("bind_dn", "")
        bind_pw     = config.get("bind_password", "")
        base_dn     = config.get("base_dn", "")
        dn_attr     = config.get("display_name_attr", "displayName" if realm_type == "ad" else "cn")
        email_attr  = config.get("email_attr", "mail")

        if realm_type == "ad":
            list_filter  = "(&(objectCategory=person)(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
            uname_attr   = "sAMAccountName"
        else:
            list_filter  = "(objectClass=inetOrgPerson)"
            uname_attr   = "uid"

        server = Server(url, get_info=ALL, connect_timeout=8)
        conn = Connection(server, user=bind_dn, password=bind_pw, auto_bind=True) \
               if (bind_dn and bind_pw) else Connection(server, auto_bind=True)

        conn.search(base_dn, list_filter, SUBTREE,
                    attributes=[uname_attr, dn_attr, email_attr],
                    size_limit=1000)

        results = []
        for entry in conn.entries:
            try:
                uname = str(entry[uname_attr].value) if entry[uname_attr] else None
                if not uname:
                    continue
                dname = str(entry[dn_attr].value) if entry[dn_attr] else uname
                email = str(entry[email_attr].value) if entry[email_attr] else None
                results.append({"username": uname, "display_name": dname, "email": email})
            except Exception:
                continue
        conn.unbind()
        return sorted(results, key=lambda x: x["username"].lower())

    loop = asyncio.get_event_loop()
    try:
        dir_users = await loop.run_in_executor(None, _search_sync, realm.type, realm.config or {})
    except Exception as e:
        raise HTTPException(500, f"目錄查詢失敗：{e}")

    existing = set((await db.execute(
        select(User.username).where(User.realm_id == realm_id)
    )).scalars().all())

    for u in dir_users:
        u["imported"] = u["username"] in existing

    return dir_users


class SyncUsersReq(BaseModel):
    usernames: list[str]


@router.post("/realms/{realm_id}/sync")
async def sync_realm_users(realm_id: int, req: SyncUsersReq, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """將選取的目錄使用者匯入系統並套用預設角色。"""
    _require_admin(user)
    realm = (await db.execute(select(Realm).where(Realm.id == realm_id))).scalar_one_or_none()
    if not realm:
        raise HTTPException(404, "Realm 不存在")
    if realm.type == "local":
        raise HTTPException(400, "本機 Realm 不支援同步")
    if not req.usernames:
        raise HTTPException(400, "未選取任何使用者")

    default_roles: list[str] = (realm.config or {}).get("default_roles", ["viewer"])
    imported = skipped = 0

    for uname in req.usernames:
        existing = (await db.execute(
            select(User).where(User.username == uname, User.realm_id == realm_id)
        )).scalar_one_or_none()
        if existing:
            skipped += 1
            continue

        new_u = User(username=uname, realm_id=realm_id, display_name=uname, enabled=True)
        db.add(new_u)
        await db.flush()

        for role_name in default_roles:
            role_obj = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
            if role_obj:
                db.add(UserRole(user_id=new_u.id, role_id=role_obj.id))

        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped}


# ─── 系統健康 ────────────────────────────────────────────────────────────────

@router.get("/system/health")
async def system_health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "tools_loaded": len(TOOL_REGISTRY),
    }
