FROM python:3.11.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config
COPY skills ./skills
COPY prompts ./prompts
COPY static ./static
COPY packages ./packages
COPY VERSION .

ENV PYTHONUNBUFFERED=1 \
    VERSION=0.1.0 \
    IMAGE_TAG=0.1.0-dev \
    POSTGRES_HOST=postgres \
    POSTGRES_PORT=5432

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=12 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
