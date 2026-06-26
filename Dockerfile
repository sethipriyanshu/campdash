# CampDash API image. The mobile UI is pre-built into web/ before docker build (see deploy.sh).
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
COPY web/ ./web/

# Apply migrations, then serve (UI + API + /admin from one origin).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
