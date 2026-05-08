-- ════════════════════════════════════════════════════════════════════════════
--  xCloudPDF — PostgreSQL 初始化腳本
--  由 docker-entrypoint-initdb.d 在首次建立資料庫時自動執行
-- ════════════════════════════════════════════════════════════════════════════

-- 啟用常用擴充套件
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- 中文全文搜尋相似度
CREATE EXTENSION IF NOT EXISTS "btree_gin";     -- 複合 GIN 索引

-- 設定時區
SET timezone = 'Asia/Taipei';

-- ── 效能設定（會話層級提示，DGX 大記憶體最佳化）──────────────────────────
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = '100';
ALTER SYSTEM SET random_page_cost = '1.1';       -- SSD/NVMe
ALTER SYSTEM SET effective_io_concurrency = '200';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET max_connections = '200';

-- 套用設定（需要 superuser，PostgreSQL 官方 image 預設有權限）
SELECT pg_reload_conf();
