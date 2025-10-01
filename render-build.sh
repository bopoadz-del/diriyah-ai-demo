#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

apt-get update   && apt-get install -y --no-install-recommends     ca-certificates     curl     libboost-all-dev   && rm -rf /var/lib/apt/lists/*
