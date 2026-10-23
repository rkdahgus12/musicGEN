"""요청/응답 스키마 + 입력 검증."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import MAX_DURATION

_NOTES = "ABCDEFG"
_ACCIDENTALS = ("", "#", "b", "♯", "♭")
VALID_KEYS = {f"{n}{a} {m}" for n in _NOTES for a in _ACCIDENTALS for m in ("major", "minor")}
VALID_LANGS = {"ko", "en", "ja", "zh", "es", "fr", "de", "it", "pt", "ru", "unknown"}


class Advanced(BaseModel):
    """ACE-Step 세부 파라미터. 기본값은 실험으로 고른 '균형' 설정."""
    # LM (가사/스타일 작성 + 오디오 코드 계획)
    lm_temperature: float = Field(0.85, ge=0.1, le=1.5)
    lm_cfg_scale: float = Field(2.5, ge=1.0, le=5.0)
    lm_top_p: float = Field(0.9, ge=0.5, le=1.0)
    lm_top_k: int = Field(0, ge=0, le=200)
    lm_repetition_penalty: float = Field(1.0, ge=1.0, le=2.0)
    lm_negative_prompt: str = Field("NO USER INPUT", max_length=300)
    thinking: bool = True  # LM이 오디오 코드를 먼저 계획 (품질↑, 느림)
    enhance_style: bool = False  # 커스텀 모드: LM이 스타일 태그를 자세한 설명으로 보강
    # DiT (오디오 생성)
    inference_steps: int = Field(8, ge=1, le=20)  # turbo 권장 8
    shift: float = Field(3.0, ge=1.0, le=5.0)  # turbo 권장 3.0
    infer_method: Literal["ode", "sde"] = "ode"
    seed: Optional[int] = Field(None, ge=0, le=2**32 - 1)  # None이면 랜덤


class SongCreate(BaseModel):
    mode: Literal["simple", "custom"]
    # 간단 모드
    description: str = Field("", max_length=500)
    # 커스텀 모드
    title: str = Field("", max_length=100)
    style: str = Field("", max_length=512)
    lyrics: str = Field("", max_length=4000)
    instrumental: bool = False
    # 공통 옵션 (None이면 LM이 자동 결정)
    duration: Optional[float] = Field(None, ge=10)
    bpm: Optional[int] = Field(None, ge=30, le=300)
    key_scale: Optional[str] = None
    time_signature: Optional[Literal["2", "3", "4", "6"]] = None
    vocal_language: Optional[str] = None  # None이면 입력 텍스트로 자동 감지
    # 간단 모드: LM에 보낼 영어 설명 직접 지정 (비우면 자동 변환)
    lm_query: str = Field("", max_length=500)
    advanced: Advanced = Field(default_factory=Advanced)

    @field_validator("description", "title", "style", "lyrics", "lm_query")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("duration")
    @classmethod
    def _max_duration(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > MAX_DURATION:
            raise ValueError(f"곡 길이는 최대 {MAX_DURATION}초")
        return v

    @field_validator("key_scale")
    @classmethod
    def _key(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        parts = v.strip().split()
        if len(parts) == 2:
            v = parts[0][:1].upper() + parts[0][1:] + " " + parts[1].lower()
        if v not in VALID_KEYS:
            raise ValueError("키는 'C major', 'A minor', 'F# minor' 형식")
        return v

    @field_validator("vocal_language")
    @classmethod
    def _lang(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in VALID_LANGS:
            raise ValueError(f"지원 언어: {sorted(VALID_LANGS)}")
        return v or None

    @model_validator(mode="after")
    def _by_mode(self):
        if self.mode == "simple" and not self.description:
            raise ValueError("간단 모드는 description(한 줄 설명)이 필요")
        if self.mode == "custom":
            if not self.style:
                raise ValueError("커스텀 모드는 style(스타일 태그)이 필요")
            if not self.lyrics and not self.instrumental:
                raise ValueError("커스텀 모드는 lyrics가 필요 (연주곡이면 instrumental=true)")
        return self


class SongOut(BaseModel):
    id: str
    job_id: str
    mode: str
    status: str
    title: str
    description: str
    style: str
    lyrics: str
    vocal_language: str
    bpm: Optional[int]
    key_scale: str
    time_signature: str
    duration: Optional[float]
    error: str
    ai_generated: bool
    audio_url: Optional[str]
    queue_position: Optional[int] = None
    # 다시 만들기/재현용: 요청 원본(옵션+고급 설정), 실제 LM 쿼리, 사용된 시드
    request: dict = {}
    lm_query: str = ""
    seed: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
