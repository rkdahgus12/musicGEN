#!/usr/bin/env bash
# ACE-Step 모델 가중치를 한 파일씩 순서대로 받기 (Git Bash / Linux / WSL).
# ACE-Step 내장 다운로더(huggingface_hub 병렬 다운로드)가 1MB/s 이하로 느려지는 경우가 있어
# 첫 실행 전에 이 스크립트로 미리 받아 두면 빠름. 중단돼도 다시 실행하면 이어받음.
#   bash scripts/download_models.sh                  # 기본 묶음 (turbo, vae, 임베딩, 1.7B LM)
#   bash scripts/download_models.sh acestep-5Hz-lm-0.6B   # 추가 모델 (별도 저장소)
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/ACE-Step-1.5/checkpoints"
REPO="${1:+ACE-Step/$1}"
REPO="${REPO:-ACE-Step/Ace-Step1.5}"
# 추가 모델은 checkpoints/<모델명>/ 아래, 기본 묶음은 checkpoints/ 바로 아래에 저장
SUB="${1:+$1/}"
mkdir -p "$DEST"

# 파일 목록: "크기 경로" 한 줄씩 (Windows python의 \r 제거)
LIST="$(curl -fsS "https://huggingface.co/api/models/$REPO/tree/main?recursive=1" \
  | python -c "import sys,json; [print(f['size'], f['path']) for f in json.load(sys.stdin) if f['type']=='file']" \
  | tr -d '\r')"

echo "$LIST" | while read -r size path; do
  out="$DEST/$SUB$path"
  if [ -f "$out" ] && [ "$(wc -c < "$out")" -eq "$size" ]; then
    echo "있음  $SUB$path"; continue
  fi
  mkdir -p "$(dirname "$out")"
  echo "받기  $SUB$path ($((size / 1000000))MB)"
  curl -fL -C - --retry 5 --retry-all-errors -o "$out.part" \
    "https://huggingface.co/$REPO/resolve/main/$path"
  mv "$out.part" "$out"
done
echo "완료: $DEST"
