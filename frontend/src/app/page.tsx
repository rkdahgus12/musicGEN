"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Help } from "@/components/Controls";
import SettingsPanel, { MusicOptions } from "@/components/SettingsPanel";
import { Advanced, api, DEFAULT_ADVANCED, SongCreate } from "@/lib/api";

const EXAMPLES = ["비 오는 날 이별 발라드, 피아노와 여성 보컬", "여름 바닷가 신나는 시티팝", "새벽 감성 로파이 힙합", "웅장한 판타지 게임 OST"];

const STYLE_CHIPS: Record<string, string[]> = {
  장르: ["k-pop", "ballad", "hip hop", "r&b", "city pop", "lo-fi", "rock", "indie", "edm", "jazz", "acoustic folk", "trot"],
  분위기: ["emotional", "melancholic", "upbeat", "dreamy", "calm", "energetic", "dark", "romantic", "nostalgic"],
  악기: ["piano", "acoustic guitar", "electric guitar", "strings", "synthesizer", "808 bass", "drums", "saxophone"],
  보컬: ["female vocal", "male vocal", "breathy vocal", "powerful vocal", "duet", "choir"],
};

const STRUCTURE_TAGS = ["[intro]", "[verse]", "[pre-chorus]", "[chorus]", "[bridge]", "[outro]", "[instrumental]"];

const LYRICS_PLACEHOLDER = `[verse]
창밖에 비가 내리면
너의 목소리가 들려

[chorus]
안녕이라는 말 대신
조용히 우산을 접어`;

const DEFAULT_MUSIC: MusicOptions = {
  duration: null,
  bpm: null,
  keyNote: "",
  keyMode: "major",
  timeSignature: "",
  vocalLanguage: "",
  instrumental: false,
};

export default function Page() {
  return (
    <Suspense fallback={<p className="text-zinc-400">불러오는 중...</p>}>
      <CreatePage />
    </Suspense>
  );
}

