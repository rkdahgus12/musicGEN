#!/usr/bin/env bash
# ACE-Step API 서버 실행 (Git Bash / Linux). 루트의 .env 설정을 읽어서 넘김.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/ACE-Step-1.5"
set -a; . "$ROOT/.env"; set +a
export PYTHONIOENCODING=utf-8
command -v ffmpeg >/dev/null || echo "[경고] ffmpeg가 PATH에 없음 → mp3 저장 실패함 (README 참고)"
exec uv run acestep-api
