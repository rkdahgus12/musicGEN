#!/usr/bin/env bash
# FastAPI 백엔드 (localhost:8000)
set -e
cd "$(dirname "$0")/../backend"
export PYTHONIOENCODING=utf-8
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
