#!/usr/bin/env bash
# Runs the FastAPI backend with both repo root and backend/ on PYTHONPATH, so `app.*`
# (backend package) and `models.*` / `data.*` / `simulation.*` / `financial.*` (repo-root
# packages) resolve identically to how tests import them (see conftest.py).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/backend:$PWD"
exec uvicorn app.main:app --reload --port 8000
