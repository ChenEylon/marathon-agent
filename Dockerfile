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
COPY google_credentials.json .

# Frontend built artifact
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Bake the training plan into the image so it survives on ephemeral deployments
RUN mkdir -p /app/data && python scripts/build_training_plan.py

# Startup: restore credentials from env vars, then launch agent
CMD ["sh", "-c", "python scripts/init_data.py && python agent/main.py"]
