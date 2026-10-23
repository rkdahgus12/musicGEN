import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import Queue

from app import main
from app.safety import find_blocked


def test_blocklist_matches():
    assert find_blocked("아이유 스타일 발라드") == ["아이유"]
    assert find_blocked("like taylor   swift") == ["Taylor Swift"]
    assert find_blocked("방탄 소년단 느낌") == ["방탄소년단"]
    assert find_blocked("paying my debts, a sad song") == []  # 'bts' 단어 경계
    assert find_blocked("비 오는 날 이별 발라드") == []


@pytest.fixture
def client(monkeypatch):
    q = Queue("test", connection=fakeredis.FakeRedis(), is_async=False)
    monkeypatch.setattr(main, "song_queue", q)
    calls = []
    monkeypatch.setattr(q, "enqueue", lambda f, sid, **kw: calls.append(sid))
    with TestClient(main.app) as c:
        c.calls = calls
        yield c


def test_create_simple_returns_job_id(client):
    r = client.post("/api/songs", json={"mode": "simple", "description": "비 오는 날 이별 발라드", "bpm": 70})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued" and body["job_id"] in client.calls and body["ai_generated"]
    assert client.get(f"/api/songs/{body['job_id']}").json()["bpm"] == 70


def test_blocked_prompt_rejected(client):
    r = client.post("/api/songs", json={"mode": "simple", "description": "BTS 같은 신나는 노래"})
    assert r.status_code == 400 and r.json()["detail"]["terms"] == ["BTS"]
    assert client.calls == []


@pytest.mark.parametrize("payload", [
    {"mode": "simple"},
    {"mode": "custom", "style": "pop"},
    {"mode": "custom", "style": "pop", "lyrics": "[verse]\nhi", "key_scale": "H major"},
    {"mode": "simple", "description": "x", "duration": 9999},
    {"mode": "simple", "description": "x", "bpm": 10},
])
def test_validation(client, payload):
    assert client.post("/api/songs", json=payload).status_code == 422


from app import tasks
from app.safety import find_profanity, strip_profane_lines


def test_profanity_matches():
    assert find_profanity("씨발 진짜") == ["씨발"]
    assert find_profanity("시1발", "씨 * 발") == ["씨발", "시발"]
    assert find_profanity("what the FUCK") == ["fuck"]
    assert find_profanity("시발점에서 다시 시작해") == []  # 예외 단어
    assert find_profanity("불이 꺼져가는 밤", "미친 듯이 달려") == []
    assert find_profanity("shitake mushroom") == []  # 영문 단어 경계


def test_strip_profane_lines():
    assert strip_profane_lines("[verse]\n좋은 날이야\n존나 좋아\n[chorus]\nla la") == "[verse]\n좋은 날이야\n[chorus]\nla la"


def test_profanity_prompt_rejected(client):
    r = client.post("/api/songs", json={"mode": "custom", "style": "rock", "lyrics": "[verse]\n병신 같은 하루"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "profanity"
    assert client.calls == []


class FakeAceStep:
    """create_sample은 준비된 가사를 순서대로 돌려주고, 생성 단계는 실패시켜 LM 단계만 검사."""

    def __init__(self, lyrics_seq):
        self.lyrics_seq, self.queries, self.temps = list(lyrics_seq), [], []

    def create_sample(self, query, vocal_language, instrumental, temperature=0.85):
        self.queries.append(query)
        self.temps.append(temperature)
        return {"caption": "ballad", "lyrics": self.lyrics_seq.pop(0), "bpm": 70, "duration": 30}

    def release_task(self, body):
        raise RuntimeError("stop after LM")


def _run_simple(client, monkeypatch, lyrics_seq):
    fake = FakeAceStep(lyrics_seq)
    monkeypatch.setattr(tasks, "AceStepClient", lambda: fake)
    sid = client.post("/api/songs", json={"mode": "simple", "description": "비 오는 날 발라드"}).json()["job_id"]
    with pytest.raises(RuntimeError):
        tasks.generate_song(sid)
    return fake, client.get(f"/api/songs/{sid}").json()


def test_simple_mode_regenerates_profane_lyrics(client, monkeypatch):
    fake, song = _run_simple(client, monkeypatch, ["[verse]\n씨발 비가 와", "[verse]\n비가 내려와"])
    assert len(fake.queries) == 2 and "clean lyrics" in fake.queries[0]
    assert fake.queries[0].startswith("Korean song, rainy day, ballad")  # 한국어 설명 → 영어 키워드
    assert song["lyrics"] == "[verse]\n비가 내려와"


def test_simple_mode_strips_lines_when_retries_exhausted(client, monkeypatch):
    bad = "[verse]\n비가 와\n존나 슬퍼"
    fake, song = _run_simple(client, monkeypatch, [bad] * tasks.MAX_LM_TRIES)
    assert len(fake.queries) == tasks.MAX_LM_TRIES
    assert song["lyrics"] == "[verse]\n비가 와"


def test_prompt_preview(client):
    r = client.post("/api/prompt-preview", json={"description": "비 오는 날 이별 발라드, 피아노"})
    assert r.json()["lm_query"] == "Korean song, rainy day, ballad, breakup, heartbreak, piano"
    assert client.post("/api/prompt-preview", json={"description": "sad ballad"}).json()["lm_query"] == "sad ballad"


def test_advanced_params_passed_to_acestep(client):
    from app.db import Song, get_session
    r = client.post("/api/songs", json={"mode": "custom", "style": "rock", "lyrics": "[verse]\nhi",
                                        "advanced": {"inference_steps": 16, "seed": 42, "infer_method": "sde",
                                                     "lm_temperature": 0.6, "enhance_style": True}})
    assert r.status_code == 202
    with get_session() as s:
        body = tasks.build_request(s.get(Song, r.json()["job_id"]))
    assert body["inference_steps"] == 16 and body["seed"] == 42 and body["use_random_seed"] is False
    assert body["infer_method"] == "sde" and body["lm_temperature"] == 0.6 and body["use_cot_caption"] is True
    assert r.json()["request"]["advanced"]["seed"] == 42


def test_advanced_validation(client):
    bad = {"mode": "simple", "description": "x", "advanced": {"inference_steps": 50}}
    assert client.post("/api/songs", json=bad).status_code == 422


def test_sane_drops_absurd_lm_values():
    assert tasks._sane(300, 50, 200) is None and tasks._sane(34, 50, 200) is None and tasks._sane(90, 50, 200) == 90


def test_retry_raises_temperature(client, monkeypatch):
    fake, _ = _run_simple(client, monkeypatch, ["[verse]\nbi-ga wa"] * 3 + ["[verse]\n비가 와"])
    assert fake.temps == [0.85, 1.0, 1.1, 1.1]
