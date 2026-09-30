#!/usr/bin/env sh
# Sentry MCP server (stdio) for the self-hosted instance at sentry.regulus.systems.
#
# Reads SENTRY_ACCESS_TOKEN (and optionally SENTRY_HOST) from the gitignored
# .env file at the repo root, so the token never lands in mcp.json or git.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$SCRIPT_DIR/../.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

if [ -z "${SENTRY_ACCESS_TOKEN:-}" ] || [ "${SENTRY_ACCESS_TOKEN}" = "replace-with-your-sentry-token" ]; then
  echo "sentry-mcp: SENTRY_ACCESS_TOKEN is not set in $ENV_FILE" >&2
  echo "sentry-mcp: create a token at https://sentry.regulus.systems/settings/account/api/auth-tokens/" >&2
  exit 1
fi

exec npx -y @sentry/mcp-server@latest --host="${SENTRY_HOST:-sentry.regulus.systems}"
