#!/usr/bin/env bash
# 포터블 Redis 실행 (127.0.0.1:6379). 데이터는 storage/redis 에 저장.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/storage/redis"
cd "$ROOT/storage/redis"
exec "$ROOT/tools/redis/redis-server.exe" --bind 127.0.0.1 --port 6379 --appendonly yes --dir .
