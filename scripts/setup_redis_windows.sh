#!/usr/bin/env bash
# Windows용 포터블 Redis 받기 (관리자 권한/설치 불필요). tools/redis 에 압축 해제.
# Docker나 Linux에서는 필요 없음 (redis 컨테이너/패키지 사용).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="${REDIS_WIN_VERSION:-8.10.2}"
DEST="$ROOT/tools/redis"
if [ -x "$DEST/redis-server.exe" ]; then echo "이미 설치됨: $DEST"; exit 0; fi
mkdir -p "$DEST"
TMP="$(mktemp -d)"
curl -fL -o "$TMP/redis.zip" \
  "https://github.com/redis-windows/redis-windows/releases/download/$VER/Redis-$VER-Windows-x64-msys2.zip"
unzip -q "$TMP/redis.zip" -d "$TMP/x"
# zip 안의 최상위 폴더 내용을 tools/redis 로 이동
SRC="$(dirname "$(find "$TMP/x" -name redis-server.exe | head -1)")"
cp -r "$SRC"/. "$DEST"/
rm -rf "$TMP"
"$DEST/redis-server.exe" --version
echo "완료: bash scripts/start_redis_windows.sh 로 실행"
