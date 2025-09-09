# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (for building wheels and PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmupdf-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
