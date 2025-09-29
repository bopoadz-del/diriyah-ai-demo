FROM python:3.10-slim

WORKDIR /app

# System deps for textract, poppler, OCR, etc.
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     poppler-utils     tesseract-ocr     libreoffice     libmagic1     && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt     gunicorn==21.2.0

COPY backend /app/backend
COPY uploads /app/uploads
COPY images /app/images
COPY storage /app/storage

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "backend.main:app"]