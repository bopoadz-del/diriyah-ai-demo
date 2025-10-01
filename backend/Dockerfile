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

# System deps for textract, poppler, OCR, etc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        poppler-utils \
        tesseract-ocr \
        libreoffice \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    gunicorn==21.2.0

COPY backend /app/backend
RUN mkdir -p /app/uploads /app/images /app/storage
COPY --from=frontend-build /frontend/dist /app/frontend_dist

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "backend.main:app"]
