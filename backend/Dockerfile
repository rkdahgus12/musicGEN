# 백엔드(FastAPI) / 워커(RQ) 공용 이미지. 빌드 컨텍스트: ./backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/

# config.py가 저장소 루트(/app)를 기준으로 storage/, config/ 를 찾음
WORKDIR /app/backend
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
