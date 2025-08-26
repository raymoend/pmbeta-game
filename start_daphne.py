#!/usr/bin/env python3
"""
Start Daphne using the PORT environment variable without shell expansion.
This avoids cases where Railway runs the Start Command directly (no shell),
causing "$PORT" to be passed literally to daphne.
"""
import os
import sys
import subprocess

PORT = os.environ.get("PORT", "8000")
HOST = os.environ.get("HOST", "0.0.0.0")
APP = os.environ.get("ASGI_APP", "pmbeta.asgi:application")

# Basic validation and logging
try:
    int(PORT)
except ValueError:
    print(f"Invalid PORT env value: {PORT!r}. Falling back to 8000.")
    PORT = "8000"

print(f"Starting Daphne on {HOST}:{PORT} -> {APP}")

# Exec Daphne so signals are delivered to the server process
os.execvp("daphne", [
    "daphne",
    "-b", HOST,
    "-p", str(PORT),
    APP,
])

