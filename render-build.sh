#!/usr/bin/env bash
set -o errexit

# Install system packages required by ifcopenshell
apt-get update && apt-get install -y \
    libboost-all-dev \
    liboce-foundation-dev liboce-modeling-dev \
    liboce-ocaf-dev liboce-visualization-dev

# Install Python dependencies
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
