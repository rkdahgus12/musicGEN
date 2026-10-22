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
};

export const isPending = (s: Song) => s.status === "queued" || s.status === "running";

export function formatDuration(sec: number | null | undefined): string {
  if (!sec) return "-";
  const s = Math.round(sec);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
