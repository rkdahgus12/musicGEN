import type { NextConfig } from "next";

// 브라우저는 같은 출처의 /api 로 요청 → Next 서버가 백엔드로 프록시 (CORS 불필요)
// Docker에서는 빌드 시 BACKEND_URL=http://backend:8000 지정
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Docker 이미지에서만 standalone 출력 사용 (로컬은 npm run dev / start)
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
