"""1단계: ACE-Step API로 간단 모드 / 커스텀 모드 각 1곡 생성 테스트.

사용법 (ACE-Step API 서버가 떠 있는 상태에서):
    python scripts/step1_test.py            # 둘 다
    python scripts/step1_test.py simple     # 간단 모드만
    python scripts/step1_test.py custom     # 커스텀 모드만
표준 라이브러리만 사용.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
BASE = os.environ.get("ACESTEP_URL", "http://127.0.0.1:8001").rstrip("/")
API_KEY = os.environ.get("ACESTEP_API_KEY", "")
OUT_DIR = ROOT / os.environ.get("STORAGE_DIR", "storage") / "step1"


def call(method, path, body=None):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read())
    if payload.get("code") != 200:
        raise RuntimeError(f"{path} 실패: {payload}")
    return payload["data"]


def generate(name, body, timeout_s=1800):
    print(f"\n=== [{name}] 요청 ===\n{json.dumps(body, ensure_ascii=False, indent=2)}")
    task = call("POST", "/release_task", body)
    task_id = task["task_id"]
    print(f"task_id={task_id}")

    start = time.time()
    while True:
        item = call("POST", "/query_result", {"task_id_list": [task_id]})[0]
        status = item["status"]
        if status == 1:
            break
        if status == 2:
            raise RuntimeError(f"[{name}] 생성 실패: {item}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"[{name}] {timeout_s}s 초과")
        print(f"  생성 중... {time.time() - start:.0f}s", end="\r")
        time.sleep(3)

    results = json.loads(item["result"])
    first = results[0]
    elapsed = time.time() - start
    print(f"\n[{name}] 완료 ({elapsed:.0f}s)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mp3_path = OUT_DIR / f"{name}.mp3"
    url = first.get("file") or ""
    if not url:
        raise RuntimeError(f"[{name}] 오디오 파일 경로가 비어 있음 (서버 로그 확인, ffmpeg 설치 여부 등): {first}")
    if url.startswith("/"):
        url = BASE + url
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"} if API_KEY else {})
    with urllib.request.urlopen(req, timeout=120) as r:
        mp3_path.write_bytes(r.read())

    meta = {
        "ai_generated": True,
        "mode": name,
        "request": body,
        "elapsed_sec": round(elapsed, 1),
        "prompt": first.get("prompt"),
        "lyrics": first.get("lyrics"),
        "metas": first.get("metas"),
        "dit_model": first.get("dit_model"),
        "lm_model": first.get("lm_model"),
        "seed_value": first.get("seed_value"),
    }
    (OUT_DIR / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장: {mp3_path} ({mp3_path.stat().st_size // 1024} KB)")
    print(f"  스타일: {meta['prompt']}")
    print(f"  메타: {meta['metas']}")
    print(f"  가사(앞부분): {(meta['lyrics'] or '')[:200]!r}")


SIMPLE = {
    # 간단 모드: 한 줄 설명 → 내장 LM이 캡션/가사/메타 자동 생성
    "sample_query": "비 오는 날 이별 발라드, 한국어 여성 보컬",
    "thinking": True,
    "batch_size": 1,
    "audio_format": "mp3",
}

CUSTOM = {
    # 커스텀 모드: 가사 + 스타일 태그 + 메타데이터 직접 지정
    "prompt": "korean ballad, piano, strings, emotional female vocal, slow tempo",
    "lyrics": (
        "[verse]\n창밖에 비가 내리면\n너의 목소리가 들려\n"
        "[chorus]\n안녕 이라는 말 대신\n조용히 우산을 접어\n"
    ),
    "vocal_language": "ko",
    "bpm": 72,
    "key_scale": "A minor",
    "time_signature": "4",
    "audio_duration": 60,
    "thinking": True,
    "batch_size": 1,
    "audio_format": "mp3",
}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print("health:", call("GET", "/health"))
    if which in ("all", "simple"):
        generate("simple", SIMPLE)
    if which in ("all", "custom"):
        generate("custom", CUSTOM)
