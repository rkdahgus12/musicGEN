# musicGEN

ACE-Step 1.5 기반 로컬 AI 노래 생성 플랫폼 (Suno 스타일).

> 진행 상황: **1단계 완료** (ACE-Step API 서버 + 간단/커스텀 모드 테스트). 2~4단계 진행 예정.

## 요구 사항

- NVIDIA GPU (테스트 환경: RTX 5060 8GB), 최신 드라이버
- Python 3.11~3.12, Git
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- **ffmpeg** (mp3 저장에 필수) — Windows: `winget install Gyan.FFmpeg`

## 설치

```bash
git clone https://github.com/rkdahgus12/musicGEN.git
cd musicGEN

# ACE-Step 1.5 (저장소에는 포함하지 않음)
git clone --depth 1 https://github.com/ACE-Step/ACE-Step-1.5.git
cd ACE-Step-1.5 && uv sync && cd ..

# 설정
cp .env.example .env    # GPU VRAM에 맞게 모델 조합 수정
```

### 모델 조합 (ACE-Step README 권장표)

| VRAM | DiT | LM | LM 백엔드 |
|------|-----|----|-----------|
| 6-8GB | acestep-v15-turbo | acestep-5Hz-lm-0.6B | pt |
| 8-16GB | acestep-v15-turbo | 0.6B (8-12GB) / 1.7B (12-16GB) | vllm |
| 16GB+ | turbo/sft 또는 XL | acestep-5Hz-lm-1.7B | vllm |

모델 가중치는 첫 생성 요청 시 자동 다운로드됩니다 (`ACE-Step-1.5/checkpoints`).

## 실행 (1단계)

```bash
# 터미널 1: ACE-Step API 서버 (localhost:8001)
bash scripts/start_acestep.sh

# 터미널 2: 간단 모드 + 커스텀 모드 테스트
python scripts/step1_test.py          # 또는 simple / custom
```

결과는 `storage/step1/*.mp3`와 메타데이터 `*.json`(`"ai_generated": true` 포함)으로 저장됩니다.

## 주의

- `.env`에서 `ACESTEP_API_KEY=`처럼 **빈 값**을 두면 ACE-Step이 인증을 켭니다. 인증을 안 쓰면 줄 자체를 주석 처리하세요.
- RTX 50 시리즈는 CUDA 12.8 PyTorch가 필요하며, ACE-Step `uv sync`가 자동으로 설치합니다.
