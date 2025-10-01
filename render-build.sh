#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

# Install system packages required by the backend
apt-get update     && apt-get install -y --no-install-recommends         libboost-all-dev     && rm -rf /var/lib/apt/lists/*

# Install Python dependencies inside a virtual environment for Render debugging
VENV_PATH="/opt/render/project/.venv"
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install --no-cache-dir     -r backend/requirements.txt     -r backend/requirements-dev.txt
