# Next.js 프론트엔드 (standalone 출력). 빌드 컨텍스트: ./frontend
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# /api 프록시 대상은 빌드 시점에 고정됨
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL \
    NEXT_OUTPUT=standalone \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
