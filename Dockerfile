# ── Stage 1: build the React frontend ───────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci --prefer-offline
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# ── Stage 2: Python app ───────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/      ./agent/
COPY scripts/    ./scripts/
COPY config.yaml .
# Google OAuth client credentials (not the token — that lives on the volume)
COPY google_credentials.json .

# Frontend built artifact
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Volume for persistent data (data.db, vapid keys, garth tokens, google token)
RUN mkdir -p /app/data

CMD ["python", "agent/main.py"]
