# CampDash — single image that builds the UI and serves UI + API + /admin.
# Works with a plain `docker build` on any host (Railway, Render, Fly, a VM…). No pre-build step.

# Stage 1: build the mobile UI
FROM node:20-slim AS web
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: the Python API (serves the built UI from /web)
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY bank/ ./bank/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY admin/ ./admin/
COPY media/ ./media/
COPY --from=web /ui/dist ./web

# Managed hosts inject $PORT; default 8080 for local/compose. Migrations run on boot.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
