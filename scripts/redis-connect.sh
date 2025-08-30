#!/usr/bin/env bash
set -euo pipefail

URL="${1:-}"
if [[ -z "${URL}" ]]; then
  URL="${REDIS_URL:-}"
fi

if [[ -z "${URL}" ]]; then
  echo "REDIS_URL not set and no URL arg provided." >&2
  echo "Usage: scripts/redis-connect.sh redis://default:{{REDIS_PASSWORD}}@host:port" >&2
  echo "Or set REDIS_URL environment variable and run: ./scripts/redis-connect.sh" >&2
  exit 1
fi

if ! command -v redis-cli >/dev/null 2>&1; then
  echo "redis-cli not found on PATH." >&2
  echo "Install Redis tools or use Docker as a fallback:" >&2
  echo "  docker run -it --rm redis:7-alpine redis-cli -u \"$URL\"" >&2
  exit 1
fi

echo "Connecting to Redis ..."
exec redis-cli -u "$URL"

