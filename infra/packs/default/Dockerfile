FROM nvidia/cuda:13.1.1-runtime-ubuntu24.04

ARG CODE_SERVER_VERSION=4.96.4
ARG USER_UID=1000
ARG USER_GID=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates git wget \
        python3 python3-pip python3-venv \
    && curl -fsSL https://code-server.dev/install.sh | sh -s -- --version=${CODE_SERVER_VERSION} \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${USER_GID} coder \
    && useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash coder \
    && mkdir -p /workspace && chown coder:coder /workspace

USER coder
WORKDIR /workspace
EXPOSE 8080

ENTRYPOINT ["code-server", "--auth", "none", "--bind-addr", "0.0.0.0:8080", "--disable-telemetry", "/workspace"]
