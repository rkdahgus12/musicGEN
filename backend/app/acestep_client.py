"""ACE-Step 1.5 API 클라이언트 (docs/en/API.md 규격)."""
import json
import time
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from .config import ACESTEP_API_KEY, ACESTEP_URL


class AceStepError(RuntimeError):
    pass


class AceStepClient:
    def __init__(self, base_url: str = ACESTEP_URL, api_key: Optional[str] = ACESTEP_API_KEY):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        # create_sample은 LM 생성이 끝날 때까지 응답이 없으므로 넉넉히
        self.http = httpx.Client(base_url=base_url, headers=headers, timeout=httpx.Timeout(600, connect=10))

    def _post(self, path: str, body: dict) -> Any:
        r = self.http.post(path, json=body)
        r.raise_for_status()
        payload = r.json()
        if payload.get("code") != 200:
            raise AceStepError(f"{path}: {payload.get('error')}")
        return payload["data"]

    def health(self) -> dict:
        return self.http.get("/health").raise_for_status().json()["data"]

    def create_sample(self, query: str, vocal_language: str = "unknown", instrumental: bool = False,
                      temperature: float = 0.85) -> dict:
        """내장 LM으로 한 줄 설명 → caption/lyrics/bpm/keyscale/duration/timesignature 생성."""
        return self._post("/v1/create_sample", {
            "query": query, "vocal_language": vocal_language, "instrumental": instrumental,
            "temperature": temperature,
        })

    def release_task(self, body: dict) -> str:
        return self._post("/release_task", body)["task_id"]

    def wait_result(self, task_id: str, timeout: float, poll: float = 3.0,
                    on_tick: Optional[Callable[[], None]] = None) -> dict:
        deadline = time.time() + timeout
        errors = 0
        while time.time() < deadline:
            try:
                item = self._post("/query_result", {"task_id_list": [task_id]})[0]
                errors = 0
            except httpx.TransportError:
                # 생성 중 서버가 keep-alive 연결을 끊는 경우가 있음 → 조회는 재시도해도 안전
                errors += 1
                if errors > 5:
                    raise
                time.sleep(poll)
                continue
            if item["status"] == 1:
                return json.loads(item["result"])[0]
            if item["status"] == 2:
                raise AceStepError(f"생성 실패: {item.get('result') or item}")
            if on_tick:
                on_tick()
            time.sleep(poll)
        raise AceStepError(f"생성 시간 초과 ({timeout:.0f}s)")

    def download(self, file_url: str, dest: Path) -> None:
        if not file_url:
            raise AceStepError("결과에 오디오 파일 경로가 없음 (ACE-Step 서버 로그/ffmpeg 확인)")
        for attempt in range(3):
            try:
                with self.http.stream("GET", file_url) as r:
                    r.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in r.iter_bytes():
                            f.write(chunk)
                return
            except httpx.TransportError:
                if attempt == 2:
                    raise
                time.sleep(2)
