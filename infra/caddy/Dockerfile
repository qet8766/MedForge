# Build Caddy with the DNS challenge plugin.
# Replace caddy-dns/cloudflare with your provider's module if needed.
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/caddy-dns/cloudflare

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
