param([switch]$NoTick)
$ErrorActionPreference = "Stop"

# Ensure Redis is up
& "$PSScriptRoot\dev_redis.ps1"

# Create and activate venv if missing
if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

# Install deps and run
python -m pip install -U pip wheel setuptools
if (Test-Path "requirements.txt") {
  pip install -r requirements.txt
}

python manage.py migrate

if (-not $NoTick) {
  Write-Host "Starting flag income/upkeep loop in background..."
  Start-Process -WindowStyle Minimized powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command `"& 'python' 'manage.py' 'process_flags' '--loop' '--interval' '60'`"" | Out-Null
}

Write-Host "Starting Django server on http://localhost:8000"
python manage.py runserver 0.0.0.0:8000

