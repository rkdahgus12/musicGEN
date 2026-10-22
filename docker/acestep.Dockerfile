# ACE-Step 1.5 REST API 서버 이미지 (빌드 컨텍스트: ./ACE-Step-1.5)
# ACE-Step 저장소의 Dockerfile을 바탕으로 API 모드 전용으로 단순화.
# 모델 가중치는 이미지에 넣지 않고 ./ACE-Step-1.5/checkpoints 를 볼륨으로 연결.
FROM nvidia/cuda:12.8.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_HTTP_TIMEOUT=600 \
    UV_CACHE_DIR=/root/.cache/uv \
    TOKENIZERS_PARALLELISM=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git curl ca-certificates libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app
# 의존성 레이어 캐시: lock 파일이 바뀔 때만 다시 설치
COPY pyproject.toml uv.lock ./
# 로컬 경로 의존성(nano-vllm)도 함께 있어야 설치 계획을 세울 수 있음
COPY acestep/third_parts/nano-vllm ./acestep/third_parts/nano-vllm
# 대용량 휠(torch, cudnn)은 캐시 마운트로 재시도 시 재다운로드 방지
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --python 3.11
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --python 3.11 && mkdir -p /app/checkpoints

ENV ACESTEP_API_HOST=0.0.0.0 \
    ACESTEP_API_PORT=8001
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -sf http://localhost:8001/health > /dev/null || exit 1

CMD ["sh", "-c", "exec uv run --no-sync acestep-api --host 0.0.0.0 --port ${ACESTEP_API_PORT}"]
