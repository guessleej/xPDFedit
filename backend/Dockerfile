# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# 建置依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim

# 系統依賴
# 注意: libgl1 取代 libgl1-mesa-glx（ARM64/aarch64 相容）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# 複製 Python 套件
COPY --from=builder /install /usr/local

WORKDIR /app

# 非 root 使用者（安全最佳實踐）
RUN groupadd -r xcloud && useradd -r -g xcloud xcloud \
    && mkdir -p /app/data/storage/uploads /app/data/storage/output \
    && chown -R xcloud:xcloud /app

COPY --chown=xcloud:xcloud . .

USER xcloud

EXPOSE 8000

# 開發模式：單 worker
# 生產模式：由 docker-compose.dgx.yml 覆蓋為 gunicorn 多 worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
