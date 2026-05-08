# jt-doc-tools → xCloudPDF 遷移指南

## 模組對應表

| jt-doc-tools 原始模組 | xCloudPDF 目標服務 | 主要改動 |
|----------------------|-------------------|----------|
| `app/core/auth.py` | `services/auth/app/providers/` | 拆分 Local/LDAP/AD Provider |
| `app/core/auth_db.py` | `services/auth/app/models/` | SQLite → PostgreSQL (SQLAlchemy) |
| `app/core/auth_ldap.py` | `services/auth/app/providers/ldap.py` | 邏輯保留，asyncio 化 |
| `app/core/db.py` | `migrations/` | SQLite WAL → Alembic + PostgreSQL |
| `app/core/job_manager.py` | `services/job/app/worker.py` | threading → Celery + Redis |
| `app/core/file_storage.py` | `core/storage_engine/` | Local FS → MinIO S3 |
| `app/core/audit_db.py` | `services/audit/app/` | SQLite → Elasticsearch |
| `app/core/audit_forward.py` | `services/audit/app/forwarder/` | 邏輯保留 |
| `app/core/roles.py` | `core/permission_engine/` | 邏輯保留，API 化 |
| `app/core/permissions.py` | `core/permission_engine/` | 邏輯保留，Dependency 注入 |
| `app/core/sessions.py` | `services/auth/app/` | SQLite session → JWT + Redis |
| `app/core/api_tokens.py` | `services/auth/app/routers/api_keys.py` | 邏輯保留 |
| `app/core/pdf_utils.py` | `core/document_engine/` | 保留，共享 |
| `app/core/office_convert.py` | `core/document_engine/` | 保留，共享 |
| `app/tools/*/` | `services/document/app/tools/*/` | ToolBase ABC 改版 |
| `app/admin/` | `services/admin/app/` | Jinja2 → API only |
| `app/web/` | `frontend/src/` | Jinja2 → React SPA |

## 資料遷移步驟

### Step 1：匯出 SQLite 資料
```bash
# 使用現有 CLI 匯出
cd /var/lib/jt-doc-tools
python -m app.cli export-all --output ./export/
```

### Step 2：建立 PostgreSQL Schema
```bash
cd xcloudpdf
alembic upgrade head
```

### Step 3：匯入核心交易資料
```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite /var/lib/jt-doc-tools/data/auth.db \
  --postgres $POSTGRES_URL
```

### Step 4：遷移檔案到 MinIO
```bash
python scripts/migrate_files_to_minio.py \
  --source /var/lib/jt-doc-tools/data/uploads/ \
  --bucket xcloudpdf-processed
```

### Step 5：匯入稽核日誌到 Elasticsearch
```bash
python scripts/migrate_audit_to_es.py \
  --sqlite /var/lib/jt-doc-tools/data/audit.db \
  --es $ELASTICSEARCH_URL
```

## 設定對應

| jt-doc-tools 設定 | xCloudPDF 環境變數 |
|-------------------|-------------------|
| `data_dir` | `STORAGE_BACKEND=local` + `LOCAL_STORAGE_PATH` |
| `auth.mode` | `AUTH_MODE=local\|ldap\|ad` |
| `ldap.*` | `LDAP_URL`, `LDAP_BIND_DN`, `LDAP_BASE_DN` |
| `llm.*` | `LLM_PROVIDER`, `LLM_ENDPOINT`, `LLM_MODEL` |
| `log_forward.*` | Audit Service 設定 UI |

## 相容性說明

- **API Token** 格式相容，舊 Token 可繼續使用（需重新 Hash 儲存至 PostgreSQL）
- **角色名稱** 完全相容（viewer/operator/manager/admin/superadmin）
- **LDAP/AD** 設定格式相容，`username@realm` 格式保留
- **工具 ID** 格式統一為 kebab-case（原 `pdf-merge` → 不變）
