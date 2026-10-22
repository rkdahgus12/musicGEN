"""RQ 워커가 실행하는 생성 작업: ACE-Step 호출 → mp3 저장 → AI generated 태그 → DB 기록."""
import json
import re
import traceback
from datetime import datetime, timezone

from mutagen.id3 import COMM, ID3, TIT2, TPE1, TXXX, USLT, ID3NoHeaderError

from .acestep_client import AceStepClient
from .config import JOB_TIMEOUT, SONGS_DIR
from .db import Song, get_session

AI_NOTE = "AI generated (ACE-Step 1.5 via musicGEN)"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def detect_language(text: str) -> str:
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[一-鿿]", text):
        return "zh"
    return "en"


def _update(song_id: str, **fields) -> Song:
    with get_session() as s:
        song = s.get(Song, song_id)
        for k, v in fields.items():
            setattr(song, k, v)
        s.add(song)
        s.commit()
        s.refresh(song)
        return song


def _tag_mp3(path, song: Song) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    tags.add(TIT2(encoding=3, text=song.title or "Untitled"))
    tags.add(TPE1(encoding=3, text="musicGEN (AI)"))
    tags.add(COMM(encoding=3, lang="eng", desc="", text=AI_NOTE))
    tags.add(TXXX(encoding=3, desc="AI_GENERATED", text="true"))
    tags.add(TXXX(encoding=3, desc="AI_MODEL", text=f"{song.metas.get('dit_model', '')} / {song.metas.get('lm_model', '')}"))
    if song.lyrics:
        tags.add(USLT(encoding=3, lang="und", desc="", text=song.lyrics))
    tags.save(path)


def build_request(song: Song) -> dict:
    """ACE-Step /release_task 요청 본문. 스타일/가사는 이미 확정된 상태(간단 모드는 LM 결과)."""
    body = {
        "prompt": song.style,
        "lyrics": song.lyrics or "[Instrumental]",
        "vocal_language": song.vocal_language or "unknown",
        "thinking": True,  # LM이 audio code 생성 → 품질 향상
        "use_cot_caption": False,  # 사용자 스타일을 LM이 바꾸지 않게
        "batch_size": 1,
        "audio_format": "mp3",
    }
    if song.bpm:
        body["bpm"] = song.bpm
    if song.key_scale:
        body["key_scale"] = song.key_scale
    if song.time_signature:
        body["time_signature"] = song.time_signature
    if song.duration:
        body["audio_duration"] = song.duration
    return body


def generate_song(song_id: str) -> str:
    song = _update(song_id, status="running", started_at=_now(), error="")
    client = AceStepClient()
    try:
        req = song.request
        if song.mode == "simple":
            # 1) 내장 LM으로 가사/스타일/메타 생성
            lang = req.get("vocal_language") or detect_language(song.description)
            for _ in range(3):
                sample = client.create_sample(song.description, vocal_language=lang,
                                              instrumental=req.get("instrumental", False))
                # 0.6B LM이 한국어 가사를 로마자로 쓰는 경우가 있어 한글이 없으면 다시 생성
                if lang != "ko" or req.get("instrumental") or re.search(r"[가-힣]", sample.get("lyrics", "")):
                    break
            # 2) 사용자가 지정한 옵션이 LM 결과보다 우선
            song = _update(
                song_id,
                style=sample.get("caption", ""),
                lyrics=sample.get("lyrics", ""),
                vocal_language=sample.get("vocal_language") or lang,
                bpm=req.get("bpm") or sample.get("bpm"),
                key_scale=req.get("key_scale") or sample.get("keyscale") or "",
                time_signature=req.get("time_signature") or str(sample.get("timesignature") or ""),
                duration=req.get("duration") or sample.get("duration"),
            )

        # 3) 노래 생성
        body = build_request(song)
        task_id = client.release_task(body)
        _update(song_id, acestep_task_id=task_id)
        result = client.wait_result(task_id, timeout=JOB_TIMEOUT)

        # 4) mp3 저장 + 메타데이터
        dest = SONGS_DIR / f"{song_id}.mp3"
        client.download(result.get("file", ""), dest)
        metas = result.get("metas") or {}
        song = _update(
            song_id,
            audio_path=dest.name,
            metas={**metas, "dit_model": result.get("dit_model"), "lm_model": result.get("lm_model"),
                   "seed": result.get("seed_value"), "acestep_request": body},
            bpm=song.bpm or metas.get("bpm"),
            key_scale=song.key_scale or metas.get("keyscale") or "",
            duration=song.duration or metas.get("duration"),
        )
        _tag_mp3(dest, song)
        (SONGS_DIR / f"{song_id}.json").write_text(json.dumps({
            "ai_generated": True, "note": AI_NOTE, "id": song.id, "mode": song.mode, "title": song.title,
            "description": song.description, "style": song.style, "lyrics": song.lyrics,
            "bpm": song.bpm, "key_scale": song.key_scale, "duration": song.duration, "metas": song.metas,
            "created_at": song.created_at.isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        _update(song_id, status="succeeded", finished_at=_now())
        return dest.name
    except Exception as exc:
        _update(song_id, status="failed", finished_at=_now(), error=f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise
