# xCloudPDF 雲端文件智能平台

> 云碩科技 CloudInfo Technology — 企業級文件處理解決方案

## 快速啟動

### 方式一：Docker Compose（推薦）

```bash
# 1. 複製環境設定
cp .env.example .env

# 2. 修改 .env 中的 SECRET_KEY（強制）

# 3. 啟動所有服務
docker compose up -d

# 4. 開啟瀏覽器
open http://localhost
```

預設帳號：`admin` / `admin1234`

---

### 方式二：本機開發

```bash
# 後端
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（另開終端機）
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 系統架構

```
┌─────────────┐    ┌──────────────────────────┐
│  瀏覽器      │───▶│  Nginx (API Gateway)      │
│  React SPA  │    │  Port 80                  │
└─────────────┘    └──────────┬───────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                                 ▼
┌─────────────────────┐           ┌─────────────────────┐
│  Backend (FastAPI)  │           │  Frontend (React)    │
│  Port 8000          │           │  Port 3000 (dev)     │
│                     │           │                      │
│  ● 認證 (JWT/LDAP) │           │  ● 工具箱 UI         │
│  ● 工具引擎 (30+)  │           │  ● 作業監控          │
│  ● 作業佇列        │           │  ● 管理後台          │
│  ● RBAC 權限       │           └─────────────────────┘
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │  SQLite DB  │  (生產環境可換 PostgreSQL)
    │  本地檔案   │  (生產環境可換 MinIO S3)
    └─────────────┘
```

---

## 功能清單

### 📄 PDF 工具
| 工具 | 說明 |
|------|------|
| PDF 合併 | 多個 PDF 合成一份 |
| PDF 分拆 | 依頁碼或每 N 頁分割 |
| PDF 壓縮 | 最佳化影像品質與字型 |
| PDF 加密 | AES-256 密碼保護 |
| PDF 解密 | 移除密碼 |
| PDF 浮水印 | 文字浮水印（透明度/角度/顏色）|
| PDF 旋轉 | 整頁旋轉方向 |
| PDF 蓋章 | 自訂文字印章 |
| N-up 排版 | 2-up / 4-up 合印 |
| PDF 比較 | 文字差異比對 |
| 擷取文字 | 純文字 / JSON 格式 |
| 擷取圖片 | ZIP 打包 |
| 中繼資料 | 查看/清除 metadata |
| 頁面管理 | 刪除/保留指定頁面 |
| 字數統計 | 逐頁字數與字元數 |
| 隱藏內容掃描 | 安全威脅檢測 |
| 擷取註解 | 批注/標記匯出 |
| 加入頁碼 | 自訂格式與位置 |

### 🔄 格式轉換
| 工具 | 說明 |
|------|------|
| PDF 轉圖片 | PNG/JPG，可設 DPI |
| 圖片轉 PDF | 多張圖片合成 PDF |
| Office 轉 PDF | Word/Excel/PPT → PDF |

### 🔒 資安防護
| 工具 | 說明 |
|------|------|
| 文件去識別化 | 遮蔽身分證/電話/Email |
| AES 加密壓縮 | AES-256 加密 ZIP |

### 🤖 AI 智能
| 工具 | 說明 |
|------|------|
| 文件翻譯 | 接入本地 LLM |

---

## API 文件

啟動後訪問：`http://localhost:8000/api/docs`

主要端點：
```
POST /api/v1/auth/login          登入
GET  /api/v1/tools               列出所有工具
POST /api/v1/tools/{id}/submit   提交作業（非同步）
POST /api/v1/tools/{id}/execute  執行工具（同步 < 20MB）
GET  /api/v1/jobs                作業列表
GET  /api/v1/jobs/{id}/download  下載結果
GET  /api/v1/admin/stats         系統統計（管理員）
```

---

## 技術棧

| 層次 | 技術 |
|------|------|
| 後端 | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 |
| 前端 | React 18, TypeScript, Vite, Tailwind CSS 3 |
| 資料庫 | SQLite（開發），PostgreSQL（生產） |
| 文件引擎 | PyMuPDF (fitz), LibreOffice |
| 容器化 | Docker, Docker Compose, Nginx |

---

## 相關文件

- [ARCHITECTURE.md](ARCHITECTURE.md) — 系統架構設計
- [docs/MIGRATION.md](docs/MIGRATION.md) — jt-doc-tools 遷移指南

---

© 2025 云碩科技 CloudInfo Technology
