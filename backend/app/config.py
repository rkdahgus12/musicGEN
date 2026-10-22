"""설정: 저장소 루트의 .env를 읽음. 경로는 루트 기준 상대경로 허용."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (ROOT / p).resolve()


ACESTEP_URL = os.getenv("ACESTEP_URL", "http://127.0.0.1:8001").rstrip("/")
ACESTEP_API_KEY = os.getenv("ACESTEP_API_KEY") or None
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "songs")

STORAGE_DIR = _path(os.getenv("STORAGE_DIR", "./storage"))
SONGS_DIR = STORAGE_DIR / "songs"
DB_PATH = _path(os.getenv("DB_PATH", str(STORAGE_DIR / "musicgen.db")))
BLOCKLIST_PATH = _path(os.getenv("BLOCKLIST_PATH", "./config/blocklist.txt"))

# Tier3(6-8GB) + LM 기준 최대 480초. GPU에 맞게 .env에서 조정
MAX_DURATION = int(os.getenv("MAX_DURATION", "480"))
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "1800"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

SONGS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
