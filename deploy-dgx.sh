#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  xCloudPDF — DGX Spark 一鍵部署腳本
#  用法：./deploy-dgx.sh [DGX_HOST] [SSH_USER]
#  範例：./deploy-dgx.sh 192.168.1.100 ubuntu
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── 參數 ──────────────────────────────────────────────────────────────────
DGX_HOST="${1:-${DGX_HOST:-}}"
SSH_USER="${2:-ubuntu}"
REMOTE_DIR="${REMOTE_DIR:-/opt/xcloudpdf/app}"
DATA_DIR="${DATA_DIR:-/opt/xcloudpdf}"
COMPOSE_FILE="docker-compose.dgx.yml"

# ── 顏色輸出 ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── 前置檢查 ──────────────────────────────────────────────────────────────
[[ -z "${DGX_HOST}" ]] && error "請提供 DGX_HOST：./deploy-dgx.sh <host> [user]"
[[ ! -f ".env" ]] && error ".env 不存在，請先：cp .env.dgx.example .env 並填入設定"
[[ ! -f "${COMPOSE_FILE}" ]] && error "${COMPOSE_FILE} 不存在"

SSH="ssh -o StrictHostKeyChecking=no ${SSH_USER}@${DGX_HOST}"
SCP="scp -o StrictHostKeyChecking=no"
RSYNC="rsync -avz --progress --exclude='.git' --exclude='node_modules' \
       --exclude='__pycache__' --exclude='.venv' --exclude='*.pyc' \
       --exclude='frontend/.next' --exclude='frontend/dist'"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        xCloudPDF → DGX Spark 部署                   ║"
echo "║  目標：${SSH_USER}@${DGX_HOST}:${REMOTE_DIR}  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 步驟 1：測試 SSH 連線 ─────────────────────────────────────────────────
info "步驟 1/6：測試 SSH 連線..."
$SSH "echo 'SSH OK'" || error "無法連線到 ${DGX_HOST}，請確認 SSH 金鑰設定"
success "SSH 連線正常"

# ── 步驟 2：建立遠端目錄 ──────────────────────────────────────────────────
info "步驟 2/6：建立遠端目錄結構..."
$SSH "sudo mkdir -p \
    ${REMOTE_DIR} \
    ${DATA_DIR}/postgres \
    ${DATA_DIR}/redis \
    ${DATA_DIR}/app-data/storage/uploads \
    ${DATA_DIR}/app-data/storage/output \
    ${DATA_DIR}/backups \
    && sudo chown -R ${SSH_USER}:${SSH_USER} ${DATA_DIR} \
    && sudo chown -R ${SSH_USER}:${SSH_USER} ${REMOTE_DIR}"
success "目錄建立完成"

# ── 步驟 3：同步程式碼 ────────────────────────────────────────────────────
info "步驟 3/6：同步程式碼到 DGX..."
$RSYNC ./ "${SSH_USER}@${DGX_HOST}:${REMOTE_DIR}/"
success "程式碼同步完成"

# ── 步驟 4：上傳 .env ─────────────────────────────────────────────────────
info "步驟 4/6：上傳 .env 設定..."
$SCP .env "${SSH_USER}@${DGX_HOST}:${REMOTE_DIR}/.env"
success ".env 上傳完成"

# ── 步驟 5：建置 Docker 映像 ──────────────────────────────────────────────
info "步驟 5/6：在 DGX 上建置 Docker 映像（ARM64）..."
$SSH "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} build --no-cache"
success "Docker 映像建置完成"

# ── 步驟 6：啟動服務 ──────────────────────────────────────────────────────
info "步驟 6/6：啟動服務..."
$SSH "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} up -d"

# 等候健康檢查
info "等候服務就緒（最多 120 秒）..."
for i in $(seq 1 24); do
    STATUS=$($SSH "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} ps --format json 2>/dev/null | grep -c '\"Health\":\"healthy\"' || echo 0" 2>/dev/null || echo 0)
    if [[ "${STATUS}" -ge 3 ]]; then
        success "服務已就緒"
        break
    fi
    echo -n "."
    sleep 5
done

echo ""
echo "════════════════════════════════════════════════════════"
success "部署完成！"
echo ""
echo "  API：    http://${DGX_HOST}/api/docs"
echo "  前端：   http://${DGX_HOST}"
echo "  預設帳號：admin / admin1234（請立即修改密碼）"
echo ""
echo "查看服務狀態："
echo "  $SSH \"cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} ps\""
echo "查看日誌："
echo "  $SSH \"cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} logs -f backend\""
echo "════════════════════════════════════════════════════════"
