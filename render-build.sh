#!/usr/bin/env bash
set -o errexit

# Install system packages required by the backend
apt-get update && apt-get install -y     libboost-all-dev

# Install Python dependencies
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
