# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Wrap daphne so it resolves $PORT even when Start Command is executed without a shell
RUN if [ -x /usr/local/bin/daphne ]; then mv /usr/local/bin/daphne /usr/local/bin/daphne.orig; fi \
    && printf '%s\n' '#!/bin/sh' 'PORT="${PORT:-8000}"' 'HOST="${HOST:-0.0.0.0}"' 'APP="${ASGI_APP:-pmbeta.asgi:application}"' 'exec /usr/local/bin/daphne.orig -b "$HOST" -p "$PORT" "$APP"' > /usr/local/bin/daphne \
    && chmod +x /usr/local/bin/daphne

COPY . .

# Collect static files (ignore errors if none)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Ensure production behavior on Railway and bind to provided $PORT
ENV DJANGO_SETTINGS_MODULE=pmbeta.settings RAILWAY_ENVIRONMENT=production RAILWAY_QUICK_START=1

# Provide an `export` wrapper so Railway Start Command overrides like
# `export FOO=bar && python ...` work even without a shell.
RUN printf '%s\n' '#!/bin/sh' 'cmd="$*"' 'exec sh -lc "export $cmd"' > /usr/local/bin/export \
    && chmod +x /usr/local/bin/export

# Robust entrypoint: start via Python script that reads $PORT and execs Daphne.
# This works even when the platform does not use a shell (so "$PORT" wouldn't expand).
ENTRYPOINT ["python", "start_daphne.py"]

# Any command provided by the platform will be passed as args and ignored by the launcher.
CMD [""]
