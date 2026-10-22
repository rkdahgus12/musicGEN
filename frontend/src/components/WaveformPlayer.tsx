"use client";

import { useEffect, useRef, useState } from "react";
import type WaveSurfer from "wavesurfer.js";
import { formatDuration } from "@/lib/api";

export default function WaveformPlayer({ src }: { src: string }) {
  const container = useRef<HTMLDivElement>(null);
  const ws = useRef<WaveSurfer | null>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [total, setTotal] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let destroyed = false;
    import("wavesurfer.js").then(({ default: WaveSurferLib }) => {
      if (destroyed || !container.current) return;
      const w = WaveSurferLib.create({
        container: container.current,
        url: src,
        height: 80,
        waveColor: "#52525b",
        progressColor: "#8b5cf6",
        cursorColor: "#c4b5fd",
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
      });
      w.on("ready", (d) => {
        setTotal(d);
        setReady(true);
      });
      w.on("timeupdate", setTime);
      w.on("play", () => setPlaying(true));
      w.on("pause", () => setPlaying(false));
      w.on("finish", () => setPlaying(false));
      ws.current = w;
    });
    return () => {
      destroyed = true;
      ws.current?.destroy();
      ws.current = null;
    };
  }, [src]);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div ref={container} className={ready ? "" : "animate-pulse"} />
      <div className="mt-3 flex items-center gap-4">
        <button
          type="button"
          onClick={() => ws.current?.playPause()}
          disabled={!ready}
          className="flex h-11 w-11 items-center justify-center rounded-full bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-40"
          aria-label={playing ? "일시정지" : "재생"}
        >
          {playing ? "❚❚" : "▶"}
        </button>
        <span className="font-mono text-sm text-zinc-400">
          {formatDuration(time) === "-" ? "0:00" : formatDuration(time)} / {formatDuration(total)}
        </span>
      </div>
    </div>
  );
}
