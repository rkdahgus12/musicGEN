"""RQ 워커. GPU 1장이므로 워커 프로세스는 1개만 띄움 → 한 번에 1곡씩 생성.

    cd backend && uv run python worker.py
Windows는 fork가 없어 SimpleWorker(+타이머 기반 타임아웃)를 사용, Linux/Docker는 일반 Worker.
"""
import sys

from rq import SimpleWorker, Worker
from rq.timeouts import TimerDeathPenalty

from datetime import datetime, timezone

from sqlmodel import select

from app.config import JOB_TIMEOUT
from app.db import Song, get_session, init_db
from app.queue import redis_conn, song_queue
from app.tasks import generate_song


class WindowsWorker(SimpleWorker):
    death_penalty_class = TimerDeathPenalty


def recover_orphans() -> None:
    """워커가 비정상 종료됐을 때 남은 작업 정리: 생성 중 → 실패, 큐에서 사라진 대기 → 재등록."""
    queued_ids = set(song_queue.job_ids)
    with get_session() as s:
        for song in s.exec(select(Song).where(Song.status.in_(["running", "queued"]))).all():
            if song.status == "running":
                song.status, song.error = "failed", "워커 재시작으로 생성이 중단됨"
                song.finished_at = datetime.now(timezone.utc)
                s.add(song)
                print(f"[worker] 중단된 작업 실패 처리: {song.id}")
            elif song.id not in queued_ids:
                song_queue.enqueue(generate_song, song.id, job_id=song.id, job_timeout=JOB_TIMEOUT + 300,
                                   result_ttl=86400, failure_ttl=86400)
                print(f"[worker] 유실된 대기 작업 재등록: {song.id}")
        s.commit()


if __name__ == "__main__":
    init_db()
    recover_orphans()
    worker_cls = WindowsWorker if sys.platform == "win32" else Worker
    print(f"[worker] {worker_cls.__name__} 시작, queue={song_queue.name}", flush=True)
    worker_cls([song_queue], connection=redis_conn).work(with_scheduler=False)
