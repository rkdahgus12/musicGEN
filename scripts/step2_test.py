"""2단계: 백엔드(FastAPI+RQ) 엔드투엔드 테스트.

백엔드(:8000), 워커, Redis, ACE-Step API가 떠 있는 상태에서:
    python scripts/step2_test.py
표준 라이브러리만 사용.
"""
import json
import os
import time
import urllib.error
import urllib.request

BASE = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, headers={"Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def wait(job_id, timeout=1800):
    start, last = time.time(), None
    while time.time() - start < timeout:
        _, song = call("GET", f"/api/songs/{job_id}")
        if song["status"] != last:
            print(f"  [{time.time() - start:5.0f}s] {song['status']}"
                  + (f" (대기 순번 {song['queue_position']})" if song.get("queue_position") else ""))
            last = song["status"]
        if song["status"] in ("succeeded", "failed"):
            return song
        time.sleep(3)
    raise TimeoutError(job_id)


print("health:", call("GET", "/api/health"))

print("\n[1] 금지어 차단")
print("  ", call("POST", "/api/songs", {"mode": "simple", "description": "아이유 같은 발라드"}))

print("\n[2] 입력 검증 (키 형식 오류)")
code, body = call("POST", "/api/songs", {"mode": "custom", "style": "pop", "lyrics": "[verse]\nhi", "key_scale": "H major"})
print("  ", code, body["detail"][0]["msg"])

jobs = {
    "simple": {"mode": "simple", "description": "비 오는 날 이별 발라드, 피아노와 여성 보컬",
               "duration": 60, "bpm": 70, "key_scale": "A minor"},
    "custom": {"mode": "custom", "title": "여름밤 드라이브",
               "style": "k-pop, synthpop, upbeat, bright female vocal, 80s synth, drum machine",
               "lyrics": "[verse]\n창문을 열고 바람을 맞아\n네온 불빛이 춤을 춰\n[chorus]\n여름밤 드라이브\n너와 나 둘이서\n",
               "duration": 45, "bpm": 118},
}
ids = {}
print("\n[3] 생성 요청 (job_id 즉시 반환)")
for name, payload in jobs.items():
    t = time.time()
    code, song = call("POST", "/api/songs", payload)
    print(f"   {name}: HTTP {code}, job_id={song['job_id']}, status={song['status']}, "
          f"queue={song['queue_position']}, {1000 * (time.time() - t):.0f}ms")
    ids[name] = song["job_id"]

for name, job_id in ids.items():
    print(f"\n[4] 폴링: {name}")
    song = wait(job_id)
    if song["status"] == "failed":
        print("   실패:", song["error"])
        continue
    print(f"   style : {song['style'][:120]}")
    print(f"   meta  : bpm={song['bpm']} key={song['key_scale']} duration={song['duration']} lang={song['vocal_language']}")
    print(f"   lyrics: {song['lyrics'][:120]!r}")
    print(f"   audio : {BASE}{song['audio_url']}")

print("\n[5] 라이브러리:", [(s["title"], s["status"]) for s in call("GET", "/api/songs")[1]])
