# Use slim Python base
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required by our Python stack
RUN apt-get update     && apt-get install -y --no-install-recommends         build-essential         gcc         g++         libffi-dev         libssl-dev         python3-dev         sqlite3         curl         libboost-all-dev     && rm -rf /var/lib/apt/lists/*

# Create and configure virtual environment
RUN python -m venv /opt/venv     && /opt/venv/bin/pip install --upgrade pip

ENV PATH="/opt/venv/bin:$PATH"

# Install Python requirements
COPY backend/requirements.txt backend/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r backend/requirements.txt

# Copy project code
COPY . .

EXPOSE 8000

# Start backend with Uvicorn from the virtual environment
CMD ["/opt/venv/bin/uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
