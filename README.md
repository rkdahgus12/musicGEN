# musicGEN

ACE-Step 1.5 기반 로컬 AI 노래 생성 플랫폼 (Suno 스타일).

> 진행 상황: **1단계** ACE-Step API 테스트 ✅ / **2단계** FastAPI + RQ 생성 파이프라인 ✅ / **3단계** Next.js 프론트엔드 ✅ / 4단계 docker-compose

## 구조

```
[frontend: Next.js :3000] → /api 프록시 → [backend: FastAPI :8000] → Redis 큐 → [worker: RQ 1개] → [ACE-Step API :8001] → GPU
                                                              ↓
                                              storage/songs/*.mp3 + storage/musicgen.db
```

| 폴더 | 내용 |
|------|------|
| `frontend/` | Next.js + Tailwind 웹 UI (만들기 / 결과 / 내 라이브러리) |
| `backend/` | FastAPI 앱(`app/`), RQ 워커(`worker.py`), 테스트 |
| `config/blocklist.txt` | 금지어(실존 가수/곡 제목) 목록. 수정 즉시 반영 |
| `scripts/` | 실행/설치/테스트 스크립트 |
| `storage/` | 생성된 mp3, 메타 json, SQLite DB (git 제외) |
| `ACE-Step-1.5/`, `tools/` | 각 PC에서 받는 외부 코드/바이너리 (git 제외) |

## 요구 사항

- NVIDIA GPU (테스트 환경: RTX 5060 8GB), 최신 드라이버
- Python 3.11~3.12, Node.js 20+, Git, Git Bash(Windows)
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- **ffmpeg** (mp3 저장에 필수) — Windows: `winget install Gyan.FFmpeg` 후 터미널 재시작
- **Redis** — Windows: 아래 스크립트로 포터블 버전 설치(관리자 권한 불필요) / Linux: `apt install redis-server` / Docker: 4단계

## 설치 (새 PC에서 처음 한 번)

Git Bash에서:

```bash
git clone https://github.com/rkdahgus12/musicGEN.git
cd musicGEN

# 1) ACE-Step 1.5
git clone --depth 1 https://github.com/ACE-Step/ACE-Step-1.5.git
(cd ACE-Step-1.5 && uv sync)

# 2) 백엔드 / 프론트 의존성
(cd backend && uv sync)
(cd frontend && npm install)

# 3) Redis (Windows만)
bash scripts/setup_redis_windows.sh

# 4) 설정 — GPU VRAM에 맞게 모델 조합 수정
cp .env.example .env
```

### 모델 조합 (ACE-Step README 권장표)

| VRAM | DiT (`ACESTEP_CONFIG_PATH`) | LM (`ACESTEP_LM_MODEL_PATH`) | `ACESTEP_LM_BACKEND` | `MAX_DURATION` |
|------|-----|----|-----------|----|
| 6-8GB | acestep-v15-turbo | acestep-5Hz-lm-0.6B | pt | 480 |
| 8-12GB | acestep-v15-turbo | acestep-5Hz-lm-0.6B | vllm | 480 |
| 12-16GB | acestep-v15-turbo | acestep-5Hz-lm-1.7B | vllm | 480 |
| 16GB+ | turbo/sft 또는 XL | acestep-5Hz-lm-1.7B | vllm | 480 |

모델 가중치는 첫 생성 요청 때 자동 다운로드됩니다 (`ACE-Step-1.5/checkpoints`, 수 GB).
LM이 클수록 간단 모드가 설명을 더 잘 따릅니다.

## 실행

터미널 5개(Git Bash)에서 각각:

```bash
bash scripts/start_acestep.sh        # 1. ACE-Step API  :8001
bash scripts/start_redis_windows.sh  # 2. Redis         :6379  (Linux는 redis-server)
bash scripts/start_backend.sh        # 3. FastAPI       :8000  (문서: http://localhost:8000/docs)
bash scripts/start_worker.sh         # 4. RQ 워커 (1개만!)
bash scripts/start_frontend.sh       # 5. 웹 UI        :3000
```

브라우저에서 **http://localhost:3000** 접속.

### 테스트

```bash
python scripts/step1_test.py      # ACE-Step 직접 호출 (간단/커스텀 각 1곡)
python scripts/step2_test.py      # 백엔드 전체 흐름 (금지어/검증/큐/폴링/라이브러리)
(cd backend && uv run pytest -q)  # 단위 테스트
```

