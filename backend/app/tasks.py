"""RQ 워커가 실행하는 생성 작업: ACE-Step 호출 → mp3 저장 → AI generated 태그 → DB 기록."""
import json
import re
import traceback
from datetime import datetime, timezone

from mutagen.id3 import COMM, ID3, TIT2, TPE1, TXXX, USLT, ID3NoHeaderError

from .acestep_client import AceStepClient
from .config import JOB_TIMEOUT, MAX_DURATION, SONGS_DIR
from .db import Song, get_session
from .prompt_en import to_lm_query
from .safety import find_profanity, strip_profane_lines
from .schemas import Advanced

AI_NOTE = "AI generated (ACE-Step 1.5 via musicGEN)"
MAX_LM_TRIES = 4
RETRY_TEMP_STEP = 0.15
# 내장 LM에 주는 힌트 (설명 뒤에 붙임)
CLEAN_HINT_EN = ", clean lyrics without profanity"


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
    adv = Advanced(**song.request.get("advanced", {}))
    body = {
        "prompt": song.style,
        "lyrics": song.lyrics or "[Instrumental]",
        "vocal_language": song.vocal_language or "unknown",
        "thinking": adv.thinking,  # LM이 audio code 계획 → 품질 향상
        # 커스텀 모드에서 '스타일 보강'을 켜면 LM이 스타일 태그를 자세한 설명으로 다시 씀
        "use_cot_caption": song.mode == "custom" and adv.enhance_style,
        "batch_size": 1,
        "audio_format": "mp3",
        "inference_steps": adv.inference_steps,
        "shift": adv.shift,
        "infer_method": adv.infer_method,
        "lm_temperature": adv.lm_temperature,
        "lm_cfg_scale": adv.lm_cfg_scale,
        "lm_top_p": adv.lm_top_p,
        "lm_top_k": adv.lm_top_k,
        "lm_repetition_penalty": adv.lm_repetition_penalty,
        "lm_negative_prompt": adv.lm_negative_prompt,
    }
    if adv.seed is not None:
        body["use_random_seed"] = False
        body["seed"] = adv.seed
    if song.bpm:
        body["bpm"] = song.bpm
    if song.key_scale:
        body["key_scale"] = song.key_scale
    if song.time_signature:
        body["time_signature"] = song.time_signature
    if song.duration:
        body["audio_duration"] = song.duration
    return body


def _sane(value, lo, hi):
    """LM이 가끔 BPM 34, 300처럼 엉뚱한 값을 내므로 범위를 벗어나면 버림 (생성 단계 LM이 다시 정함)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return value if lo <= v <= hi else None


def generate_song(song_id: str) -> str:
    song = _update(song_id, status="running", started_at=_now(), error="")
    client = AceStepClient()
    try:
        req = song.request
        if song.mode == "simple":
            # 1) 내장 LM으로 가사/스타일/메타 생성
            lang = req.get("vocal_language") or detect_language(song.description)
            instrumental = req.get("instrumental", False)
            adv = Advanced(**req.get("advanced", {}))
            # 0.6B LM은 한국어 설명을 잘 이해 못 하므로 영어 키워드로 변환해서 전달
            lm_query = req.get("lm_query") or to_lm_query(song.description, lang)
            query = lm_query + CLEAN_HINT_EN
            _update(song_id, metas={"lm_query": lm_query})
            for attempt in range(MAX_LM_TRIES):
                # 온도가 낮으면 LM이 매번 비슷한 결과(로마자 가사 등)를 내므로 재시도마다 조금씩 올림
                temperature = min(adv.lm_temperature + RETRY_TEMP_STEP * attempt, max(adv.lm_temperature, 1.1))
                sample = client.create_sample(query, vocal_language=lang, instrumental=instrumental,
                                              temperature=temperature)
                lyrics = sample.get("lyrics", "")
                # 0.6B LM이 한국어 가사를 로마자로 쓰는 경우가 있어 한글이 없으면 다시 생성
                romanized = lang == "ko" and not instrumental and not re.search(r"[가-힣]", lyrics)
                # 욕설이 섞이면 다시 생성
                profane = find_profanity(lyrics, sample.get("caption", ""))
                if not romanized and not profane:
                    break
                print(f"[generate_song] LM 재생성 (temp={temperature:.2f}, romanized={romanized}, profanity={profane})", flush=True)
            if find_profanity(sample.get("lyrics", "")):
                # 재생성으로도 안 걸러지면 해당 줄 제거
                sample["lyrics"] = strip_profane_lines(sample["lyrics"])
            # 2) 사용자가 지정한 옵션이 LM 결과보다 우선
            song = _update(
                song_id,
                style=sample.get("caption", ""),
                lyrics=sample.get("lyrics", ""),
                vocal_language=sample.get("vocal_language") or lang,
                bpm=req.get("bpm") or _sane(sample.get("bpm"), 50, 200),
                key_scale=req.get("key_scale") or sample.get("keyscale") or "",
                time_signature=req.get("time_signature") or str(sample.get("timesignature") or ""),
                duration=req.get("duration") or _sane(sample.get("duration"), 10, MAX_DURATION),
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
            metas={**song.metas, **metas, "dit_model": result.get("dit_model"), "lm_model": result.get("lm_model"),
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
