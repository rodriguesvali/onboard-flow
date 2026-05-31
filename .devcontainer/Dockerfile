FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends bubblewrap \
    && rm -rf /var/lib/apt/lists/*

# Rootless Docker can expose bind-mounted workspace files as root:root.
RUN usermod -aG root vscode

WORKDIR /workspace/onboard-flow
