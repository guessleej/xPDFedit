#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  xCloudPDF — 備份腳本
#  執行：docker compose -f docker-compose.dgx.yml --profile backup run --rm backup
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/${TIMESTAMP}"
PGHOST="${PGHOST:-postgres}"
PGPORT="${PGPORT:-5432}"
PGUSER="${POSTGRES_USER:-xcloud}"
PGDB="${POSTGRES_DB:-xcloudpdf}"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"
echo "[$(date -Iseconds)] 開始備份 → ${BACKUP_DIR}"

# ── 1. PostgreSQL dump ────────────────────────────────────────────────────
echo "[$(date -Iseconds)] 備份 PostgreSQL..."
pg_dump \
  -h "${PGHOST}" \
  -p "${PGPORT}" \
  -U "${PGUSER}" \
  -d "${PGDB}" \
  --format=custom \
  --compress=9 \
  --no-password \
  -f "${BACKUP_DIR}/postgres_${PGDB}_${TIMESTAMP}.dump"

echo "[$(date -Iseconds)] PostgreSQL 備份完成：$(du -sh "${BACKUP_DIR}/postgres_${PGDB}_${TIMESTAMP}.dump" | cut -f1)"

# ── 2. 清理舊備份 ─────────────────────────────────────────────────────────
echo "[$(date -Iseconds)] 清理超過 ${RETAIN_DAYS} 天的舊備份..."
find /backups -maxdepth 1 -type d -mtime "+${RETAIN_DAYS}" -exec rm -rf {} + 2>/dev/null || true

# ── 3. 統計 ───────────────────────────────────────────────────────────────
TOTAL=$(du -sh /backups 2>/dev/null | cut -f1)
echo "[$(date -Iseconds)] 備份完成。/backups 總佔用：${TOTAL}"
echo "[$(date -Iseconds)] 備份項目："
ls -lh "${BACKUP_DIR}/"
