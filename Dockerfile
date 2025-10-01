FROM node:20-bullseye-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
COPY frontend/vite.config.js frontend/tailwind.config.js frontend/postcss.config.js frontend/index.html ./
COPY frontend/src ./src
COPY frontend/public ./public

RUN npm ci \
    && npm run build


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

# Create and configure a dedicated virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python requirements
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy project code and runtime assets
COPY backend /app/backend
RUN mkdir -p /app/uploads /app/images /app/storage

# Include the compiled frontend bundle
COPY --from=frontend-build /frontend/dist /app/frontend_dist

EXPOSE 8000

# Start backend with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
