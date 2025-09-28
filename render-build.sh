#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

# Install system packages required by the backend
apt-get update     && apt-get install -y --no-install-recommends         libboost-all-dev         python3-venv     && rm -rf /var/lib/apt/lists/*

# Ensure the Render build installs into the same virtual environment as the Docker image
VENV_PATH="/opt/venv"
if [[ ! -d "${VENV_PATH}" ]]; then
    python3 -m venv "${VENV_PATH}"
    "${VENV_PATH}/bin/pip" install --upgrade pip
fi

source "${VENV_PATH}/bin/activate"

# Install Python dependencies needed for Render debugging inside the virtual environment
pip install --no-cache-dir     -r backend/requirements.txt     -r backend/requirements-dev.txt
