"""텍스트 필터.

- 금지어(실존 가수 이름 / 곡 제목): config/blocklist.txt
- 욕설: config/profanity.txt
형식: 한 줄에 하나, '#' 뒤는 주석, '!'로 시작하면 예외 단어(예: !시발점 → '시발'로 걸리지 않음).
"""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from .config import BLOCKLIST_PATH, PROFANITY_PATH


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def _compact(text: str) -> str:
    # 띄어쓰기·숫자·기호를 끼워 넣어 피하는 경우("씨 발", "시1발", "씨*발")까지 잡기 위해 글자만 남김
    # NFKC가 호환 자모(ㅅㅂ)를 조합용 자모(U+1100~)로 바꾸므로 그 범위도 남김
    return re.sub("[^a-z가-힣ㄱ-ㅎㅏ-ㅣᄀ-ᇿ]", "", text)


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> tuple[list[tuple[str, re.Pattern]], list[tuple[str, str]], list[str]]:
    ascii_terms, other_terms, exceptions = [], [], []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        term = raw.split("#", 1)[0].strip()
        if not term:
            continue
        if term.startswith("!"):
            if _compact(_norm(term[1:])):
                exceptions.append(_compact(_norm(term[1:])))
            continue
        t = _norm(term)
        if t.isascii():
            # 영문은 단어 경계로 매칭 ("bts"가 "debts"에 걸리지 않게), 공백 개수는 무시
            pattern = r"(?<![a-z0-9])" + r"\s*".join(map(re.escape, t.split())) + r"(?![a-z0-9])"
            ascii_terms.append((term, re.compile(pattern)))
        else:
            # 한글 등은 띄어쓰기/기호 무시하고 부분 일치
            if _compact(t):  # 빈 문자열은 모든 텍스트에 매칭되므로 제외
                other_terms.append((term, _compact(t)))
    return ascii_terms, other_terms, exceptions


def find_terms(path: Path, *texts: str) -> list[str]:
    """목록 파일의 단어 중 텍스트에서 발견된 것 반환 (없으면 빈 리스트)."""
    if not path.exists():
        return []
    ascii_terms, other_terms, exceptions = _load(str(path), path.stat().st_mtime)
    joined = _norm("\n".join(t for t in texts if t))
    compact = _compact(joined)
    for e in exceptions:
        compact = compact.replace(e, "")
    hits = [term for term, pat in ascii_terms if pat.search(joined)]
    hits += [term for term, t in other_terms if t in compact]
    return hits


def find_blocked(*texts: str, path: Path = BLOCKLIST_PATH) -> list[str]:
    return find_terms(path, *texts)


def find_profanity(*texts: str, path: Path = PROFANITY_PATH) -> list[str]:
    return find_terms(path, *texts)


def strip_profane_lines(lyrics: str, path: Path = PROFANITY_PATH) -> str:
    """욕설이 들어간 가사 줄을 제거 (LM 재생성으로도 못 걸러졌을 때의 마지막 안전장치)."""
    return "\n".join(line for line in lyrics.split("\n") if not find_terms(path, line))
