FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG UV_VERSION=0.8.22

WORKDIR /app

COPY . .

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && uv pip install --system --no-cache-dir . \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user with docker group for container management.
# The docker GID must match the host's docker group (typically 999).
ARG DOCKER_GID=999
RUN groupadd -g ${DOCKER_GID} docker || true \
    && useradd -r -m -s /bin/false -G docker medforge \
    && chown -R medforge:medforge /app

USER medforge

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
