"""認證提供者抽象基底 — 保留 jt-doc-tools 多 Realm 設計"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AuthResult:
    user_id: int
    username: str
    realm: str
    display_name: str
    email: str | None
    roles: list[str]
    groups: list[str]
    extra: dict


class AuthProvider(ABC):
    """所有認證提供者實作此 ABC"""

    @property
    @abstractmethod
    def realm_type(self) -> str:
        """'local' | 'ldap' | 'ad' | 'saml'"""

    @abstractmethod
    async def authenticate(self, username: str, password: str, realm: str) -> AuthResult | None:
        """驗證帳密，失敗回傳 None"""

    @abstractmethod
    async def get_user(self, user_id: int) -> AuthResult | None:
        """依 user_id 取得使用者資訊"""
