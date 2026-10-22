"""FastAPI: 생성 요청(job_id 즉시 반환) / 상태 폴링 / 라이브러리 / 오디오 제공."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import select

from .config import CORS_ORIGINS, JOB_TIMEOUT, SONGS_DIR
from .db import Song, get_session, init_db
from .queue import redis_conn, song_queue
from .safety import find_blocked
from .schemas import SongCreate, SongOut
from .tasks import detect_language, generate_song


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="musicGEN API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


def to_out(song: Song) -> SongOut:
    position = None
    if song.status == "queued":
        ids = song_queue.job_ids
        position = ids.index(song.id) + 1 if song.id in ids else None
    return SongOut(
        **song.model_dump(exclude={"request", "metas", "audio_path", "acestep_task_id"}),
        job_id=song.id,
        audio_url=f"/api/songs/{song.id}/audio" if song.audio_path else None,
        queue_position=position,
    )


@app.get("/api/health")
def health():
    try:
        redis_ok = bool(redis_conn.ping())
    except Exception:
        redis_ok = False
    return {"ok": True, "redis": redis_ok, "queued": song_queue.count}


@app.post("/api/songs", response_model=SongOut, status_code=202)
def create_song(req: SongCreate):
    blocked = find_blocked(req.description, req.title, req.style, req.lyrics)
    if blocked:
        raise HTTPException(400, detail={"code": "blocked_term", "message": "실존 가수 이름/곡 제목은 사용할 수 없습니다.",
                                         "terms": blocked})

    if req.mode == "simple":
        title = req.description[:40]
        fields = dict(description=req.description)
    else:
        title = req.title or req.style[:40]
        fields = dict(style=req.style, lyrics=req.lyrics,
                      vocal_language=req.vocal_language or detect_language(req.lyrics or req.style))
    song = Song(
        mode=req.mode, title=title, request=req.model_dump(),
        bpm=req.bpm, key_scale=req.key_scale or "", time_signature=req.time_signature or "",
        duration=req.duration, **fields,
    )
    with get_session() as s:
        s.add(song)
        s.commit()
        s.refresh(song)
    try:
        song_queue.enqueue(generate_song, song.id, job_id=song.id, job_timeout=JOB_TIMEOUT + 300,
                           result_ttl=86400, failure_ttl=86400)
    except Exception as exc:
        with get_session() as s:
            db_song = s.get(Song, song.id)
            db_song.status, db_song.error = "failed", f"큐 등록 실패: {exc}"
            db_song.finished_at = datetime.now(timezone.utc)
            s.add(db_song)
            s.commit()
        raise HTTPException(503, detail="작업 큐(Redis)에 연결할 수 없습니다.")
    return to_out(song)


@app.get("/api/songs", response_model=list[SongOut])
def list_songs(limit: int = 50, offset: int = 0):
    with get_session() as s:
        songs = s.exec(select(Song).order_by(Song.created_at.desc()).offset(offset).limit(min(limit, 200))).all()
        return [to_out(x) for x in songs]


@app.get("/api/songs/{song_id}", response_model=SongOut)
def get_song(song_id: str):
    with get_session() as s:
        song = s.get(Song, song_id)
        if not song:
            raise HTTPException(404, "곡을 찾을 수 없습니다.")
        return to_out(song)


@app.get("/api/songs/{song_id}/audio")
def get_audio(song_id: str, download: bool = False):
    with get_session() as s:
        song = s.get(Song, song_id)
    if not song or not song.audio_path:
        raise HTTPException(404, "오디오가 아직 없습니다.")
    path = SONGS_DIR / song.audio_path
    filename = f"{(song.title or song.id)[:40]} (AI generated).mp3" if download else None
    return FileResponse(path, media_type="audio/mpeg", filename=filename)
