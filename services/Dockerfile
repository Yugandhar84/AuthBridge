# One image for both Python services; SERVICE selects which app runs.
# Build context is the repository root (see docker-compose.yml).
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/requirements.txt /app/services/requirements.txt
RUN pip install --no-cache-dir -r /app/services/requirements.txt
COPY services /app/services
COPY shared /app/shared
ENV PYTHONPATH=/app/services/common:/app/services/payer:/app/services/provider \
    AUTHBRIDGE_SEED_DIR=/app/shared/seed
ARG SERVICE=payer
ENV SERVICE=${SERVICE}
CMD ["sh", "-c", "uvicorn ${SERVICE}_service.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
