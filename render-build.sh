#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

# Install system packages required by the backend and debugging tools
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    libboost-all-dev \
    python3-venv

# Install Node.js 18 for debugging the frontend when using Render Shell
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y --no-install-recommends nodejs
fi

rm -rf /var/lib/apt/lists/*

# Install Python dependencies inside a virtual environment for Render debugging
VENV_PATH="/opt/render/project/.venv"
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install --no-cache-dir \
    -r backend/requirements.txt \
    -r backend/requirements-dev.txt

# Install frontend dependencies for local debugging in Render Shell
pushd frontend >/dev/null
npm ci
popd >/dev/null
