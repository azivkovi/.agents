#!/usr/bin/env sh
# Playwright MCP server (stdio) for browser automation.
#
# Uses the system Chromium by default, so no Playwright browser download is
# needed. Behaviour can be tuned from the gitignored .env at the repo root:
#
#   PLAYWRIGHT_MCP_EXECUTABLE  browser binary to use (default /usr/bin/chromium)
#   PLAYWRIGHT_MCP_HEADLESS    0 to show a visible window (default 1, headless)
#   PLAYWRIGHT_MCP_ISOLATED    1 to keep the profile in memory (default 0,
#                              profile persists, so logins survive restarts)
#   PLAYWRIGHT_MCP_VIEWPORT    viewport size, e.g. 1280,720
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$SCRIPT_DIR/../.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

set -- -y @playwright/mcp@latest

EXECUTABLE="${PLAYWRIGHT_MCP_EXECUTABLE:-}"
if [ -z "$EXECUTABLE" ] && [ -x /usr/bin/chromium ]; then
  EXECUTABLE=/usr/bin/chromium
fi
if [ -n "$EXECUTABLE" ]; then
  set -- "$@" --executable-path "$EXECUTABLE"
fi

if [ "${PLAYWRIGHT_MCP_HEADLESS:-1}" = "1" ]; then
  set -- "$@" --headless
fi

if [ "${PLAYWRIGHT_MCP_ISOLATED:-0}" = "1" ]; then
  set -- "$@" --isolated
fi

if [ -n "${PLAYWRIGHT_MCP_VIEWPORT:-}" ]; then
  set -- "$@" --viewport-size "$PLAYWRIGHT_MCP_VIEWPORT"
fi

exec npx "$@"
