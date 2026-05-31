#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
elif command -v sudo >/dev/null 2>&1; then
  SUDO="sudo -H env PATH=${PATH}"
else
  echo "This setup needs sudo when running as a non-root devcontainer user." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required. Rebuild this project through the Dev Containers extension or devcontainer CLI so the Node feature is applied." >&2
  exit 1
fi

${SUDO} python -m pip install --upgrade pip
${SUDO} python -m pip install -r .devcontainer/requirements-bootstrap.txt
${SUDO} npm install -g @angular/cli

primeng_mcp_dir="${HOME}/.codex/mcp/primeng"
context7_mcp_dir="${HOME}/.codex/mcp/context7"
codex_config="${HOME}/.codex/config.toml"

mkdir -p "${primeng_mcp_dir}" "${context7_mcp_dir}" "${HOME}/.codex"
cp .devcontainer/primeng-mcp-package.json "${primeng_mcp_dir}/package.json"
cp .devcontainer/context7-mcp-package.json "${context7_mcp_dir}/package.json"
npm install --prefix "${primeng_mcp_dir}"
npm install --prefix "${context7_mcp_dir}"
touch "${codex_config}"

tmp_codex_config="$(mktemp)"
awk '
  /^\[mcp_servers\.(primeng|prime-ng|context7)\]$/ { skip = 1; next }
  /^\[/ { skip = 0 }
  !skip { print }
' "${codex_config}" > "${tmp_codex_config}"
mv "${tmp_codex_config}" "${codex_config}"

{
  printf "\n[mcp_servers.context7]\n"
  printf "command = \"%s/node_modules/.bin/context7-mcp\"\n" "${context7_mcp_dir}"
  printf "enabled = true\n"
  printf "startup_timeout_sec = 30\n"
  printf "tool_timeout_sec = 60\n"
  printf "\n[mcp_servers.primeng]\n"
  printf "command = \"%s/node_modules/.bin/primeng-mcp\"\n" "${primeng_mcp_dir}"
  printf "enabled = true\n"
  printf "startup_timeout_sec = 30\n"
  printf "tool_timeout_sec = 60\n"
} >> "${codex_config}"

if [ -f backend/requirements.txt ]; then
  ${SUDO} python -m pip install -r backend/requirements.txt
fi

if [ -f backend/pyproject.toml ] || [ -f backend/setup.py ]; then
  ${SUDO} python -m pip install -e backend
fi

if ! command -v codex >/dev/null 2>&1; then
  curl -fsSL https://chatgpt.com/codex/install.sh | sh
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI installation completed, but codex is not available on PATH." >&2
  exit 1
fi
