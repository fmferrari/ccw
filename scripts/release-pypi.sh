#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f ".venv/bin/python" ]]; then
  echo "Missing .venv/bin/python. Create the virtualenv first." >&2
  exit 1
fi

# Load local secrets if present. .env is gitignored and must never be committed.
if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -z "${TWINE_PASSWORD:-}" ]]; then
  export TWINE_PASSWORD="${PYPI_API_TOKEN:-${PYPI_TOKEN:-${PYPI_TOKEN_PROD:-}}}"
fi

if [[ -z "${TWINE_USERNAME:-}" && -n "${TWINE_PASSWORD:-}" ]]; then
  export TWINE_USERNAME="__token__"
fi

if [[ -z "${TWINE_PASSWORD:-}" ]]; then
  echo "PyPI token not found. Set TWINE_PASSWORD or one of: PYPI_API_TOKEN, PYPI_TOKEN, PYPI_TOKEN_PROD." >&2
  exit 1
fi

if ! compgen -G "dist/*" > /dev/null; then
  echo "No artifacts found in dist/. Run '.venv/bin/python -m build' first." >&2
  exit 1
fi

exec .venv/bin/python -m twine upload "$@" dist/*
