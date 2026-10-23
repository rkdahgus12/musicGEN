"use client";

import { useState } from "react";

export function Help({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setOpen(false)}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-zinc-700 text-[10px] text-zinc-500 hover:border-violet-500 hover:text-zinc-200"
        aria-label="설명"
      >
        ?
      </button>
      {open && (
        <span className="absolute left-0 top-5 z-20 w-60 rounded-lg border border-zinc-700 bg-zinc-900 p-2 text-xs font-normal leading-relaxed text-zinc-300 shadow-xl">
          {text}
        </span>
      )}
    </span>
  );
}

interface SliderProps {
  label: string;
  help?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  format?: (v: number) => string;
  hints?: [string, string]; // 왼쪽/오른쪽 끝 설명
}

export function Slider({ label, help, value, min, max, step, onChange, format, hints }: SliderProps) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="font-medium text-zinc-400">
          {label}
          {help && <Help text={help} />}
        </span>
        <span className="font-mono text-zinc-200">{format ? format(value) : value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-violet-500"
      />
      {hints && (
        <div className="flex justify-between text-[10px] text-zinc-600">
          <span>{hints[0]}</span>
          <span>{hints[1]}</span>
        </div>
      )}
    </div>
  );
}

/** "자동" 체크를 끄면 슬라이더로 값을 지정 (null = 자동) */
export function OptionalSlider(props: Omit<SliderProps, "value" | "onChange"> & {
  value: number | null;
  defaultValue: number;
  onChange: (v: number | null) => void;
}) {
  const { value, defaultValue, onChange, ...rest } = props;
  const auto = value === null;
  return (
    <div>
      <div className={auto ? "pointer-events-none opacity-40" : ""}>
        <Slider {...rest} value={value ?? defaultValue} onChange={onChange} format={auto ? () => "자동" : rest.format} />
      </div>
      <label className="mt-1 flex items-center gap-1.5 text-[11px] text-zinc-500">
        <input type="checkbox" checked={auto} onChange={(e) => onChange(e.target.checked ? null : defaultValue)} />
        자동 (LM이 결정)
      </label>
    </div>
  );
}

export function Toggle({ label, help, checked, onChange }: { label: string; help?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 text-xs">
      <span className="font-medium text-zinc-400">
        {label}
        {help && <Help text={help} />}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 shrink-0 rounded-full transition ${checked ? "bg-violet-600" : "bg-zinc-700"}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${checked ? "left-4.5" : "left-0.5"}`} />
      </button>
    </label>
  );
}

export function Segmented<T extends string>({ options, value, onChange }: { options: { value: T; label: string }[]; value: T | null; onChange: (v: T) => void }) {
  return (
    <div className="grid rounded-lg border border-zinc-800 p-1" style={{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`rounded-md px-2 py-1.5 text-xs ${value === o.value ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-zinc-100"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  return (
    <details open={defaultOpen} className="group rounded-xl border border-zinc-800 bg-zinc-900/40">
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-zinc-200">
        {title}
        <span className="text-zinc-500 transition group-open:rotate-180">▾</span>
      </summary>
      <div className="space-y-4 border-t border-zinc-800 px-4 py-4">{children}</div>
    </details>
  );
}
