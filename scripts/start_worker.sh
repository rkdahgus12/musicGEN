#!/usr/bin/env bash
# RQ 워커 (GPU 1장 → 반드시 1개만 실행)
set -e
cd "$(dirname "$0")/../backend"
export PYTHONIOENCODING=utf-8
exec uv run python -u worker.py
