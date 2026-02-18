FROM nvidia/cuda:13.1.1-runtime-ubuntu24.04

ARG USER_UID=1000
ARG USER_GID=1000
ARG UV_VERSION=0.10.2
ARG INSTALL_EXTRAS=false

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}"

COPY basic.in /tmp/pack/basic.in
COPY extras.in /tmp/pack/extras.in

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates git git-lfs wget unzip \
        python3 python3-venv \
        build-essential python3-dev pkg-config \
        less openssh-client openssh-server jq htop tmux \
        libfontconfig1 fonts-dejavu-core \
    && git lfs install \
    && curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh \
    && install -m 0755 /root/.local/bin/uv /usr/local/bin/uv \
    && install -m 0755 /root/.local/bin/uvx /usr/local/bin/uvx \
    && uv venv ${VIRTUAL_ENV} \
    && uv pip install --python ${VIRTUAL_ENV}/bin/python --no-cache-dir -r /tmp/pack/basic.in \
    && if [ "${INSTALL_EXTRAS}" = "true" ]; then uv pip install --python ${VIRTUAL_ENV}/bin/python --no-cache-dir -r /tmp/pack/extras.in; fi \
    && rm -rf /tmp/pack \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd -o -g ${USER_GID} coder || true \
    && useradd -o -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash coder || true \
    && mkdir -p /workspace && chown ${USER_UID}:${USER_GID} /workspace \
    && mkdir -p /run/sshd

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

WORKDIR /workspace
EXPOSE 22

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
