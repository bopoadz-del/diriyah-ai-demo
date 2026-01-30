#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_BACKEND_OPTIONALS="${INSTALL_BACKEND_OPTIONALS:-false}"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install --requirement "$PROJECT_ROOT/requirements.txt"
python -m pip install --requirement "$PROJECT_ROOT/backend/requirements-dev.txt"

if [[ "$INSTALL_BACKEND_OPTIONALS" == "true" ]]; then
  echo "Installing full backend dependency stack (this may take several minutes)"
  python -m pip install --requirement "$PROJECT_ROOT/backend/requirements.txt"
  python -m pip install --requirement "$PROJECT_ROOT/backend/requirements-optional.txt"
fi

echo "Environment ready. Activate it with: source $VENV_DIR/bin/activate"
