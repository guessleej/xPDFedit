from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.user import User, Realm, Role, UserRole, Session, APIToken
from ..schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    UserOut, APITokenCreate, APITokenOut, APITokenCreated,
)
from ..core.security import (
    verify_password, hash_token, generate_token,
    create_access_token, create_refresh_token, hash_password,
)
from ..core.deps import CurrentUser, get_current_user
from ..config import settings

router = APIRouter()


# ─── LDAP / AD 認證 ──────────────────────────────────────────────────────────

def _ldap_authenticate_sync(realm_type: str, config: dict, username: str, password: str) -> dict | None:
    """同步執行 LDAP 認證（在 thread pool 中呼叫）。成功回傳使用者資訊，失敗回傳 None。"""
    try:
        from ldap3 import Server, Connection, ALL, SUBTREE, AUTO_BIND_NO_TLS
        url = config.get("url", "")
        bind_dn = config.get("bind_dn", "")
        bind_password = config.get("bind_password", "")
        base_dn = config.get("base_dn", "")
        default_filter = "(sAMAccountName={username})" if realm_type == "ad" else "(uid={username})"
        user_filter = config.get("user_filter", default_filter)
        dn_attr = config.get("display_name_attr", "displayName" if realm_type == "ad" else "cn")
        email_attr = config.get("email_attr", "mail")

        if not url or not base_dn:
            return None

        server = Server(url, get_info=ALL, connect_timeout=5)

        # Step 1: 以服務帳號綁定並搜尋使用者 DN
        if bind_dn and bind_password:
            svc = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
        else:
            svc = Connection(server, auto_bind=True)

        search_filter = user_filter.format(username=username)
        svc.search(base_dn, search_filter, SUBTREE, attributes=[dn_attr, email_attr])
        entries = list(svc.entries)
        svc.unbind()

        if not entries:
            return None

        entry = entries[0]
        user_dn = entry.entry_dn

        # Step 2: 以使用者身份綁定驗證密碼
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        bound = user_conn.bound
        user_conn.unbind()

        if not bound:
            return None

        try:
            display_name = str(entry[dn_attr].value) if entry[dn_attr] else username
        except Exception:
            display_name = username
        try:
            email = str(entry[email_attr].value) if entry[email_attr] else None
        except Exception:
            email = None

        return {"display_name": display_name, "email": email}
    except Exception:
        return None


async def _ldap_authenticate(realm: Realm, username: str, password: str) -> dict | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _ldap_authenticate_sync, realm.type, realm.config or {}, username, password
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _user_to_out(user: User, roles: list[str]) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        realm=user.realm.name if user.realm else "local",
        display_name=user.display_name,
        email=user.email,
        roles=roles,
        is_superadmin=user.is_superadmin,
        enabled=user.enabled,
        last_login=user.last_login,
        created_at=user.created_at,
    )


# ─── 公開：列出可用 Realm ─────────────────────────────────────────────────────

@router.get("/realms")
async def list_public_realms(db: AsyncSession = Depends(get_db)):
    """登入頁使用：列出所有已啟用的認證網域。"""
    result = await db.execute(select(Realm).where(Realm.enabled == True).order_by(Realm.id))
    realms = result.scalars().all()
    return [
        {"name": r.name, "type": r.type, "label": _realm_label(r)}
        for r in realms
    ]


def _realm_label(r: Realm) -> str:
    labels = {"local": "本機帳號", "ldap": "LDAP 目錄", "ad": "Active Directory"}
    display = (r.config or {}).get("display_name", "")
    return display or labels.get(r.type, r.name)


