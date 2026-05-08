"""
RBAC 權限評估引擎

角色層次（由高至低）：
  superadmin > admin > manager > operator > viewer > guest
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class RoleLevel(IntEnum):
    GUEST      = 0
    VIEWER     = 10
    OPERATOR   = 20
    MANAGER    = 30
    ADMIN      = 40
    SUPERADMIN = 50


@dataclass(frozen=True)
class Permission:
    resource: str   # "tool", "document", "user", "audit", "settings"
    action: str     # "read", "execute", "create", "update", "delete", "export"


# 預設角色權限矩陣（保留 jt-doc-tools RBAC 邏輯）
DEFAULT_ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "viewer": {
        Permission("tool", "read"),
        Permission("document", "read"),
        Permission("job", "read"),
    },
    "operator": {
        Permission("tool", "read"),
        Permission("tool", "execute"),
        Permission("document", "read"),
        Permission("document", "create"),
        Permission("document", "delete"),
        Permission("job", "read"),
        Permission("job", "create"),
        Permission("job", "delete"),
    },
    "manager": {
        Permission("tool", "read"),
        Permission("tool", "execute"),
        Permission("document", "read"),
        Permission("document", "create"),
        Permission("document", "delete"),
        Permission("job", "read"),
        Permission("job", "create"),
        Permission("job", "delete"),
        Permission("audit", "read"),
        Permission("audit", "export"),
    },
    "admin": {
        Permission("tool", "read"),
        Permission("tool", "execute"),
        Permission("tool", "update"),
        Permission("document", "read"),
        Permission("document", "create"),
        Permission("document", "delete"),
        Permission("job", "read"),
        Permission("job", "create"),
        Permission("job", "delete"),
        Permission("audit", "read"),
        Permission("audit", "export"),
        Permission("user", "read"),
        Permission("user", "create"),
        Permission("user", "update"),
        Permission("user", "delete"),
        Permission("settings", "read"),
        Permission("settings", "update"),
    },
}


def check_permission(user_roles: list[str], resource: str, action: str) -> bool:
    """評估使用者是否有指定權限"""
    required = Permission(resource, action)
    for role in user_roles:
        if required in DEFAULT_ROLE_PERMISSIONS.get(role, set()):
            return True
    return False


def require_permission(resource: str, action: str):
    """FastAPI Dependency：驗證 JWT 內 roles 是否有權限"""
    from fastapi import Depends, HTTPException, Header

    def dependency(x_user_roles: str = Header(...)):
        roles = x_user_roles.split(",")
        if not check_permission(roles, resource, action):
            raise HTTPException(403, f"需要 {resource}:{action} 權限")

    return Depends(dependency)
