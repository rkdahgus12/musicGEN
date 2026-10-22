// ACE-Step 가사 표시: [verse] 같은 구조 태그는 소제목으로, 줄 앞의 [ko] 같은 언어 태그는 제거
export default function LyricsView({ lyrics }: { lyrics: string }) {
  if (!lyrics.trim()) return <p className="text-sm text-zinc-500">가사 없음 (연주곡)</p>;

  const lines = lyrics.split("\n").map((l) => l.replace(/^\[[a-z]{2}\]\s*/i, ""));
  return (
    <div className="space-y-1 text-sm leading-relaxed">
      {lines.map((line, i) => {
        const tag = line.trim().match(/^\[(.+)\]$/);
        if (tag) {
          return (
            <p key={i} className="pt-3 text-xs font-semibold uppercase tracking-wider text-violet-400 first:pt-0">
              {tag[1]}
            </p>
          );
        }
        return line.trim() ? (
          <p key={i} className="text-zinc-200">
            {line}
          </p>
        ) : null;
      })}
    </div>
  );
}
