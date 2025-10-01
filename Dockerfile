# Use slim Python base
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required by our Python stack
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     gcc     g++     libffi-dev     libssl-dev     python3-dev     sqlite3     curl     libboost-all-dev     && rm -rf /var/lib/apt/lists/*

# Create and configure a dedicated virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

EXPOSE 8000

# Start backend with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
