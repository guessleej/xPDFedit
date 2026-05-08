# ════════════════════════════════════════════════════════════════════════════
#  xCloudPDF — Makefile
#  本機開發：make up
#  DGX 部署：make deploy DGX_HOST=192.168.1.100
# ════════════════════════════════════════════════════════════════════════════

SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE        := docker compose
COMPOSE_DGX    := docker compose -f docker-compose.dgx.yml
DGX_HOST       ?=
DGX_USER       ?= ubuntu
VERSION        ?= $(shell git describe --tags --always 2>/dev/null || echo "dev")

# ── 顏色 ──────────────────────────────────────────────────────────────────
CYAN  := \033[0;36m
RESET := \033[0m

.PHONY: help
help: ## 顯示此說明
	@echo ""
	@echo "  xCloudPDF 操作指令"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ════════════════════════════════════════════════════════════════════════════
#  本機開發
# ════════════════════════════════════════════════════════════════════════════

.PHONY: dev
dev: ## 啟動本機開發（SQLite + 單 worker）
	@[[ -f .env ]] || cp .env.example .env
	$(COMPOSE) up -d
	@echo "前端：http://localhost | API 文件：http://localhost:8000/api/docs"

.PHONY: up
up: dev ## 同 dev

.PHONY: down
down: ## 停止並移除容器（保留 Volume）
	$(COMPOSE) down

.PHONY: restart
restart: ## 重啟所有服務
	$(COMPOSE) restart

.PHONY: logs
logs: ## 追蹤所有服務日誌
	$(COMPOSE) logs -f

.PHONY: logs-backend
logs-backend: ## 追蹤後端日誌
	$(COMPOSE) logs -f backend

.PHONY: logs-frontend
logs-frontend: ## 追蹤前端日誌
	$(COMPOSE) logs -f frontend

.PHONY: ps
ps: ## 列出容器狀態
	$(COMPOSE) ps

.PHONY: shell-backend
shell-backend: ## 進入後端容器 Shell
	$(COMPOSE) exec backend /bin/bash

.PHONY: shell-db
shell-db: ## 進入 PostgreSQL psql
	$(COMPOSE) exec postgres psql -U xcloud -d xcloudpdf

# ════════════════════════════════════════════════════════════════════════════
#  DGX Spark 生產
# ════════════════════════════════════════════════════════════════════════════

.PHONY: dgx-build
dgx-build: ## 在本機建置 DGX ARM64 映像（需要 buildx）
	$(COMPOSE_DGX) build --no-cache

.PHONY: dgx-up
dgx-up: ## 在本機啟動 DGX 設定
	@[[ -f .env ]] || { echo "請先建立 .env（cp .env.dgx.example .env）"; exit 1; }
	$(COMPOSE_DGX) up -d

.PHONY: dgx-down
dgx-down: ## 停止 DGX 服務
	$(COMPOSE_DGX) down

.PHONY: dgx-logs
dgx-logs: ## 追蹤 DGX 服務日誌
	$(COMPOSE_DGX) logs -f

.PHONY: dgx-ps
dgx-ps: ## DGX 容器狀態
	$(COMPOSE_DGX) ps

.PHONY: dgx-restart-backend
dgx-restart-backend: ## 滾動重啟後端（零停機）
	$(COMPOSE_DGX) restart backend

.PHONY: deploy
deploy: ## 部署到 DGX Spark（需要 DGX_HOST）
	@[[ -n "$(DGX_HOST)" ]] || { echo "用法：make deploy DGX_HOST=<ip>"; exit 1; }
	@chmod +x deploy-dgx.sh
	VERSION=$(VERSION) DGX_HOST=$(DGX_HOST) ./deploy-dgx.sh $(DGX_HOST) $(DGX_USER)

# ════════════════════════════════════════════════════════════════════════════
#  備份 / 還原
# ════════════════════════════════════════════════════════════════════════════

.PHONY: backup
backup: ## 執行 PostgreSQL 備份
	$(COMPOSE_DGX) --profile backup run --rm backup

.PHONY: backup-list
backup-list: ## 列出現有備份
	@ls -lh backups/ 2>/dev/null || echo "尚無備份"

# ════════════════════════════════════════════════════════════════════════════
#  資料庫遷移
# ════════════════════════════════════════════════════════════════════════════

.PHONY: migrate
migrate: ## 執行 Alembic 資料庫遷移
	$(COMPOSE) exec backend alembic upgrade head

.PHONY: migrate-dgx
migrate-dgx: ## 在 DGX 上執行資料庫遷移
	$(COMPOSE_DGX) exec backend alembic upgrade head

# ════════════════════════════════════════════════════════════════════════════
#  清理
# ════════════════════════════════════════════════════════════════════════════

.PHONY: clean
clean: ## 停止並移除容器 + Volume（危險！資料會遺失）
	@echo "警告：這將刪除所有 Docker Volume 中的資料！"
	@read -p "確認繼續？(yes/N): " CONFIRM && [[ "$$CONFIRM" == "yes" ]] || exit 1
	$(COMPOSE) down -v
	docker image rm xcloudpdf-backend xcloudpdf-frontend 2>/dev/null || true

.PHONY: prune
prune: ## 清理懸空 Docker 資源
	docker system prune -f