function CreatePage() {
  const router = useRouter();
  const params = useSearchParams();
  const [mode, setMode] = useState<"simple" | "custom">("simple");
  const [description, setDescription] = useState("");
  const [title, setTitle] = useState("");
  const [style, setStyle] = useState("");
  const [lyrics, setLyrics] = useState("");
  const [music, setMusic] = useState<MusicOptions>(DEFAULT_MUSIC);
  const [adv, setAdv] = useState<Advanced>(DEFAULT_ADVANCED);
  const [lmQuery, setLmQuery] = useState(""); // 자동 변환 결과
  const [lmQueryEdit, setLmQueryEdit] = useState<string | null>(null); // 직접 수정한 값 (null = 자동)
  const [maxDuration, setMaxDuration] = useState(480);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const lyricsRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((h) => h.max_duration && setMaxDuration(h.max_duration))
      .catch(() => {});
  }, []);

  // ?from=<id> : 기존 곡 설정 불러오기, &seed=1 이면 그 곡의 시드까지 고정
  useEffect(() => {
    const from = params.get("from");
    if (!from) return;
    api
      .get(from)
      .then((s) => {
        const r = s.request;
        setMode(s.mode);
        setDescription(r.description ?? s.description);
        setTitle(r.title ?? "");
        // 커스텀 모드는 원래 입력, 간단 모드에서 "가사 편집"으로 넘어온 경우는 LM 결과를 커스텀으로
        if (params.get("as") === "custom") {
          setMode("custom");
          setTitle(s.title);
          setStyle(s.style);
          setLyrics(s.lyrics);
        } else {
          setStyle(r.style ?? "");
          setLyrics(r.lyrics ?? "");
        }
        setMusic({
          duration: r.duration ?? null,
          bpm: r.bpm ?? null,
          keyNote: r.key_scale ? r.key_scale.split(" ")[0] : "",
          keyMode: r.key_scale?.endsWith("minor") ? "minor" : "major",
          timeSignature: r.time_signature ?? "",
          vocalLanguage: r.vocal_language ?? "",
          instrumental: r.instrumental ?? false,
        });
        const a = { ...DEFAULT_ADVANCED, ...(r.advanced ?? {}) };
        if (params.get("seed") && s.seed !== null) a.seed = s.seed;
        setAdv(a);
        if (r.lm_query) setLmQueryEdit(r.lm_query);
        setNotice(`"${s.title}" 설정을 불러왔어요${params.get("seed") && s.seed !== null ? ` (시드 ${s.seed} 고정)` : ""}.`);
      })
      .catch(() => setError("불러올 곡을 찾지 못했습니다."));
  }, [params]);

  // 간단 모드: LM에 전달될 영어 키워드 미리보기 (입력 멈추고 0.4초 뒤)
  useEffect(() => {
    if (mode !== "simple" || !description.trim()) {
      setLmQuery("");
      return;
    }
    const t = setTimeout(() => {
      api
        .promptPreview(description, music.vocalLanguage)
        .then((r) => setLmQuery(r.lm_query))
        .catch(() => {});
    }, 400);
    return () => clearTimeout(t);
  }, [description, music.vocalLanguage, mode]);

  function toggleStyleTag(tag: string) {
    const tags = style
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const next = tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag];
    setStyle(next.join(", "));
  }

  function insertTag(tag: string) {
    const el = lyricsRef.current;
    if (!el) return setLyrics((l) => `${l}${l && !l.endsWith("\n") ? "\n" : ""}${tag}\n`);
    const { selectionStart: s, selectionEnd: e } = el;
    const before = lyrics.slice(0, s);
    const insert = `${before && !before.endsWith("\n") ? "\n" : ""}${tag}\n`;
    setLyrics(before + insert + lyrics.slice(e));
    requestAnimationFrame(() => {
      el.focus();
      el.selectionStart = el.selectionEnd = s + insert.length;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const data: SongCreate =
      mode === "simple"
        ? { mode, description, instrumental: music.instrumental, lm_query: lmQueryEdit ?? "" }
        : { mode, title, style, lyrics: music.instrumental ? "" : lyrics, instrumental: music.instrumental };
    if (music.duration !== null) data.duration = music.duration;
    if (music.bpm !== null) data.bpm = music.bpm;
    if (music.keyNote) data.key_scale = `${music.keyNote} ${music.keyMode}`;
    if (music.timeSignature) data.time_signature = music.timeSignature;
    if (music.vocalLanguage) data.vocal_language = music.vocalLanguage;
    data.advanced = adv;

    setSubmitting(true);
    try {
      const song = await api.create(data);
      router.push(`/songs/${song.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  const selectedTags = new Set(style.split(",").map((t) => t.trim()));

  return (
    <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-bold">노래 만들기</h1>
          <p className="mt-1 text-sm text-zinc-400">한 줄 설명만 쓰거나, 가사와 스타일을 직접 입력하세요.</p>
        </div>

        {notice && <p className="rounded-lg border border-violet-900 bg-violet-950/40 px-3 py-2 text-sm text-violet-200">{notice}</p>}

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

        {mode === "simple" ? (
          <div className="space-y-4">
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
              <p className="mt-2 text-xs text-zinc-500">장르·분위기·악기·보컬을 구체적으로 쓸수록 잘 따라요.</p>
            </div>

            {description.trim() && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-400">
                    LM에 전달될 설명
                    <Help text="내장 LM(0.6B)은 한국어 설명을 잘 이해하지 못해서, 음악 용어를 영어 키워드로 바꿔 전달합니다. 원하는 대로 직접 고칠 수도 있어요." />
                  </span>
                  {lmQueryEdit === null ? (
                    <button type="button" onClick={() => setLmQueryEdit(lmQuery)} className="text-xs text-violet-400 hover:underline">
                      직접 수정
                    </button>
                  ) : (
                    <button type="button" onClick={() => setLmQueryEdit(null)} className="text-xs text-zinc-500 hover:underline">
                      자동으로 되돌리기
                    </button>
                  )}
                </div>
                {lmQueryEdit === null ? (
                  <p className="font-mono text-sm text-zinc-200">{lmQuery || "…"}</p>
                ) : (
                  <input
                    className="input font-mono"
                    value={lmQueryEdit}
                    onChange={(e) => setLmQueryEdit(e.target.value)}
                    maxLength={500}
                    placeholder="english keywords, genre, mood, instruments, vocal"
                  />
                )}
                {lmQuery && lmQuery === description.trim() && /[가-힣]/.test(lmQuery) && lmQueryEdit === null && (
                  <p className="mt-2 text-xs text-amber-400">아는 음악 용어가 없어 원문 그대로 전달돼요. 장르나 악기를 넣거나 영어로 직접 써 주세요.</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="label" htmlFor="title">
                제목 (선택)
              </label>
              <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={100} />
            </div>
            <div>
              <label className="label" htmlFor="style">
                스타일 태그 — 영어로, 쉼표로 구분
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
              <div className="mt-3 space-y-2">
                {Object.entries(STYLE_CHIPS).map(([group, tags]) => (
                  <div key={group} className="flex flex-wrap items-center gap-1.5">
                    <span className="w-12 shrink-0 text-[11px] text-zinc-500">{group}</span>
                    {tags.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => toggleStyleTag(t)}
                        className={`rounded-full border px-2.5 py-0.5 text-xs ${
                          selectedTags.has(t)
                            ? "border-violet-500 bg-violet-600/20 text-violet-200"
                            : "border-zinc-800 text-zinc-400 hover:border-zinc-600 hover:text-zinc-100"
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
            {!music.instrumental && (
              <div>
                <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                  <label className="label mb-0" htmlFor="lyrics">
                    가사
                  </label>
                  <div className="flex flex-wrap gap-1">
                    {STRUCTURE_TAGS.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => insertTag(t)}
                        className="rounded border border-zinc-800 px-1.5 py-0.5 font-mono text-[11px] text-zinc-400 hover:border-violet-500 hover:text-zinc-100"
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  id="lyrics"
                  ref={lyricsRef}
                  className="input h-72 font-mono leading-relaxed"
                  placeholder={LYRICS_PLACEHOLDER}
                  value={lyrics}
                  onChange={(e) => setLyrics(e.target.value)}
                  maxLength={4000}
                  required
                />
                <p className="mt-1 text-right text-[11px] text-zinc-600">{lyrics.length} / 4000</p>
              </div>
            )}
          </div>
        )}

        {error && <p className="rounded-lg border border-red-900 bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-violet-600 py-3 font-semibold text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {submitting ? "요청 중..." : "🎵 노래 생성"}
        </button>
      </div>

      <aside className="lg:sticky lg:top-20 lg:self-start">
        <SettingsPanel mode={mode} music={music} setMusic={setMusic} adv={adv} setAdv={setAdv} maxDuration={maxDuration} />
      </aside>
    </form>
  );
}
