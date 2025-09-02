#!/usr/bin/env bash
# Run Daphne ASGI server for local dev with websockets
PORT=${1:-8001}
BIND=${2:-127.0.0.1}
export DJANGO_SETTINGS_MODULE=pmbeta.settings
echo "Starting Daphne on http://${BIND}:${PORT} ..."
python -m daphne -b "$BIND" -p "$PORT" pmbeta.asgi:application

