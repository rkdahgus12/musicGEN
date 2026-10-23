export type SongStatus = "queued" | "running" | "succeeded" | "failed";

export interface Song {
  id: string;
  job_id: string;
  mode: "simple" | "custom";
  status: SongStatus;
  title: string;
  description: string;
  style: string;
  lyrics: string;
  vocal_language: string;
  bpm: number | null;
  key_scale: string;
  time_signature: string;
  duration: number | null;
  error: string;
  ai_generated: boolean;
  audio_url: string | null;
  queue_position: number | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  request: Partial<SongCreate>;
  lm_query: string;
  seed: number | null;
}

export interface Advanced {
  lm_temperature: number;
  lm_cfg_scale: number;
  lm_top_p: number;
  lm_top_k: number;
  lm_repetition_penalty: number;
  lm_negative_prompt: string;
  thinking: boolean;
  enhance_style: boolean;
  inference_steps: number;
  shift: number;
  infer_method: "ode" | "sde";
  seed: number | null;
}

// 백엔드 schemas.Advanced 기본값과 동일 (= "균형" 프리셋)
export const DEFAULT_ADVANCED: Advanced = {
  lm_temperature: 0.85,
  lm_cfg_scale: 2.5,
  lm_top_p: 0.9,
  lm_top_k: 0,
  lm_repetition_penalty: 1.0,
  lm_negative_prompt: "NO USER INPUT",
  thinking: true,
  enhance_style: false,
  inference_steps: 8,
  shift: 3.0,
  infer_method: "ode",
  seed: null,
};

export type PresetName = "stable" | "balanced" | "creative";

export const PRESETS: Record<PresetName, { label: string; desc: string; values: Partial<Advanced> }> = {
  stable: {
    label: "안정적",
    desc: "LM이 보수적으로 작곡, 생성 단계 12. 설명을 충실히 따르고 결과가 고름",
    values: { lm_temperature: 0.6, lm_cfg_scale: 3.0, lm_top_p: 0.85, inference_steps: 12, infer_method: "ode" },
  },
  balanced: {
    label: "균형",
    desc: "기본값. 속도와 품질의 균형",
    values: { lm_temperature: 0.85, lm_cfg_scale: 2.5, lm_top_p: 0.9, inference_steps: 8, infer_method: "ode" },
  },
  creative: {
    label: "창의적",
    desc: "LM이 과감하게 작곡하고 확률적 샘플링(SDE). 매번 결과가 크게 달라짐",
    values: { lm_temperature: 1.05, lm_cfg_scale: 2.0, lm_top_p: 0.95, inference_steps: 8, infer_method: "sde" },
  },
};

export function matchPreset(a: Advanced): PresetName | null {
  for (const [name, p] of Object.entries(PRESETS) as [PresetName, (typeof PRESETS)[PresetName]][]) {
    if (Object.entries(p.values).every(([k, v]) => a[k as keyof Advanced] === v)) return name;
  }
  return null;
}

export interface SongCreate {
  mode: "simple" | "custom";
  description?: string;
  title?: string;
  style?: string;
  lyrics?: string;
  instrumental?: boolean;
  duration?: number;
  bpm?: number;
  key_scale?: string;
  time_signature?: string;
  vocal_language?: string;
  lm_query?: string;
  advanced?: Advanced;
}

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorMessage(res.status, body));
  return body as T;
}

function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const d = detail as { message?: string; terms?: string[] };
    return d.terms?.length ? `${d.message} (${d.terms.join(", ")})` : d.message ?? `오류 ${status}`;
  }
  if (Array.isArray(detail)) {
    // FastAPI 검증 오류
    return detail.map((e: { msg: string }) => e.msg.replace(/^Value error, /, "")).join(" / ");
  }
  if (typeof detail === "string") return detail;
  return `서버 오류 (${status})`;
}

export const api = {
  create: (data: SongCreate) => request<Song>("/api/songs", { method: "POST", body: JSON.stringify(data) }),
  get: (id: string) => request<Song>(`/api/songs/${id}`),
  list: () => request<Song[]>("/api/songs?limit=100"),
  promptPreview: (description: string, vocal_language?: string) =>
    request<{ lm_query: string; vocal_language: string }>("/api/prompt-preview", {
      method: "POST",
      body: JSON.stringify({ description, vocal_language: vocal_language || null }),
    }),
};

export const isPending = (s: Song) => s.status === "queued" || s.status === "running";

export function formatDuration(sec: number | null | undefined): string {
  if (!sec) return "-";
  const s = Math.round(sec);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
