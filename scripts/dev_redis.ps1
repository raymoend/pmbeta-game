param()
$ErrorActionPreference = "Stop"

# Start Redis using Docker if available; otherwise prompt for Memurai/Redis
if (Get-Command docker -ErrorAction SilentlyContinue) {
  Write-Host "Starting Redis via Docker..."
  docker rm -f pk-redis 2>$null | Out-Null
  docker run -d --name pk-redis -p 6379:6379 redis:7-alpine | Out-Null
  Write-Host "Redis running at redis://127.0.0.1:6379 (container: pk-redis)"
} else {
  Write-Host "Docker not found. Ensure Redis/Memurai is running locally on 127.0.0.1:6379."
  Write-Host "Tip: winget install Memurai.MemuraiCommunity"
}

