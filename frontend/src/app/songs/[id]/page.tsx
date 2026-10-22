"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import LyricsView from "@/components/LyricsView";
import StatusBadge from "@/components/StatusBadge";
import WaveformPlayer from "@/components/WaveformPlayer";
import { api, formatDuration, isPending, Song } from "@/lib/api";

const POLL_MS = 2000;

export default function SongPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [song, setSong] = useState<Song | null>(null);
  const [error, setError] = useState("");
  const [now, setNow] = useState(() => Date.now());

  // 대기/생성중이면 폴링
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;
    const tick = async () => {
      try {
        const s = await api.get(id);
        if (stopped) return;
        setSong(s);
        setError("");
        if (isPending(s)) timer = setTimeout(tick, POLL_MS);
      } catch (err) {
        if (stopped) return;
        setError(err instanceof Error ? err.message : String(err));
        timer = setTimeout(tick, POLL_MS * 2);
      }
    };
    tick();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  // 경과 시간 표시용
  useEffect(() => {
    if (!song || !isPending(song)) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [song]);

  if (!song) {
    return <p className="text-zinc-400">{error || "불러오는 중..."}</p>;
  }

  const startedAt = new Date(song.started_at ?? song.created_at).getTime();
  const elapsed = Math.max(0, Math.round((now - startedAt) / 1000));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <StatusBadge status={song.status} />
            <span className="text-xs text-zinc-500">{song.mode === "simple" ? "간단 모드" : "커스텀 모드"}</span>
            <span className="rounded border border-zinc-700 px-1.5 text-[10px] text-zinc-400">AI generated</span>
          </div>
          <h1 className="mt-2 truncate text-2xl font-bold">{song.title || "제목 없음"}</h1>
          {song.description && <p className="mt-1 text-sm text-zinc-400">“{song.description}”</p>}
        </div>
        {song.status === "succeeded" && song.audio_url && (
          <a
            href={`${song.audio_url}?download=true`}
            className="shrink-0 rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:border-violet-500"
          >
            ⬇ 다운로드
          </a>
        )}
      </div>

      {isPending(song) && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-zinc-700 border-t-violet-500" />
          {song.status === "queued" ? (
            <p className="text-zinc-300">
              대기 중{song.queue_position ? ` — 앞에 ${song.queue_position - 1}곡` : ""}
            </p>
          ) : (
            <p className="text-zinc-300">
              {song.mode === "simple" && !song.style ? "가사와 스타일을 만드는 중" : "노래를 생성하는 중"}… {elapsed}초
            </p>
          )}
          <p className="mt-2 text-xs text-zinc-500">GPU 1장에서 한 곡씩 만들어요. 보통 20초~3분 걸립니다.</p>
        </div>
      )}

      {song.status === "failed" && (
        <div className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          생성에 실패했습니다: {song.error || "알 수 없는 오류"}
        </div>
      )}

      {song.status === "succeeded" && song.audio_url && <WaveformPlayer src={song.audio_url} />}

      <div className="grid gap-6 md:grid-cols-[1fr_16rem]">
        <section className="rounded-xl border border-zinc-800 p-5">
          <h2 className="mb-3 text-sm font-semibold text-zinc-400">가사</h2>
          {song.lyrics || !isPending(song) ? (
            <LyricsView lyrics={song.lyrics} />
          ) : (
            <p className="text-sm text-zinc-500">LM이 가사를 쓰는 중...</p>
          )}
        </section>
        <aside className="space-y-4 rounded-xl border border-zinc-800 p-5 text-sm">
          <Meta label="스타일" value={song.style || "-"} />
          <Meta label="길이" value={formatDuration(song.duration)} />
          <Meta label="BPM" value={song.bpm ? String(song.bpm) : "-"} />
          <Meta label="키" value={song.key_scale || "-"} />
          <Meta label="언어" value={song.vocal_language || "-"} />
          <Meta label="생성 시각" value={new Date(song.created_at).toLocaleString("ko-KR")} />
        </aside>
      </div>

      <div className="flex gap-4 text-sm">
        <Link href="/" className="text-violet-400 hover:underline">
          + 새 노래 만들기
        </Link>
        <Link href="/library" className="text-zinc-400 hover:underline">
          내 라이브러리
        </Link>
      </div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-0.5 break-words text-zinc-200">{value}</div>
    </div>
  );
}
