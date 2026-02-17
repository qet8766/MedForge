# ── Build stage ────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY . .

# Build-time public env values must be present for client-side API routing.
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_DOMAIN=""
ARG DOMAIN=""
ENV NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL}"
ENV NEXT_PUBLIC_DOMAIN="${NEXT_PUBLIC_DOMAIN}"
ENV DOMAIN="${DOMAIN}"

RUN npm run build

# ── Runtime stage ─────────────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN addgroup --system --gid 1001 nextjs \
    && adduser --system --uid 1001 nextjs

# Copy standalone output from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
