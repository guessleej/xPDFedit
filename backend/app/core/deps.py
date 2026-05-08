from __future__ import annotations
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.user import User, APIToken, Role, UserRole
from ..core.security import decode_access_token, hash_token
from ..config import settings

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    if not settings.auth_enabled:
        result = await db.execute(select(User).where(User.username == "admin", User.is_superadmin == True))
        user = result.scalar_one_or_none()
        if user:
            return user
        raise HTTPException(status_code=500, detail="系統未初始化，請執行 init-db")

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="請提供認證 Token")

    token = credentials.credentials

    # 1. 嘗試 JWT access token
    payload = decode_access_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            result = await db.execute(select(User).where(User.id == int(user_id), User.enabled == True))
            user = result.scalar_one_or_none()
            if user:
                return user

    # 2. 嘗試 API Token
    token_hash = hash_token(token)
    result = await db.execute(
        select(APIToken).where(
            APIToken.token_hash == token_hash,
            APIToken.revoked == False,
        )
    )
    api_token = result.scalar_one_or_none()
    if api_token:
        result = await db.execute(select(User).where(User.id == api_token.user_id, User.enabled == True))
        user = result.scalar_one_or_none()
        if user:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 無效或已過期")


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: AsyncSession = Depends(get_db),
) -> User | None:
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_superadmin(user: CurrentUser) -> User:
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail="需要超級管理員權限")
    return user


def require_permission(permission: str):
    """Factory: 回傳檢查使用者是否具有指定權限的 FastAPI dependency。

    支援萬用字元：
    - "*" 符合所有權限
    - "tool:*" 符合所有 tool: 開頭的權限
    - "tool:execute" 精確符合
    """
    async def _inner(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> User:
        if user.is_superadmin:
            return user
        result = await db.execute(
            select(Role).join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        roles = result.scalars().all()
        ns = permission.split(":")[0]
        for role in roles:
            perms: list = role.permissions or []
            if "*" in perms or permission in perms or f"{ns}:*" in perms:
                return user
        raise HTTPException(status_code=403, detail=f"權限不足（需要 {permission}）")
    return _inner
