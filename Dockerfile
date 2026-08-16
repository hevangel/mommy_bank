# ---------- Stage 1: build the SPA ----------
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: python runtime (API + SPA in one container) ----------
FROM python:3.12-slim
WORKDIR /app

# backend package first for layer caching
COPY backend/pyproject.toml ./
COPY backend/mommybank ./mommybank
RUN pip install --no-cache-dir .

# SPA served by FastAPI
ENV MOMMYBANK_STATIC_DIR=/app/frontend/dist
COPY --from=frontend /app/dist ./frontend/dist

# SQLite lives on a volume
ENV MOMMYBANK_DB=/app/data/mommybank.db
RUN mkdir -p /app/data
VOLUME /app/data

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health').read()" || exit 1

CMD ["uvicorn", "mommybank.main:app", "--host", "0.0.0.1", "--port", "8000"]
