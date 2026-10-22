import { SongStatus } from "@/lib/api";

const STYLES: Record<SongStatus, [string, string]> = {
  queued: ["대기", "bg-zinc-800 text-zinc-300"],
  running: ["생성중", "bg-violet-900/60 text-violet-200 animate-pulse"],
  succeeded: ["완료", "bg-emerald-900/60 text-emerald-200"],
  failed: ["실패", "bg-red-900/60 text-red-200"],
};

export default function StatusBadge({ status }: { status: SongStatus }) {
  const [label, cls] = STYLES[status];
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{label}</span>;
}
