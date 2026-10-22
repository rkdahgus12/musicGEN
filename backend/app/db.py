"""SQLite 생성 이력."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Field, Session, SQLModel, create_engine

from .config import DB_PATH


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Song(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    mode: str  # simple | custom
    status: str = Field(default="queued", index=True)  # queued | running | succeeded | failed
    title: str = ""
    description: str = ""  # 간단 모드 입력
    style: str = ""  # 스타일 태그 / 캡션 (간단 모드는 LM 생성 결과)
    lyrics: str = ""
    vocal_language: str = ""
    bpm: Optional[int] = None
    key_scale: str = ""
    time_signature: str = ""
    duration: Optional[float] = None
    request: dict = Field(default_factory=dict, sa_column=Column(JSON))
    metas: dict = Field(default_factory=dict, sa_column=Column(JSON))
    audio_path: str = ""
    error: str = ""
    acestep_task_id: str = ""
    ai_generated: bool = True
    created_at: datetime = Field(default_factory=_now, index=True)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
