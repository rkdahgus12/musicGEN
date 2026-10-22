"""금지어 필터: 실존 가수 이름 / 곡 제목. 목록은 config/blocklist.txt (한 줄에 하나, # 주석)."""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from .config import BLOCKLIST_PATH


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> tuple[list[tuple[str, re.Pattern]], list[tuple[str, str]]]:
    ascii_terms, other_terms = [], []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        term = raw.split("#", 1)[0].strip()
        if not term:
            continue
        t = _norm(term)
        if t.isascii():
            # 영문은 단어 경계로 매칭 ("bts"가 "debts"에 걸리지 않게), 공백 개수는 무시
            pattern = r"(?<![a-z0-9])" + r"\s*".join(map(re.escape, t.split())) + r"(?![a-z0-9])"
            ascii_terms.append((term, re.compile(pattern)))
        else:
            # 한글 등은 띄어쓰기 무시하고 부분 일치
            other_terms.append((term, re.sub(r"\s+", "", t)))
    return ascii_terms, other_terms


def find_blocked(*texts: str, path: Path = BLOCKLIST_PATH) -> list[str]:
    """입력 텍스트들에서 발견된 금지어 목록 반환 (없으면 빈 리스트)."""
    if not path.exists():
        return []
    ascii_terms, other_terms = _load(str(path), path.stat().st_mtime)
    joined = _norm("\n".join(t for t in texts if t))
    compact = re.sub(r"\s+", "", joined)
    hits = [term for term, pat in ascii_terms if pat.search(joined)]
    hits += [term for term, t in other_terms if t in compact]
    return hits