## 백엔드 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/songs` | 생성 요청 → `202` + `job_id` 즉시 반환 |
| GET | `/api/songs/{job_id}` | 상태 폴링: `queued`(대기) / `running`(생성중) / `succeeded`(완료) / `failed`(실패) |
| GET | `/api/songs` | 내 라이브러리 (최신순) |
| GET | `/api/songs/{id}/audio` | mp3 스트리밍, `?download=true`면 다운로드 |
| GET | `/api/health` | 상태 확인 |

요청 예시:

```jsonc
// 간단 모드: 한 줄 설명 → ACE-Step 내장 LM이 가사/스타일 생성
{"mode": "simple", "description": "비 오는 날 이별 발라드", "duration": 60, "bpm": 70, "key_scale": "A minor"}

// 커스텀 모드: 가사(구조 태그) + 스타일 태그 직접 입력
{"mode": "custom", "title": "여름밤", "style": "k-pop, synthpop, female vocal",
 "lyrics": "[verse]\n...\n[chorus]\n...", "bpm": 118, "duration": 45}
```

옵션(모두 선택): `duration`(10~MAX_DURATION초), `bpm`(30~300), `key_scale`("C major", "F# minor" 등), `time_signature`("2"/"3"/"4"/"6"), `vocal_language`(생략 시 자동 감지), `instrumental`.

### 동작 방식

- **간단 모드**: ACE-Step `/v1/create_sample`(내장 LM)로 가사·스타일·메타 생성 → 사용자 옵션으로 덮어쓰기 → `/release_task`로 생성. (`sample_query`로 한 번에 보내면 LM이 사용자 BPM/키/길이를 무시하기 때문)
- **커스텀 모드**: `/release_task`에 `thinking=true`, `use_cot_caption=false`(스타일을 LM이 바꾸지 않게)로 생성.
- **안전장치**: 설명/제목/스타일/가사에 `config/blocklist.txt` 단어가 있으면 `400` 차단. 모든 mp3에 ID3 태그 `AI_GENERATED=true`와 "AI generated" 주석, 옆에 `*.json` 메타(`"ai_generated": true`) 저장, DB에도 `ai_generated` 기록.
- **한 번에 1곡**: 워커 1개 + ACE-Step `ACESTEP_QUEUE_WORKERS=1`.
- **복구**: 워커 시작 시 중단된 `running` 작업은 실패 처리, 큐에서 사라진 `queued` 작업은 재등록.

## 웹 화면 (3단계)

- **만들기(/)**: 간단 모드(한 줄 설명 + 예시 버튼) / 커스텀 모드(제목, 스타일 태그, 구조 태그 가사), 옵션(길이, BPM, 키, 연주곡). 금지어·검증 오류는 폼 아래에 표시.
- **결과(/songs/[id])**: 2초마다 상태 폴링(대기 순번, 경과 시간) → 완료 시 파형 플레이어(wavesurfer.js), 가사(구조 태그 소제목), 메타 정보, 다운로드 버튼.
- **내 라이브러리(/library)**: 생성 이력, 바로 재생/다운로드. 진행 중인 곡이 있으면 자동 새로고침.
- LRC 가사 싱크는 ACE-Step REST API에서 타임스탬프를 제공하지 않아 현재는 가사만 표시합니다.

## 주의 / 알려진 문제

- `.env`에서 `ACESTEP_API_KEY=`처럼 **빈 값**을 두면 ACE-Step이 인증을 켭니다. 안 쓰면 줄을 주석 처리하세요.
- RTX 50 시리즈는 CUDA 12.8 PyTorch가 필요하며 ACE-Step `uv sync`가 자동 설치합니다.
- Windows에서는 RQ가 fork를 못 쓰므로 워커가 자동으로 `SimpleWorker`를 사용합니다. 코드를 고치면 워커를 재시작하세요.
- 0.6B LM은 간단 모드에서 설명의 장르를 잘 안 따르거나 한국어 가사를 로마자로 쓰는 경우가 있습니다. 한국어인데 한글이 없으면 최대 3번까지 다시 생성합니다.
- **exFAT 드라이브(외장 SSD 등)**에서는 Node의 readlink 버그로 Next.js 빌드가 실패해서 `frontend/exfat-readlink-fix.cjs`를 npm 스크립트에서 미리 불러옵니다. 다른 드라이브에서는 영향 없음.
- Git Bash의 `curl -d`로 한글을 보내면 깨집니다. 테스트는 `scripts/step2_test.py`나 `/docs`를 사용하세요.
