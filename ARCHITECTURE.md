# xCloudPDF 雲端文件智能平台 — 系統架構設計

> **云碩科技 CloudInfo Technology**  
> 基於 [jt-doc-tools](https://github.com/jasoncheng7115/jt-doc-tools) 重新架構  
> 版本：1.0 | 日期：2026-05-07

---

## 一、系統定位

| 項目 | 說明 |
|------|------|
| 系統名稱 | xCloudPDF 雲端文件智能平台 |
| 對象 | 云碩科技內部及企業客戶 |
| 核心能力 | PDF/Office 文件處理、企業認證、稽核追蹤、AI 輔助 |
| 架構模式 | 分層設計 + 模組化服務 + RESTful API 閘道 + 資料層分離 |
| 部署方式 | Docker Compose（單機）/ Kubernetes（叢集） |

---

## 二、架構全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                        L0  用戶端層 (Client)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Web SPA  │  │ Mobile   │  │  API Clients │  │  ERP/ECM/DMS   │  │
│  │React+TS  │  │   PWA    │  │  CLI / SDK   │  │  Third-party   │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └───────┬────────┘  │
└───────┼─────────────┼───────────────┼──────────────────┼───────────┘
        │             │               │                  │
        ▼             ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     L1  邊緣層 (Edge)                                 │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐    │
│  │  CDN (靜態資源/預覽) │    │  WAF + Rate Limiter + TLS 終止   │    │
│  └─────────────────────┘    └──────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    L2  API 閘道層 (Gateway)                           │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                    Nginx Reverse Proxy                        │  │
│   │   路由分發 │ JWT 驗證 │ 限流 │ CORS │ 版本控制 │ 熔斷保護     │  │
│   └───────────────────────────┬──────────────────────────────────┘  │
│                               │                                     │
│   /api/v1/auth/*  /api/v1/docs/*  /api/v1/jobs/*  /api/v1/admin/*  │
└───────┬───────────────┬───────────────┬───────────────┬─────────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   L3  應用服務層 (Application Services)               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Auth &     │  │  Document    │  │  Job Queue   │              │
│  │  Identity    │  │  Processing  │  │   Service    │              │
│  │  Service     │  │   Service    │  │              │              │
│  │              │  │              │  │  Celery +    │              │
│  │ Local/LDAP/  │  │ 30+ Tools    │  │  Redis       │              │
│  │ AD/SSO       │  │ Engine       │  │              │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Audit &    │  │  Admin &     │  │  AI / LLM    │              │
│  │  Compliance  │  │  Config      │  │   Service    │              │
│  │   Service    │  │   Service    │  │              │              │
│  │              │  │              │  │ 翻譯/審閱/   │              │
│  │ 稽核/法規/   │  │ 使用者/角色/ │  │ 去識別化     │              │
│  │ syslog轉送   │  │ 系統設定     │  │              │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌──────────────┐                                                   │
│  │ Notification │                                                   │
│  │   Service    │                                                   │
│  │ Email/Webhook│                                                   │
│  └──────────────┘                                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   L4  領域核心層 (Domain Core)                        │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Document Engine │  │ Permission Engine│  │  Storage Engine  │  │
│  │                  │  │                  │  │                  │  │
│  │  PyMuPDF         │  │  RBAC Evaluator  │  │  S3 Abstraction  │  │
│  │  LibreOffice API │  │  Policy Enforcer │  │  Local / MinIO   │  │
│  │  Tool Registry   │  │  Resource ACL    │  │  Quota Manager   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
│  ┌──────────────────┐                                               │
│  │   Event Bus      │                                               │
│  │                  │                                               │
│  │  Redis Pub/Sub   │                                               │
│  │  Audit Capture   │                                               │
│  │  Async Triggers  │                                               │
│  └──────────────────┘                                               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      L5  資料層 (Data) — 分離設計                     │
│                                                                     │
│  ┌─────────────────────────┐   ┌────────────────────────────────┐  │
│  │  核心交易資料            │   │  影像 / 文件 物件儲存           │  │
│  │  PostgreSQL 16           │   │  MinIO (S3-compatible)         │  │
│  │                          │   │                                │  │
│  │  • users / realms        │   │  Bucket: uploads/              │  │
│  │  • groups / roles        │   │  Bucket: processed/            │  │
│  │  • permissions           │   │  Bucket: previews/             │  │
│  │  • sessions / api_keys   │   │  Bucket: templates/            │  │
│  │  • jobs (metadata)       │   │  Bucket: assets/               │  │
│  │  • settings / branding   │   │                                │  │
│  │  • tool_configs          │   │  生命週期自動清理政策           │  │
│  └─────────────────────────┘   └────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────┐   ┌────────────────────────────────┐  │
│  │  稽核 / 日誌資料         │   │  快取 / 訊息佇列               │  │
│  │  Elasticsearch 8         │   │  Redis 7 Cluster               │  │
│  │                          │   │                                │  │
│  │  Index: audit_events     │   │  • Session Cache (TTL)         │  │
│  │  Index: access_logs      │   │  • Rate Limit Counters         │  │
│  │  Index: security_events  │   │  • Job Queue (List)            │  │
│  │  Index: system_logs      │   │  • Pub/Sub Notifications       │  │
│  │                          │   │  • Distributed Locks           │  │
│  │  全文索引 + 視覺儀表板    │   │                                │  │
│  └─────────────────────────┘   └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、資料層分離設計（核心決策）

### 3.1 分離原則

| 資料類型 | 特性 | 儲存引擎 | 理由 |
|----------|------|----------|------|
| 核心交易資料 | ACID、關聯完整性、頻繁更新 | PostgreSQL | 強一致性、外鍵約束、事務支持 |
| 文件 / 影像物件 | 二進位大物件、生命週期管理 | MinIO (S3) | 水平擴展、CDN 整合、版本控制 |
| 稽核 / 日誌 | 僅寫入、時序、全文搜尋 | Elasticsearch | 毫秒級索引、法規長期保留、Kibana |
| 快取 / 佇列 | 揮發性、低延遲、高吞吐 | Redis Cluster | 記憶體速度、分散式結構 |

### 3.2 PostgreSQL 核心 Schema

```sql
-- 身份域 (Identity Domain)
CREATE SCHEMA identity;
CREATE TABLE identity.realms        (id, name, type, config_json, ...);
CREATE TABLE identity.users         (id, username, realm_id, password_hash, ...);
CREATE TABLE identity.groups        (id, name, realm_id, ...);
CREATE TABLE identity.user_groups   (user_id, group_id);
CREATE TABLE identity.roles         (id, name, builtin, description, ...);
CREATE TABLE identity.role_grants   (role_id, user_id, group_id, ...);
CREATE TABLE identity.permissions   (id, role_id, resource_type, action, ...);
CREATE TABLE identity.api_tokens    (id, user_id, token_hash, scopes, expires_at, ...);
CREATE TABLE identity.sessions      (id, user_id, token_hash, ip, ua, created_at, ...);

-- 文件作業域 (Job Domain) — 只存 Metadata
CREATE SCHEMA job;
CREATE TABLE job.jobs (
    id UUID PRIMARY KEY,
    user_id INT REFERENCES identity.users(id),
    tool_id VARCHAR(64),
    status VARCHAR(16),   -- queued / running / done / failed / cancelled
    priority SMALLINT DEFAULT 5,
    input_object_key TEXT,    -- MinIO key
    output_object_key TEXT,   -- MinIO key (nullable until done)
    params_json JSONB,
    error_message TEXT,
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ    -- auto-cleanup
);

-- 系統設定域 (Config Domain)
CREATE SCHEMA config;
CREATE TABLE config.settings         (key, value_json, updated_by, updated_at);
CREATE TABLE config.branding         (key, value, ...);
CREATE TABLE config.tool_configs     (tool_id, config_json, enabled, ...);
CREATE TABLE config.llm_settings     (id, provider, endpoint, model, ...);
CREATE TABLE config.retention_policy (resource_type, days, ...);
CREATE TABLE config.font_catalog     (id, filename, display_name, ...);
CREATE TABLE config.templates        (id, name, tool_id, content, ...);
```

### 3.3 MinIO Bucket 策略

```
xcloudpdf-uploads/          # 上傳暫存（TTL: 24hr）
xcloudpdf-processed/        # 處理結果（TTL: 依 retention policy）
xcloudpdf-previews/         # 預覽縮圖（TTL: 72hr，可 CDN 快取）
xcloudpdf-templates/        # 文件範本（永久）
xcloudpdf-assets/           # 印章/Logo/字型（永久）
xcloudpdf-audit-export/     # 稽核報表匯出（TTL: 30天）
```

---

## 四、API 閘道設計

### 4.1 路由表

```
Base URL: https://docs.cloudinfo.com.tw/api/v1

─── 認證 Auth ──────────────────────────────────────────────
POST   /auth/login                  # 本機登入
POST   /auth/login/ldap             # LDAP/AD 登入
POST   /auth/logout
POST   /auth/token/refresh
GET    /auth/me                     # 當前使用者資訊
POST   /auth/api-keys               # 建立 API Key
GET    /auth/api-keys               # 列出 API Keys
DELETE /auth/api-keys/{key_id}      # 撤銷 API Key

─── 文件 Documents ─────────────────────────────────────────
POST   /documents/upload            # 上傳（回傳 document_id）
GET    /documents/{id}              # 文件 metadata
GET    /documents/{id}/download     # 下載原始檔
GET    /documents/{id}/preview      # 預覽 URL（簽名 S3 連結）
DELETE /documents/{id}              # 刪除

─── 工具 Tools ─────────────────────────────────────────────
GET    /tools                       # 列出所有可用工具
GET    /tools/{tool_id}             # 工具 metadata + 參數 schema
POST   /tools/{tool_id}/execute     # 同步執行（< 5MB，< 10s）
POST   /tools/{tool_id}/submit      # 非同步提交（回傳 job_id）

─── 作業 Jobs ──────────────────────────────────────────────
GET    /jobs                        # 列出使用者作業
GET    /jobs/{job_id}               # 作業狀態 + 進度
GET    /jobs/{job_id}/result        # 下載結果（簽名 URL）
DELETE /jobs/{job_id}               # 取消 / 刪除

─── AI 服務 AI ─────────────────────────────────────────────
POST   /ai/translate                # 文件翻譯
POST   /ai/review                   # 文件審閱
POST   /ai/deidentify               # 去識別化
GET    /ai/settings                 # LLM 設定（admin only）

─── 稽核 Audit ─────────────────────────────────────────────
GET    /audit/events                # 稽核事件列表（filter, page）
POST   /audit/export                # 匯出稽核報表（非同步）
GET    /audit/forward/settings      # 日誌轉送設定（admin）

─── 管理 Admin ─────────────────────────────────────────────
CRUD   /admin/users
CRUD   /admin/groups
CRUD   /admin/roles
CRUD   /admin/realms
GET    /admin/stats                 # 系統統計
GET    /admin/system/health         # 健康檢查
PUT    /admin/settings/{key}        # 系統設定
CRUD   /admin/templates
CRUD   /admin/fonts
```

### 4.2 JWT Token 結構

```json
{
  "sub": "user:42",
  "realm": "cloudinfo.com.tw",
  "roles": ["operator", "reviewer"],
  "scopes": ["tools:read", "tools:execute", "jobs:read"],
  "iat": 1746576000,
  "exp": 1746662400,
  "jti": "uuid-v4"
}
```

### 4.3 統一回應格式

```json
// 成功
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "total": 100, "request_id": "uuid" }
}

// 錯誤
{
  "success": false,
  "error": {
    "code": "TOOL_EXECUTION_FAILED",
    "message": "PDF 加密失敗：密碼不符規範",
    "detail": { ... }
  },
  "meta": { "request_id": "uuid" }
}
```

---

## 五、模組化服務設計

### 5.1 Auth & Identity Service

```
services/auth/
├── app/
│   ├── providers/
│   │   ├── base.py           # AuthProvider ABC
│   │   ├── local.py          # 本機帳號（bcrypt）
│   │   ├── ldap.py           # LDAP/AD（ldap3）
│   │   └── saml.py           # SAML 2.0（未來）
│   ├── models/
│   │   ├── user.py
│   │   ├── session.py
│   │   └── api_token.py
│   ├── routers/
│   │   ├── auth.py           # /auth/*
│   │   └── api_keys.py       # /auth/api-keys/*
│   ├── jwt.py                # Token 簽發/驗證
│   ├── mfa.py                # TOTP（未來）
│   └── main.py
└── Dockerfile
```

**關鍵設計：多 Realm 支援**
```python
# 同名帳號可屬不同 Realm（保留 jt-doc-tools 設計）
# user@cloudinfo.com.tw   → LDAP Realm
# user@local              → Local Realm
# API 閘道統一驗證後傳遞 X-User-ID / X-User-Roles Header
```

### 5.2 Document Processing Service

```
services/document/
├── app/
│   ├── engine/
│   │   ├── pdf_engine.py     # PyMuPDF wrapper
│   │   ├── office_engine.py  # LibreOffice UNO bridge
│   │   ├── image_engine.py   # Pillow + ImageMagick
│   │   └── tool_registry.py  # 動態工具發現（保留原設計）
│   ├── tools/                # 從 jt-doc-tools 遷移的 30+ 工具
│   │   ├── base.py           # ToolBase ABC
│   │   ├── pdf_compress/
│   │   ├── pdf_merge/
│   │   ├── pdf_split/
│   │   ├── pdf_encrypt/
│   │   ├── pdf_decrypt/
│   │   ├── pdf_watermark/
│   │   ├── pdf_stamp/
│   │   ├── office_to_pdf/
│   │   ├── image_to_pdf/
│   │   ├── pdf_extract_text/
│   │   ├── pdf_extract_images/
│   │   ├── doc_deident/
│   │   └── ... (全部 30+ 工具)
│   ├── storage/
│   │   └── s3_client.py      # MinIO/S3 存取
│   ├── routers/
│   │   ├── documents.py
│   │   └── tools.py
│   └── main.py
└── Dockerfile
```

**工具執行流程：**
```
Client → POST /tools/{id}/submit
         → 驗證權限（Permission Engine）
         → 上傳輸入至 MinIO (uploads/)
         → 建立 Job record (PostgreSQL)
         → 推入 Celery Queue (Redis)
         → 回傳 job_id

Worker  → 取出 Job
         → 下載輸入 from MinIO
         → 執行 Tool (document engine)
         → 上傳輸出至 MinIO (processed/)
         → 更新 Job status (PostgreSQL)
         → 發送 Event (Redis Pub/Sub)
         → Notification Service 通知使用者
```

### 5.3 Job Queue Service

```
services/job/
├── app/
│   ├── worker.py             # Celery Worker
│   ├── tasks/
│   │   ├── document_task.py  # 文件處理任務
│   │   ├── ai_task.py        # AI 處理任務
│   │   └── export_task.py    # 報表匯出任務
│   ├── routers/
│   │   └── jobs.py           # /jobs/*
│   └── main.py
```

**佇列優先級：**
```python
CELERY_TASK_QUEUES = {
    'high':    {'priority': 10},  # 互動式同步執行
    'normal':  {'priority': 5},   # 一般非同步作業
    'batch':   {'priority': 1},   # 批次/背景作業
    'ai':      {'priority': 3},   # AI 處理（GPU 限制）
}
```

### 5.4 Audit & Compliance Service

```
services/audit/
├── app/
│   ├── capture.py            # 事件擷取（from Event Bus）
│   ├── forwarder/
│   │   ├── syslog.py         # RFC 5424 Syslog
│   │   ├── cef.py            # ArcSight CEF
│   │   └── gelf.py           # Graylog GELF
│   ├── retention.py          # 資料保留政策執行
│   ├── routers/
│   │   └── audit.py          # /audit/*
│   └── main.py
```

**稽核事件 Schema（Elasticsearch）：**
```json
{
  "@timestamp": "2026-05-07T08:30:00Z",
  "event_type": "tool.execute",
  "severity": "INFO",
  "actor": {
    "user_id": 42,
    "username": "jeff@cloudinfo.com.tw",
    "realm": "cloudinfo.com.tw",
    "ip": "192.168.1.100",
    "ua": "Mozilla/5.0..."
  },
  "resource": {
    "type": "document",
    "id": "uuid",
    "name": "合約書.pdf"
  },
  "action": {
    "tool": "pdf_encrypt",
    "params": {"algorithm": "AES256"},
    "result": "success",
    "duration_ms": 342
  },
  "job_id": "uuid"
}
```

---

## 六、目錄結構

```
xcloudpdf/
├── gateway/                        # API 閘道
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── conf.d/
│   └── middleware/                 # JWT 驗證 middleware
│
├── services/                       # 應用服務層
│   ├── auth/                       # 認證服務
│   ├── document/                   # 文件處理服務
│   ├── job/                        # 作業佇列服務
│   ├── audit/                      # 稽核合規服務
│   ├── admin/                      # 管理服務
│   ├── ai/                         # AI/LLM 服務
│   └── notify/                     # 通知服務
│
├── core/                           # 領域核心層（共享程式庫）
│   ├── document_engine/            # PDF/Office 引擎
│   ├── permission_engine/          # RBAC 評估引擎
│   ├── storage_engine/             # 儲存抽象層
│   └── event_bus/                  # 事件匯流排
│
├── frontend/                       # React SPA
│   ├── src/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── documents/
│   │   │   ├── tools/
│   │   │   ├── jobs/
│   │   │   ├── audit/
│   │   │   └── admin/
│   │   ├── components/ui/          # shadcn/ui
│   │   ├── lib/api/                # API 客戶端
│   │   └── stores/                 # Zustand 狀態管理
│   └── vite.config.ts
│
├── migrations/                     # Alembic DB 遷移
│   ├── env.py
│   └── versions/
│
├── infra/                          # 基礎設施
│   ├── docker-compose.yml          # 開發環境
│   ├── docker-compose.prod.yml     # 生產環境
│   ├── k8s/                        # Kubernetes manifests
│   │   ├── deployments/
│   │   ├── services/
│   │   └── ingress/
│   └── monitoring/
│       ├── prometheus/
│       ├── grafana/
│       └── elasticsearch/
│
└── docs/
    ├── ARCHITECTURE.md             # 本文件
    ├── API.md                      # API 規格
    ├── DEPLOYMENT.md               # 部署指南
    └── MIGRATION.md                # jt-doc-tools 遷移指南
```

---

## 七、技術棧選型

### 後端

| 層次 | 技術 | 理由 |
|------|------|------|
| Web Framework | FastAPI 0.115 + Python 3.12 | 保留 jt-doc-tools 投資；OpenAPI 自動生成 |
| ORM | SQLAlchemy 2.0 + asyncpg | 非同步 PostgreSQL；原 SQLite 層可無縫替換 |
| DB Migration | Alembic | 版本化 Schema 管理 |
| Task Queue | Celery 5 + Redis | 取代原 job_manager；支援優先級佇列 |
| Validation | Pydantic v2 | FastAPI 原生整合 |
| Auth | python-jose (JWT) + passlib | 標準 JWT；bcrypt 密碼 |
| LDAP | ldap3 | 保留原 LDAP 邏輯 |
| Storage | boto3 (S3/MinIO) | 物件儲存統一介面 |
| Search | elasticsearch-py 8 | 稽核日誌索引 |
| PDF | PyMuPDF (fitz) | 保留原引擎 |
| Office | LibreOffice UNO / OxOffice | 保留原轉換邏輯 |

### 前端

| 項目 | 技術 |
|------|------|
| Framework | React 18 + TypeScript 5 |
| Build | Vite 5 |
| UI Library | shadcn/ui + Tailwind CSS 3 |
| State | Zustand + React Query (TanStack) |
| Router | React Router v6 |
| i18n | react-i18next（繁中 / English）|
| Charts | Recharts（Dashboard）|

### 基礎設施

| 項目 | 技術 |
|------|------|
| 容器 | Docker + Docker Compose / Kubernetes |
| Proxy | Nginx |
| DB | PostgreSQL 16 |
| Cache/Queue | Redis 7 Cluster |
| Object Storage | MinIO (S3-compatible) |
| Search/Log | Elasticsearch 8 / OpenSearch 2 |
| Monitoring | Prometheus + Grafana |
| Log Aggregation | Loki + Promtail |
| Error Tracking | Sentry |
| CI/CD | GitHub Actions |

---

## 八、部署拓撲

### 開發環境（Docker Compose）

```yaml
# docker-compose.yml
services:
  # 基礎設施
  postgres:    image: postgres:16-alpine
  redis:       image: redis:7-alpine
  minio:       image: minio/minio
  elasticsearch: image: elasticsearch:8.13.0

  # 服務層
  gateway:     build: ./gateway
  auth:        build: ./services/auth
  document:    build: ./services/document
  job-api:     build: ./services/job
  audit:       build: ./services/audit
  admin:       build: ./services/admin
  ai:          build: ./services/ai

  # Worker（Celery）
  worker-doc:  build: ./services/document  # celery worker
  worker-ai:   build: ./services/ai        # celery worker

  # 前端
  frontend:    build: ./frontend
```

### 生產環境（Kubernetes 概念）

```
Internet
   │
   ▼
LoadBalancer (AWS ALB / 雲碩 F5)
   │
   ▼
Nginx Ingress Controller
   │
   ├──▶ Auth Service (Deployment × 2)
   ├──▶ Document Service (Deployment × 3)
   ├──▶ Job API (Deployment × 2)
   ├──▶ Audit Service (Deployment × 2)
   └──▶ Admin Service (Deployment × 1)

Document Worker (Deployment × 5, HPA)
AI Worker      (Deployment × 2, GPU Node Pool)

StatefulSets:
   PostgreSQL   (Primary + Read Replica)
   Redis        (Cluster Mode × 6 nodes)
   MinIO        (Distributed Mode × 4 nodes)
   Elasticsearch (Master × 3 + Data × 3)
```

---

## 九、jt-doc-tools 遷移路徑

### Phase 1（M1-M2）：基礎設施建立
- [ ] PostgreSQL + Redis + MinIO 環境就緒
- [ ] SQLite → PostgreSQL Schema 遷移（使用原 db.py migration 機制）
- [ ] 檔案系統 → MinIO 遷移腳本
- [ ] Nginx API 閘道設定

### Phase 2（M3-M4）：服務拆分
- [ ] Auth Service 提取（auth.py, auth_db.py, auth_ldap.py）
- [ ] Admin Service 提取（admin/router.py）
- [ ] 引入 Celery 取代 job_manager.py
- [ ] 稽核事件接入 Elasticsearch

### Phase 3（M5-M6）：前端重建
- [ ] React SPA 建立（取代 Jinja2 模板）
- [ ] 工具 UI 組件化
- [ ] Dashboard / 報表頁面
- [ ] i18n 多語系

### Phase 4（M7-M8）：AI 與企業功能
- [ ] AI/LLM Service 整合
- [ ] SAML 2.0 SSO
- [ ] Kubernetes 生產部署
- [ ] 監控告警設定

---

## 十、非功能性需求

| 項目 | 目標 |
|------|------|
| API 回應時間 | P50 < 200ms（同步），P95 < 500ms |
| 文件處理吞吐 | 100 個並發作業（可水平擴展） |
| 可用性 | 99.5%（單機）/ 99.9%（K8s）|
| 稽核保留 | 最少 1 年（可設定）|
| 檔案保留 | 最少 30 天（可設定，含 S3 Lifecycle）|
| 認證 | JWT 有效期 8hr，Refresh Token 7 天 |
| 限流 | 100 req/min/user，1000 req/min/IP |
| 加密 | TLS 1.2+，資料庫欄位加密（API Key Hash）|

---

*架構設計 by Claude / 云碩科技 CloudInfo Technology*
