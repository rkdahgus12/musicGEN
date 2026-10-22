"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, SongCreate } from "@/lib/api";

const EXAMPLES = ["비 오는 날 이별 발라드", "여름 바닷가 신나는 시티팝", "새벽 감성 로파이 힙합", "웅장한 판타지 게임 OST"];

const LYRICS_PLACEHOLDER = `[verse]
창밖에 비가 내리면
너의 목소리가 들려

[chorus]
안녕이라는 말 대신
조용히 우산을 접어`;

const KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

export default function CreatePage() {
  const router = useRouter();
  const [mode, setMode] = useState<"simple" | "custom">("simple");
  const [description, setDescription] = useState("");
  const [title, setTitle] = useState("");
  const [style, setStyle] = useState("");
  const [lyrics, setLyrics] = useState("");
  const [instrumental, setInstrumental] = useState(false);
  const [duration, setDuration] = useState("");
  const [bpm, setBpm] = useState("");
  const [keyNote, setKeyNote] = useState("");
  const [keyMode, setKeyMode] = useState("major");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const data: SongCreate =
      mode === "simple"
        ? { mode, description, instrumental }
        : { mode, title, style, lyrics: instrumental ? "" : lyrics, instrumental };
    if (duration) data.duration = Number(duration);
    if (bpm) data.bpm = Number(bpm);
    if (keyNote) data.key_scale = `${keyNote} ${keyMode}`;

    setSubmitting(true);
    try {
      const song = await api.create(data);
      router.push(`/songs/${song.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">노래 만들기</h1>
        <p className="mt-1 text-sm text-zinc-400">한 줄 설명만 쓰거나, 가사와 스타일을 직접 입력하세요.</p>
      </div>

      <div className="inline-flex rounded-lg border border-zinc-800 p-1">
        {(["simple", "custom"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded-md px-4 py-1.5 text-sm ${mode === m ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-zinc-100"}`}
          >
            {m === "simple" ? "간단 모드" : "커스텀 모드"}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="space-y-5">
        {mode === "simple" ? (
          <div>
            <label className="label" htmlFor="desc">
              어떤 노래를 원하세요?
            </label>
            <textarea
              id="desc"
              className="input h-24 resize-none"
              placeholder="예) 비 오는 날 이별 발라드, 피아노와 여성 보컬"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              required
            />
            <div className="mt-2 flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onClick={() => setDescription(ex)}
                  className="rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-400 hover:border-violet-500 hover:text-zinc-100"
                >
                  {ex}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-zinc-500">ACE-Step 내장 LM이 가사와 스타일을 자동으로 만듭니다.</p>
          </div>
        ) : (
          <>
            <div>
              <label className="label" htmlFor="title">
                제목 (선택)
              </label>
              <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={100} />
            </div>
            <div>
              <label className="label" htmlFor="style">
                스타일 태그 — 장르, 악기, 보컬, 분위기
              </label>
              <input
                id="style"
                className="input"
                placeholder="k-pop, synthpop, upbeat, bright female vocal, 80s synth"
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                maxLength={512}
                required
              />
            </div>
            {!instrumental && (
              <div>
                <label className="label" htmlFor="lyrics">
                  가사 — [verse], [chorus], [bridge] 같은 구조 태그 사용
                </label>
                <textarea
                  id="lyrics"
                  className="input h-56 font-mono"
                  placeholder={LYRICS_PLACEHOLDER}
                  value={lyrics}
                  onChange={(e) => setLyrics(e.target.value)}
                  maxLength={4000}
                  required
                />
              </div>
            )}
          </>
        )}

        <details className="rounded-lg border border-zinc-800 p-4" open={mode === "custom"}>
          <summary className="cursor-pointer text-sm font-medium text-zinc-300">옵션 (비워두면 자동)</summary>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className="label" htmlFor="duration">
                곡 길이 (초)
              </label>
              <input id="duration" type="number" min={10} max={480} className="input" placeholder="자동" value={duration} onChange={(e) => setDuration(e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="bpm">
                BPM
              </label>
              <input id="bpm" type="number" min={30} max={300} className="input" placeholder="자동" value={bpm} onChange={(e) => setBpm(e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="key">
                키
              </label>
              <select id="key" className="input" value={keyNote} onChange={(e) => setKeyNote(e.target.value)}>
                <option value="">자동</option>
                {KEYS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="keymode">
                장조/단조
              </label>
              <select id="keymode" className="input" value={keyMode} onChange={(e) => setKeyMode(e.target.value)} disabled={!keyNote}>
                <option value="major">major</option>
                <option value="minor">minor</option>
              </select>
            </div>
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm text-zinc-300">
            <input type="checkbox" checked={instrumental} onChange={(e) => setInstrumental(e.target.checked)} />
            연주곡 (보컬 없음)
          </label>
        </details>

        {error && <p className="rounded-lg border border-red-900 bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-violet-600 py-3 font-semibold text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {submitting ? "요청 중..." : "노래 생성"}
        </button>
      </form>
    </div>
  );
}
