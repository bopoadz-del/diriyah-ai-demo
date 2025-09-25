# Use slim Python base
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies, including those needed by ifcopenshell
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    python3-dev \
    sqlite3 \
    curl \
    libboost-all-dev \
    liboce-foundation-dev liboce-modeling-dev \
    liboce-ocaf-dev liboce-visualization-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy project code
COPY . .

EXPOSE 8000

# Start backend with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
