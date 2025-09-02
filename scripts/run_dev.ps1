# PowerShell: run Daphne ASGI server for local dev with websockets
param(
    [int]$Port = 8001,
    [string]$Bind = "127.0.0.1"
)

Write-Host "Starting Daphne on http://$Bind:$Port ..." -ForegroundColor Cyan
$env:DJANGO_SETTINGS_MODULE = "pmbeta.settings"

# Prefer Python launcher
$py = "py"
try {
  & $py -3 -m daphne -b $Bind -p $Port pmbeta.asgi:application
} catch {
  # Fallback to 'python'
  python -m daphne -b $Bind -p $Port pmbeta.asgi:application
}

