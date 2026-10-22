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
