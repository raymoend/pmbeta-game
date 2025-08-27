#!/usr/bin/env python3
"""
Start Daphne using the PORT environment variable without shell expansion.
Also optionally launch database migrations (and optional setup) in the background
so the app can pass health checks quickly and become available.
"""
import os
import sys
import subprocess

PORT = os.environ.get("PORT", "8000")
HOST = os.environ.get("HOST", "0.0.0.0")
APP = os.environ.get("ASGI_APP", "pmbeta.asgi:application")

RUN_MIGRATIONS = os.environ.get("RUN_MIGRATIONS_ON_START", "1").lower() in ("1", "true", "yes")
RUN_MIGRATIONS_SYNC = os.environ.get("RUN_MIGRATIONS_SYNC", "1").lower() in ("1", "true", "yes")
RUN_SETUP = os.environ.get("RUN_SETUP_RAILWAY", "").lower() in ("1", "true", "yes")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# Basic validation and logging
try:
    int(PORT)
except ValueError:
    print(f"Invalid PORT env value: {PORT!r}. Falling back to 8000.")
    PORT = "8000"

# Apply migrations (sync by default so tables exist before serving)
if RUN_MIGRATIONS:
    if RUN_MIGRATIONS_SYNC:
        try:
            print("Running migrations: python manage.py migrate --noinput (synchronous)")
            result = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=False)
            if result.returncode != 0:
                print(f"Warning: migrations exited with code {result.returncode}; proceeding to start server")
        except Exception as e:
            print(f"Warning: migrations failed to start: {e}; proceeding to start server")
    else:
        try:
            print("Launching background migrations: python manage.py migrate --noinput")
            subprocess.Popen([sys.executable, "manage.py", "migrate", "--noinput"])  # nosec B603,B607
        except Exception as e:
            print(f"Warning: could not start background migrations: {e}")

if RUN_SETUP:
    try:
        print("Launching background setup_railway (one-time recommended):")
        subprocess.Popen([sys.executable, "manage.py", "setup_railway", "--admin-password", ADMIN_PASSWORD])  # nosec B603,B607
    except Exception as e:
        print(f"Warning: could not start background setup_railway: {e}")

print(f"Starting Daphne on {HOST}:{PORT} -> {APP}")

# Exec Daphne so signals are delivered to the server process
os.execvp("daphne", [
    "daphne",
    "-b", HOST,
    "-p", str(PORT),
    APP,
])

