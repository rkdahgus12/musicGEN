#!/usr/bin/env bash
# Next.js 프론트엔드 (localhost:3000). 처음 한 번은 npm install 필요.
set -e
cd "$(dirname "$0")/../frontend"
[ -d node_modules ] || npm install
exec npm run dev
