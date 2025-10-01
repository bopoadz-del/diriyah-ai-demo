FROM node:20-bullseye-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
COPY frontend/vite.config.js frontend/tailwind.config.js frontend/postcss.config.js frontend/index.html ./
COPY frontend/src ./src
COPY frontend/public ./public

RUN npm ci || npm install
RUN npm run build

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required by the Python stack
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        python3-dev \
        sqlite3 \
        curl \
        libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy project code and runtime assets
COPY backend /app/backend
RUN mkdir -p /app/uploads /app/images /app/storage
# Include the compiled frontend bundle
COPY --from=frontend-build /frontend/dist /app/frontend_dist

EXPOSE 8000
CMD ["gunicorn", "backend.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
