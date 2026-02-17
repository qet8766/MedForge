# syntax=docker/dockerfile:1
FROM python:3.12-slim@sha256:9e01bf1ae5db7649a236da7be1e94ffbbbdd7a93f867dd0d8d5720d9e1f89fab

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG UV_VERSION=0.8.22

WORKDIR /app

# ── 1. System packages (cached unless this block changes) ────────────
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && sed -i 's/^Components: .*/Components: main contrib non-free non-free-firmware/' \
       /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       curl ca-certificates kmod zfsutils-linux

# ── 2. Install uv (cached unless UV_VERSION changes) ─────────────────
RUN curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

# ── 3. Python deps (cached unless pyproject.toml or uv.lock change) ──
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --format requirements-txt --no-dev --frozen --no-emit-project \
      > /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# ── 4. Application source (changes frequently — cheap layer) ─────────
COPY . .

# ── 5. Non-root user with docker group ────────────────────────────────
ARG DOCKER_GID=999
RUN groupadd -g ${DOCKER_GID} docker || true \
    && useradd -r -m -s /bin/false -G docker medforge \
    && chown -R medforge:medforge /app

USER medforge

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
