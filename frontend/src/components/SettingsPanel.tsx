"use client";

import { Advanced, matchPreset, PresetName, PRESETS } from "@/lib/api";
import { Help, OptionalSlider, Section, Segmented, Slider, Toggle } from "./Controls";

export interface MusicOptions {
  duration: number | null;
  bpm: number | null;
  keyNote: string; // "" = 자동
  keyMode: "major" | "minor";
  timeSignature: string; // "" = 자동
  vocalLanguage: string; // "" = 자동 감지
  instrumental: boolean;
}

const KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const LANGS = [
  ["", "자동 감지"],
  ["ko", "한국어"],
  ["en", "영어"],
  ["ja", "일본어"],
  ["zh", "중국어"],
  ["es", "스페인어"],
];

const fmtSec = (v: number) => `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`;

interface Props {
  mode: "simple" | "custom";
  music: MusicOptions;
  setMusic: (m: MusicOptions) => void;
  adv: Advanced;
  setAdv: (a: Advanced) => void;
  maxDuration: number;
}

export default function SettingsPanel({ mode, music, setMusic, adv, setAdv, maxDuration }: Props) {
  const m = (patch: Partial<MusicOptions>) => setMusic({ ...music, ...patch });
  const a = (patch: Partial<Advanced>) => setAdv({ ...adv, ...patch });
  const preset = matchPreset(adv);

  return (
    <div className="space-y-3">
      <Section title="🎵 음악 옵션">
        <OptionalSlider
          label="곡 길이"
          help="10초 ~ 최대 길이. 길수록 생성 시간이 늘어납니다."
          value={music.duration}
          defaultValue={60}
          min={10}
          max={maxDuration}
          step={5}
          format={fmtSec}
          onChange={(v) => m({ duration: v })}
        />
        <OptionalSlider
          label="BPM (템포)"
          help="발라드 60~80, 팝 100~120, 댄스 120~130, 힙합 85~100 정도가 일반적"
          value={music.bpm}
          defaultValue={100}
          min={40}
          max={200}
          step={1}
          hints={["느림", "빠름"]}
          onChange={(v) => m({ bpm: v })}
        />
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="label">
              키<Help text="minor(단조)는 슬프고 어두운 느낌, major(장조)는 밝은 느낌" />
            </label>
            <select className="input" value={music.keyNote} onChange={(e) => m({ keyNote: e.target.value })}>
              <option value="">자동</option>
              {KEYS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">장조/단조</label>
            <select
              className="input"
              value={music.keyMode}
              disabled={!music.keyNote}
              onChange={(e) => m({ keyMode: e.target.value as "major" | "minor" })}
            >
              <option value="major">major (장조)</option>
              <option value="minor">minor (단조)</option>
            </select>
          </div>
          <div>
            <label className="label">박자</label>
            <select className="input" value={music.timeSignature} onChange={(e) => m({ timeSignature: e.target.value })}>
              <option value="">자동</option>
              <option value="4">4/4</option>
              <option value="3">3/4 (왈츠)</option>
              <option value="6">6/8</option>
              <option value="2">2/4</option>
            </select>
          </div>
          <div>
            <label className="label">보컬 언어</label>
            <select className="input" value={music.vocalLanguage} onChange={(e) => m({ vocalLanguage: e.target.value })}>
              {LANGS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Toggle label="연주곡 (보컬 없음)" checked={music.instrumental} onChange={(v) => m({ instrumental: v })} />
      </Section>

      <Section title="✨ 품질 프리셋">
        <Segmented<PresetName>
          options={(Object.keys(PRESETS) as PresetName[]).map((k) => ({ value: k, label: PRESETS[k].label }))}
          value={preset}
          onChange={(p) => a(PRESETS[p].values)}
        />
        <p className="text-xs text-zinc-500">{preset ? PRESETS[preset].desc : "사용자 지정 설정"}</p>
      </Section>

      <Section title="⚙️ 고급 설정" defaultOpen={false}>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-violet-400">LM (작곡·작사 계획)</p>
        <Slider
          label="창의성 (temperature)"
          help="낮으면 무난하고 일관된 결과, 높으면 과감하지만 엉뚱해질 수 있음. 간단 모드의 가사·스타일 작성에도 적용"
          value={adv.lm_temperature}
          min={0.1}
          max={1.5}
          step={0.05}
          format={(v) => v.toFixed(2)}
          hints={["보수적", "과감"]}
          onChange={(v) => a({ lm_temperature: v })}
        />
        <Slider
          label="설명 충실도 (LM CFG)"
          help="높을수록 스타일/가사 지시를 강하게 따름. 너무 높으면 부자연스러울 수 있음"
          value={adv.lm_cfg_scale}
          min={1}
          max={5}
          step={0.1}
          format={(v) => v.toFixed(1)}
          hints={["자유롭게", "충실하게"]}
          onChange={(v) => a({ lm_cfg_scale: v })}
        />
        <Slider
          label="top-p"
          help="확률 상위 p만큼의 후보에서만 고름. 낮을수록 안전한 선택"
          value={adv.lm_top_p}
          min={0.5}
          max={1}
          step={0.01}
          format={(v) => v.toFixed(2)}
          onChange={(v) => a({ lm_top_p: v })}
        />
        <Slider
          label="top-k"
          help="상위 k개 후보에서만 고름. 0이면 끔. 보통 40~100"
          value={adv.lm_top_k}
          min={0}
          max={200}
          step={5}
          format={(v) => (v === 0 ? "끔" : String(v))}
          onChange={(v) => a({ lm_top_k: v })}
        />
        <Slider
          label="반복 억제"
          help="1.0은 끔. 높이면 같은 구절 반복이 줄지만 노래다운 반복(후렴)도 줄어듦"
          value={adv.lm_repetition_penalty}
          min={1}
          max={1.5}
          step={0.01}
          format={(v) => v.toFixed(2)}
          onChange={(v) => a({ lm_repetition_penalty: v })}
        />
        <div>
          <label className="label">
            네거티브 프롬프트
            <Help text="LM이 피했으면 하는 특징 (예: 'j-pop, anime, children song'). 기본값 'NO USER INPUT'" />
          </label>
          <input className="input" value={adv.lm_negative_prompt} onChange={(e) => a({ lm_negative_prompt: e.target.value })} maxLength={300} />
        </div>
        <Toggle
          label="LM 사고(thinking)"
          help="LM이 곡 구조(오디오 코드)를 먼저 계획한 뒤 생성. 끄면 빠르지만 구성이 단조로워질 수 있음"
          checked={adv.thinking}
          onChange={(v) => a({ thinking: v })}
        />
        {mode === "custom" && (
          <Toggle
            label="스타일 보강"
            help="입력한 스타일 태그를 LM이 자세한 영어 설명으로 다시 써서 생성. 짧은 태그만 쓸 때 유용"
            checked={adv.enhance_style}
            onChange={(v) => a({ enhance_style: v })}
          />
        )}

        <p className="pt-2 text-[11px] font-semibold uppercase tracking-wider text-violet-400">DiT (오디오 생성)</p>
        <Slider
          label="생성 단계 (steps)"
          help="turbo 모델 권장 8. 늘리면 디테일이 조금 좋아질 수 있지만 느려짐"
          value={adv.inference_steps}
          min={1}
          max={20}
          step={1}
          hints={["빠름", "정밀"]}
          onChange={(v) => a({ inference_steps: v })}
        />
        <Slider
          label="shift"
          help="노이즈 제거 일정 조절. turbo 권장 3.0"
          value={adv.shift}
          min={1}
          max={5}
          step={0.1}
          format={(v) => v.toFixed(1)}
          onChange={(v) => a({ shift: v })}
        />
        <div>
          <label className="label">
            샘플링 방식
            <Help text="ODE: 빠르고 결정적(같은 시드 = 같은 결과). SDE: 확률적, 같은 시드여도 매번 조금씩 다름" />
          </label>
          <Segmented<"ode" | "sde">
            options={[
              { value: "ode", label: "ODE (결정적)" },
              { value: "sde", label: "SDE (확률적)" },
            ]}
            value={adv.infer_method}
            onChange={(v) => a({ infer_method: v })}
          />
        </div>
        <div>
          <label className="label">
            시드
            <Help text="같은 시드 + 같은 설정이면 같은 곡이 나옴(ODE 기준). 마음에 든 곡을 조금씩 바꿔볼 때 고정" />
          </label>
          <div className="flex gap-2">
            <input
              className="input font-mono"
              type="number"
              min={0}
              placeholder="랜덤"
              value={adv.seed ?? ""}
              onChange={(e) => a({ seed: e.target.value === "" ? null : Math.max(0, Math.floor(Number(e.target.value))) })}
            />
            <button
              type="button"
              onClick={() => a({ seed: Math.floor(Math.random() * 2 ** 31) })}
              className="shrink-0 rounded-lg border border-zinc-700 px-3 text-sm hover:border-violet-500"
              title="랜덤 시드 고정"
            >
              🎲
            </button>
            {adv.seed !== null && (
              <button type="button" onClick={() => a({ seed: null })} className="shrink-0 text-xs text-zinc-500 hover:text-zinc-200">
                해제
              </button>
            )}
          </div>
        </div>
      </Section>
    </div>
  );
}