# ─── 登入 ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # 解析 username@realm
    username = req.username
    realm_name = req.realm
    if "@" in req.username:
        parts = req.username.rsplit("@", 1)
        username, realm_name = parts[0], parts[1]

    result = await db.execute(
        select(Realm).where(Realm.name == realm_name, Realm.enabled == True)
    )
    realm = result.scalar_one_or_none()
    if not realm:
        raise HTTPException(status_code=401, detail="無效的 Realm")

    # ── LDAP / AD 認證 ──
    if realm.type in ("ldap", "ad"):
        ldap_info = await _ldap_authenticate(realm, username, req.password)
        if ldap_info is None:
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

        # 查找或自動建立使用者
        result = await db.execute(
            select(User)
            .where(User.username == username, User.realm_id == realm.id)
            .options(selectinload(User.realm))
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                username=username,
                realm_id=realm.id,
                display_name=ldap_info["display_name"],
                email=ldap_info["email"],
                enabled=True,
            )
            db.add(user)
            await db.flush()
            default_roles: list[str] = (realm.config or {}).get("default_roles", ["viewer"])
            for role_name in default_roles:
                role_obj = (await db.execute(
                    select(Role).where(Role.name == role_name)
                )).scalar_one_or_none()
                if role_obj:
                    db.add(UserRole(user_id=user.id, role_id=role_obj.id))
            await db.flush()  # 確保 UserRole 在角色查詢前可見
        elif not user.enabled:
            raise HTTPException(status_code=401, detail="帳號已停用")
        else:
            await db.execute(
                update(User).where(User.id == user.id).values(
                    display_name=ldap_info["display_name"],
                    email=ldap_info["email"],
                )
            )

    # ── 本機認證 ──
    else:
        result = await db.execute(
            select(User)
            .where(User.username == username, User.realm_id == realm.id, User.enabled == True)
            .options(selectinload(User.realm))
        )
        user = result.scalar_one_or_none()
        if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    # 取角色
    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    )
    roles = [r for (r,) in result.all()]

    # 更新最後登入時間
    await db.execute(
        update(User).where(User.id == user.id).values(last_login=datetime.now(timezone.utc))
    )

    # 建立 JWT
    access_token = create_access_token({"sub": str(user.id), "roles": roles})
    raw_refresh, refresh_hash = create_refresh_token()

    expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    db.add(Session(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires,
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(req.refresh_token)
    await db.execute(
        update(Session).where(Session.refresh_token_hash == token_hash).values(revoked=True)
    )
    await db.commit()
    return {"message": "已登出"}


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(req.refresh_token)
    result = await db.execute(
        select(Session).where(
            Session.refresh_token_hash == token_hash,
            Session.revoked == False,
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Refresh Token 無效或已過期")

    result = await db.execute(
        select(User).where(User.id == session.user_id, User.enabled == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="使用者不存在")

    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    )
    roles = [r for (r,) in result.all()]

    access_token = create_access_token({"sub": str(user.id), "roles": roles})
    return TokenResponse(
        access_token=access_token,
        refresh_token=req.refresh_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
async def get_me(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.id == user.id).options(selectinload(User.realm))
    )
    full_user = result.scalar_one()
    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    )
    roles = [r for (r,) in result.all()]
    return _user_to_out(full_user, roles)


@router.get("/api-keys", response_model=list[APITokenOut])
async def list_api_keys(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(APIToken).where(APIToken.user_id == user.id, APIToken.revoked == False)
        .order_by(APIToken.created_at.desc())
    )
    return result.scalars().all()


@router.post("/api-keys", response_model=APITokenCreated)
async def create_api_key(req: APITokenCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    raw_token, token_hash = generate_token("xcp")
    expires_at = None
    if req.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_days)

    api_token = APIToken(
        user_id=user.id,
        name=req.name,
        token_hash=token_hash,
        token_prefix=raw_token[:12],
        scopes=req.scopes,
        expires_at=expires_at,
    )
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)

    return APITokenCreated(
        id=api_token.id,
        name=api_token.name,
        token_prefix=api_token.token_prefix,
        scopes=api_token.scopes,
        created_at=api_token.created_at,
        last_used_at=api_token.last_used_at,
        expires_at=api_token.expires_at,
        revoked=api_token.revoked,
        token=raw_token,
    )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(APIToken).where(APIToken.id == key_id, APIToken.user_id == user.id)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    token.revoked = True
    await db.commit()
    return {"message": "API Key 已撤銷"}
