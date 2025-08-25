param()
$ErrorActionPreference = "Stop"

# Stop Redis container if it exists
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker rm -f pk-redis 2>$null | Out-Null
}

# Kill background process_flags loop
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match "manage.py process_flags" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Write-Host "Dev environment stopped."
