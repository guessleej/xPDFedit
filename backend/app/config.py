from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "xPDFedit"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "dev-secret-key-change-in-production-min-32-chars"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:80"]

    # Database
    database_url: str = "sqlite+aiosqlite:///./xpdfedit.db"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 480       # 8 hours
    jwt_refresh_expire_days: int = 7

    # Storage
    storage_backend: Literal["local", "minio"] = "local"
    storage_local_path: str = "./data/storage"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"

    # Auth
    auth_enabled: bool = True
    default_realm: str = "local"

    # LDAP (optional)
    ldap_url: str = ""
    ldap_bind_dn: str = ""
    ldap_bind_password: str = ""
    ldap_base_dn: str = ""
    ldap_user_filter: str = "(uid={username})"

    # LibreOffice
    libreoffice_path: str = "libreoffice"

    # Upload limits
    max_upload_size_mb: int = 200

    # Job retention
    job_retention_days: int = 30
    file_retention_days: int = 7

    # LLM (OpenAI-compatible, e.g. LiteLLM / Ollama)
    llm_base_url: str = ""
    llm_api_key: str = "sk-not-required"
    llm_model: str = "qwen2.5"
    llm_timeout: int = 120

    # AI 進階設定
    rag_model: str = "qwen3.6:35b"         # PDF 問答（推理強）
    summary_model: str = "gemma4:e4b"       # 摘要 / 關鍵字（快）
    embedding_model: str = "bge-m3:latest"  # 向量化


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
