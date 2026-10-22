"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import { api, formatDuration, isPending, Song } from "@/lib/api";

export default function LibraryPage() {
  const [songs, setSongs] = useState<Song[] | null>(null);
  const [error, setError] = useState("");
  const [playing, setPlaying] = useState<string | null>(null);

  // 진행 중인 곡이 있으면 주기적으로 새로고침
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;
    const load = async () => {
      try {
        const list = await api.list();
        if (stopped) return;
        setSongs(list);
        setError("");
        if (list.some(isPending)) timer = setTimeout(load, 3000);
      } catch (err) {
        if (!stopped) setError(err instanceof Error ? err.message : String(err));
      }
    };
    load();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <h1 className="text-2xl font-bold">내 라이브러리</h1>
        {songs && <span className="text-sm text-zinc-500">{songs.length}곡</span>}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {!songs && !error && <p className="text-zinc-400">불러오는 중...</p>}
      {songs?.length === 0 && (
        <p className="text-zinc-400">
          아직 만든 노래가 없어요.{" "}
          <Link href="/" className="text-violet-400 hover:underline">
            첫 노래 만들기
          </Link>
        </p>
      )}

      <ul className="divide-y divide-zinc-800 rounded-xl border border-zinc-800">
        {songs?.map((s) => (
          <li key={s.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <StatusBadge status={s.status} />
                <Link href={`/songs/${s.id}`} className="truncate font-medium hover:text-violet-300">
                  {s.title || "제목 없음"}
                </Link>
              </div>
              <p className="mt-1 truncate text-xs text-zinc-500">
                {s.mode === "simple" ? "간단" : "커스텀"} · {formatDuration(s.duration)} · {s.bpm ?? "-"} BPM ·{" "}
                {s.key_scale || "-"} · {new Date(s.created_at).toLocaleString("ko-KR")}
              </p>
            </div>
            {s.status === "succeeded" && s.audio_url && (
              <div className="flex items-center gap-2">
                {playing === s.id ? (
                  <audio src={s.audio_url} controls autoPlay className="h-9 w-64" onEnded={() => setPlaying(null)} />
                ) : (
                  <button
                    type="button"
                    onClick={() => setPlaying(s.id)}
                    className="rounded-full bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-500"
                  >
                    ▶ 재생
                  </button>
                )}
                <a
                  href={`${s.audio_url}?download=true`}
                  className="rounded-full border border-zinc-700 px-3 py-1.5 text-xs hover:border-violet-500"
                >
                  ⬇
                </a>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
