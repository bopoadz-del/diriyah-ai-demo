#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
set -o xtrace

# Install system packages required by the backend and frontend builds
echo "[render-build] Installing system dependencies"
apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libboost-all-dev \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies inside a virtual environment for Render debugging
VENV_PATH="/opt/render/project/.venv"
echo "[render-build] Creating virtual environment at ${VENV_PATH}"
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install --no-cache-dir \
  -r backend/requirements.txt \
  -r backend/requirements-dev.txt

# Build the frontend bundle that FastAPI serves in production
pushd frontend
npm ci
npm run build
popd

rm -rf backend/frontend_dist
mkdir -p backend/frontend_dist
cp -R frontend/dist/. backend/frontend_dist/

echo "[render-build] Frontend bundle copied to backend/frontend_dist"
