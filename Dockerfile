FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       coreutils \
       git \
       nodejs \
       npm \
       python3 \
       python3-pip \
       ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /bin/bash agent

WORKDIR /work
USER agent

CMD ["sleep", "infinity"]
