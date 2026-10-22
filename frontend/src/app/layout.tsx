import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "musicGEN",
  description: "ACE-Step 1.5 기반 AI 노래 생성",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        <header className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
          <nav className="mx-auto flex max-w-4xl items-center gap-6 px-4 py-3">
            <Link href="/" className="text-lg font-bold tracking-tight">
              <span className="text-violet-400">♪</span> musicGEN
            </Link>
            <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-100">
              만들기
            </Link>
            <Link href="/library" className="text-sm text-zinc-400 hover:text-zinc-100">
              내 라이브러리
            </Link>
          </nav>
        </header>
        <main className="mx-auto max-w-4xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-4xl px-4 pb-8 text-xs text-zinc-600">
          모든 결과물은 AI로 생성되었습니다 (ACE-Step 1.5). 실존 가수 이름·곡 제목은 사용할 수 없습니다.
        </footer>
      </body>
    </html>
  );
}
